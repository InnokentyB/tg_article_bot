#!/usr/bin/env python3
"""Recover original Habr links for legacy n8n-imported articles.

The old n8n pipeline stored article text and title but did not persist the
source URL. Most of those rows appear to be Habr posts, so this script builds a
temporary Habr title index from official sitemaps + article JSON API and links
only unambiguous title matches.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import aiohttp
import asyncpg


HABR_SITEMAPS = (
    "https://habr.com/sitemap_articles1.xml",
    "https://habr.com/sitemap_articles2.xml",
)
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; TGArticlesLinkRecovery/0.1)"


def clean_title(value: str | None) -> str:
    title = html.unescape(value or "")
    title = re.sub(r"<[^>]+>", "", title)
    title = title.replace("\xa0", " ")
    title = title.replace("ё", "е").replace("Ё", "Е")
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"\s*/\s*Хабр\s*$", "", title, flags=re.IGNORECASE).strip()
    return title


def normalized_title(value: str | None) -> str:
    title = clean_title(value)
    title = re.sub(
        r"^\[(перевод|обзор|туториал)\]\s*",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()
    title = re.sub(r"\s*([:;,.!?])\s*", r"\1 ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title.casefold()


async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def load_habr_candidates(
    session: aiohttp.ClientSession,
    id_min: int,
    id_max: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    for sitemap_url in HABR_SITEMAPS:
        xml_text = await fetch_text(session, sitemap_url)
        root = ET.fromstring(xml_text)
        for item in root.findall("sm:url", namespace):
            loc = (item.findtext("sm:loc", default="", namespaces=namespace) or "").strip()
            match = re.search(r"/ru/articles/(\d+)/?", loc)
            if not match:
                continue
            habr_id = int(match.group(1))
            if id_min <= habr_id <= id_max:
                candidates.append(
                    {
                        "habr_id": habr_id,
                        "url": f"https://habr.com/ru/articles/{habr_id}/",
                    }
                )

    return sorted(candidates, key=lambda row: row["habr_id"])


async def fetch_habr_article(
    session: aiohttp.ClientSession,
    candidate: dict[str, Any],
    retries: int,
    request_delay: float,
) -> tuple[dict[str, Any] | None, str]:
    habr_id = candidate["habr_id"]
    api_url = f"https://habr.com/kek/v2/articles/{habr_id}/"

    for attempt in range(retries + 1):
        if request_delay:
            await asyncio.sleep(request_delay)
        try:
            async with session.get(api_url) as response:
                status = response.status
                if status == 200:
                    data = await response.json(content_type=None)
                    title = clean_title(data.get("titleHtml") or data.get("title"))
                    if not title:
                        return None, "empty_title"
                    return (
                        {
                            "habr_id": habr_id,
                            "url": candidate["url"],
                            "published_at": (data.get("timePublished") or "")[:10],
                            "title": title,
                        },
                        "200",
                    )
                if status in {429, 500, 502, 503, 504} and attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return None, str(status)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return None, "client_error"

    return None, "unknown_error"


async def load_or_build_habr_index(args: argparse.Namespace) -> tuple[dict[str, list[dict[str, Any]]], Counter]:
    cache_path = Path(args.cache_file).expanduser()
    status_counts: Counter = Counter()

    if cache_path.exists() and not args.refresh_cache:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        articles = payload["articles"]
        status_counts.update(payload.get("status_counts") or {})
    else:
        timeout = aiohttp.ClientTimeout(total=args.request_timeout)
        connector = aiohttp.TCPConnector(limit=args.concurrency)
        headers = {"User-Agent": args.user_agent}
        async with aiohttp.ClientSession(
            connector=connector,
            headers=headers,
            timeout=timeout,
        ) as session:
            candidates = await load_habr_candidates(session, args.id_min, args.id_max)
            if args.candidate_limit:
                candidates = candidates[: args.candidate_limit]
            print(f"Habr candidates: {len(candidates)}", flush=True)

            semaphore = asyncio.Semaphore(args.concurrency)
            done = 0
            started_at = time.monotonic()
            articles = []

            async def run_one(candidate: dict[str, Any]) -> None:
                nonlocal done
                async with semaphore:
                    article, status = await fetch_habr_article(
                        session,
                        candidate,
                        retries=args.retries,
                        request_delay=args.request_delay,
                    )
                status_counts[status] += 1
                if article:
                    articles.append(article)
                done += 1
                if done % args.progress_every == 0:
                    elapsed = round(time.monotonic() - started_at, 1)
                    print(
                        f"Fetched {done}/{len(candidates)} Habr titles in {elapsed}s",
                        flush=True,
                    )

            await asyncio.gather(*(run_one(candidate) for candidate in candidates))

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "id_min": args.id_min,
                    "id_max": args.id_max,
                    "articles": sorted(articles, key=lambda row: row["habr_id"]),
                    "status_counts": dict(status_counts),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    title_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for article in articles:
        title_index[normalized_title(article["title"])].append(article)

    return title_index, status_counts


async def load_n8n_articles(conn: asyncpg.Connection, source: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        select id, title, original_link
        from articles
        where source = $1
          and coalesce(original_link, '') = ''
        order by id
        """,
        source,
    )


async def existing_article_columns(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        select column_name
        from information_schema.columns
        where table_name = 'articles'
        """
    )
    return {row["column_name"] for row in rows}


async def apply_matches(
    conn: asyncpg.Connection,
    matches: list[tuple[int, dict[str, Any]]],
    batch_size: int,
) -> int:
    columns = await existing_article_columns(conn)
    writable_columns = [
        column
        for column in ("original_link", "canonical_url", "direct_source_url")
        if column in columns
    ]
    if not writable_columns:
        raise RuntimeError("No supported URL columns found on articles table")

    updated = 0
    for start in range(0, len(matches), batch_size):
        batch = matches[start : start + batch_size]
        async with conn.transaction():
            for article_id, habr_article in batch:
                assignments = [
                    f"{column} = coalesce(nullif({column}, ''), $2)"
                    for column in writable_columns
                ]
                await conn.execute(
                    f"""
                    update articles
                    set {", ".join(assignments)}, updated_at = current_timestamp
                    where id = $1
                    """,
                    article_id,
                    habr_article["url"],
                )
                updated += 1

    return updated


def print_examples(
    title: str,
    rows: list[tuple[asyncpg.Record, list[dict[str, Any]]]] | list[tuple[int, dict[str, Any]]],
    limit: int,
) -> None:
    print(f"\n{title}:")
    for row in rows[:limit]:
        if isinstance(row[0], int):
            article_id, habr_article = row
            print(f"  {article_id}: {habr_article['url']} | {habr_article['title']}")
        else:
            article, hits = row
            print(f"  {article['id']}: {article['title']} -> {[hit['url'] for hit in hits[:3]]}")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Update matched rows in the database")
    parser.add_argument("--source", default="n8n", help="Legacy source name to repair")
    parser.add_argument("--id-min", type=int, default=940000, help="Minimum Habr article id to index")
    parser.add_argument("--id-max", type=int, default=986000, help="Maximum Habr article id to index")
    parser.add_argument("--candidate-limit", type=int, default=0, help="Debug limit for Habr candidates")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent Habr API requests")
    parser.add_argument("--request-delay", type=float, default=0.15, help="Delay before each Habr API request")
    parser.add_argument("--request-timeout", type=float, default=20.0, help="HTTP request timeout in seconds")
    parser.add_argument("--retries", type=int, default=4, help="Retries for transient Habr API errors")
    parser.add_argument("--batch-size", type=int, default=100, help="Database update batch size")
    parser.add_argument("--examples", type=int, default=12, help="Number of examples to print")
    parser.add_argument("--progress-every", type=int, default=500, help="Progress log interval")
    parser.add_argument("--refresh-cache", action="store_true", help="Ignore cached Habr titles")
    parser.add_argument(
        "--cache-file",
        default="/tmp/tgarticles_habr_titles_940000_986000.json",
        help="JSON cache for fetched Habr titles",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        title_index, status_counts = await load_or_build_habr_index(args)
        n8n_articles = await load_n8n_articles(conn, args.source)

        matches: list[tuple[int, dict[str, Any]]] = []
        ambiguous: list[tuple[asyncpg.Record, list[dict[str, Any]]]] = []
        missing: list[asyncpg.Record] = []

        for article in n8n_articles:
            hits = title_index.get(normalized_title(article["title"]), [])
            if len(hits) == 1:
                matches.append((article["id"], hits[0]))
            elif len(hits) > 1:
                ambiguous.append((article, hits))
            else:
                missing.append(article)

        print("\nRecovery report")
        print(f"source={args.source}")
        print(f"n8n_without_original_link={len(n8n_articles)}")
        print(f"unique_matches={len(matches)}")
        print(f"ambiguous={len(ambiguous)}")
        print(f"missing={len(missing)}")
        print(f"habr_status_counts={dict(status_counts)}")

        print_examples("Match examples", matches, args.examples)
        print_examples("Ambiguous examples", ambiguous, args.examples)

        print("\nMissing examples:")
        for article in missing[: args.examples]:
            print(f"  {article['id']}: {article['title']}")

        if args.apply:
            updated = await apply_matches(conn, matches, args.batch_size)
            print(f"\nApplied updates: {updated}")
        else:
            print("\nDry run only. Re-run with --apply to update unique matches.")
    finally:
        await conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

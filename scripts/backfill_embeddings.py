#!/usr/bin/env python3
"""Backfill article chunks and embeddings for existing articles."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from itertools import islice
from pathlib import Path
from typing import Any

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from article_chunker import ArticleChunker
from embedding_provider import get_embedding_provider


def get_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    raw = subprocess.check_output(
        ["railway", "variables", "--json", "--service", "tg-article-bot-db"],
        text=True,
    )
    return json.loads(raw)["DATABASE_PUBLIC_URL"] + "?sslmode=require"


async def get_counts(conn: asyncpg.Connection, model: str) -> dict[str, int]:
    articles = await conn.fetchval("select count(*) from articles")
    articles_with_text = await conn.fetchval(
        "select count(*) from articles where coalesce(text, '') <> ''"
    )
    chunks = await conn.fetchval("select count(*) from article_chunks")
    chunked_articles = await conn.fetchval(
        "select count(distinct article_id) from article_chunks"
    )
    embeddings = await conn.fetchval(
        "select count(*) from article_embeddings where model = $1",
        model,
    )
    embedded_articles = await conn.fetchval(
        "select count(distinct article_id) from article_embeddings where model = $1",
        model,
    )
    pending_articles = await conn.fetchval(
        """
        select count(*)
        from articles a
        where coalesce(a.text, '') <> ''
          and not exists (
              select 1
              from article_embeddings e
              where e.article_id = a.id
                and e.model = $1
          )
        """,
        model,
    )
    return {
        "articles": articles,
        "articles_with_text": articles_with_text,
        "chunks": chunks,
        "chunked_articles": chunked_articles,
        "embeddings": embeddings,
        "embedded_articles": embedded_articles,
        "pending_articles": pending_articles,
    }


def print_counts(label: str, counts: dict[str, int], model: str) -> None:
    print(label)
    print(f"model={model}")
    for key, value in counts.items():
        print(f"{key}={value}")


async def fetch_articles(
    conn: asyncpg.Connection,
    model: str,
    limit: int,
    force: bool,
) -> list[asyncpg.Record]:
    where = "coalesce(a.text, '') <> ''"
    if not force:
        where += """
          and not exists (
              select 1
              from article_embeddings e
              where e.article_id = a.id
                and e.model = $1
          )
        """
        return await conn.fetch(
            f"""
            select a.id, a.title, a.text
            from articles a
            where {where}
            order by a.id
            limit $2
            """,
            model,
            limit,
        )

    return await conn.fetch(
        f"""
        select a.id, a.title, a.text
        from articles a
        where {where}
        order by a.id
        limit $1
        """,
        limit,
    )


async def replace_chunks(
    conn: asyncpg.Connection,
    article_id: int,
    chunks: Sequence[dict[str, Any]],
) -> list[asyncpg.Record]:
    await conn.execute("delete from article_chunks where article_id = $1", article_id)
    if not chunks:
        return []

    indexes = [chunk.get("chunk_index", index) for index, chunk in enumerate(chunks)]
    texts = [chunk["text"] for chunk in chunks]
    token_counts = [chunk.get("token_count") for chunk in chunks]
    metadata = [json.dumps(chunk.get("metadata") or {}) for chunk in chunks]
    return await conn.fetch(
        """
        insert into article_chunks
            (article_id, chunk_index, text, token_count, metadata)
        select $1, chunk_index, text, token_count, metadata
        from unnest(
            $2::int[],
            $3::text[],
            $4::int[],
            $5::jsonb[]
        ) as payload(chunk_index, text, token_count, metadata)
        order by chunk_index
        returning id, article_id, chunk_index, text
        """,
        article_id,
        indexes,
        texts,
        token_counts,
        metadata,
    )


async def get_or_create_chunks(
    conn: asyncpg.Connection,
    chunker: ArticleChunker,
    article_id: int,
    text: str,
    force: bool,
) -> list[asyncpg.Record]:
    if force:
        return await replace_chunks(conn, article_id, chunker.chunk_text(text))

    rows = await conn.fetch(
        """
        select id, article_id, chunk_index, text
        from article_chunks
        where article_id = $1
        order by chunk_index
        """,
        article_id,
    )
    if rows:
        return rows

    return await replace_chunks(conn, article_id, chunker.chunk_text(text))


async def upsert_embeddings(
    conn: asyncpg.Connection,
    article_id: int,
    chunks: Sequence[asyncpg.Record],
    model: str,
    vectors: Sequence[Sequence[float]],
) -> int:
    rows = [
        (
            article_id,
            chunk["id"],
            model,
            f"[{','.join(map(str, vector))}]",
            len(vector),
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    if not rows:
        return 0
    await conn.executemany(
        """
        insert into article_embeddings
            (article_id, chunk_id, model, embedding, embedding_dimensions)
        values ($1, $2, $3, $4::vector, $5)
        on conflict (chunk_id, model) do update set
            embedding = excluded.embedding,
            embedding_dimensions = excluded.embedding_dimensions,
            created_at = current_timestamp
        """,
        rows,
    )
    return len(rows)


async def upsert_embedding_rows(
    conn: asyncpg.Connection,
    rows: Sequence[tuple[int, int, str, str, int]],
) -> int:
    if not rows:
        return 0
    await conn.executemany(
        """
        insert into article_embeddings
            (article_id, chunk_id, model, embedding, embedding_dimensions)
        values ($1, $2, $3, $4::vector, $5)
        on conflict (chunk_id, model) do update set
            embedding = excluded.embedding,
            embedding_dimensions = excluded.embedding_dimensions,
            created_at = current_timestamp
        """,
        rows,
    )
    return len(rows)


def batched(items: Sequence[Any], size: int) -> Sequence[Sequence[Any]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


async def get_chunks_for_batch(
    conn: asyncpg.Connection,
    chunker: ArticleChunker,
    articles: Sequence[asyncpg.Record],
    force: bool,
) -> dict[int, list[asyncpg.Record]]:
    article_ids = [article["id"] for article in articles]
    if force:
        await conn.execute("delete from article_chunks where article_id = any($1::int[])", article_ids)

    existing = []
    if not force:
        existing = await conn.fetch(
            """
            select id, article_id, chunk_index, text
            from article_chunks
            where article_id = any($1::int[])
            order by article_id, chunk_index
            """,
            article_ids,
        )

    chunks_by_article: dict[int, list[asyncpg.Record]] = {}
    for row in existing:
        chunks_by_article.setdefault(row["article_id"], []).append(row)

    insert_article_ids = []
    insert_indexes = []
    insert_texts = []
    insert_token_counts = []
    insert_metadata = []

    for article in articles:
        article_id = article["id"]
        if chunks_by_article.get(article_id):
            continue

        for index, chunk in enumerate(chunker.chunk_text(article["text"] or "")):
            insert_article_ids.append(article_id)
            insert_indexes.append(chunk.get("chunk_index", index))
            insert_texts.append(chunk["text"])
            insert_token_counts.append(chunk.get("token_count"))
            insert_metadata.append(json.dumps(chunk.get("metadata") or {}))

    if insert_article_ids:
        inserted = await conn.fetch(
            """
            insert into article_chunks
                (article_id, chunk_index, text, token_count, metadata)
            select article_id, chunk_index, text, token_count, metadata
            from unnest(
                $1::int[],
                $2::int[],
                $3::text[],
                $4::int[],
                $5::jsonb[]
            ) as payload(article_id, chunk_index, text, token_count, metadata)
            order by article_id, chunk_index
            returning id, article_id, chunk_index, text
            """,
            insert_article_ids,
            insert_indexes,
            insert_texts,
            insert_token_counts,
            insert_metadata,
        )
        for row in inserted:
            chunks_by_article.setdefault(row["article_id"], []).append(row)

    return chunks_by_article


async def ensure_vector_index(conn: asyncpg.Connection, dimensions: int) -> None:
    index_name = f"idx_article_embeddings_ivfflat_{dimensions}"
    exists = await conn.fetchval(
        "select 1 from pg_indexes where indexname = $1",
        index_name,
    )
    if exists:
        return
    await conn.execute(
        f"""
        create index {index_name}
            on article_embeddings
            using ivfflat ((embedding::vector({dimensions})) vector_cosine_ops)
            with (lists = 100)
        """
    )


async def backfill(args: argparse.Namespace) -> None:
    if args.provider:
        os.environ["EMBEDDING_PROVIDER"] = args.provider
    if args.fake_dimensions:
        os.environ["FAKE_EMBEDDING_DIMENSIONS"] = str(args.fake_dimensions)
    if args.openai_model:
        os.environ["OPENAI_EMBEDDING_MODEL"] = args.openai_model
    if args.openai_dimensions:
        os.environ["OPENAI_EMBEDDING_DIMENSIONS"] = str(args.openai_dimensions)

    provider = get_embedding_provider()
    model = args.model or provider.model
    chunker = ArticleChunker(max_words=args.max_words, overlap_words=args.overlap_words)

    conn = await asyncpg.connect(get_database_url())
    try:
        before = await get_counts(conn, model)
        print_counts("Before backfill:", before, model)
        candidates = await fetch_articles(conn, model, args.limit, args.force)
        print(f"selected_articles={len(candidates)}")

        if not args.apply:
            print("Dry run only. Re-run with --apply to write chunks and embeddings.")
            return

        processed_articles = 0
        written_chunks = 0
        written_embeddings = 0
        vector_dimensions = 0

        for article_batch in batched(candidates, args.article_batch_size):
            async with conn.transaction():
                chunks_by_article = await get_chunks_for_batch(
                    conn,
                    chunker,
                    article_batch,
                    args.force,
                )

            flat_chunks = [
                chunk
                for article in article_batch
                for chunk in chunks_by_article.get(article["id"], [])
            ]
            if not flat_chunks:
                continue

            embedding_rows = []
            for chunk_batch in batched(flat_chunks, args.embedding_batch_size):
                vectors = await provider.embed_texts([chunk["text"] for chunk in chunk_batch])
                if len(vectors) != len(chunk_batch):
                    raise RuntimeError(
                        f"Embedding provider returned {len(vectors)} vectors for "
                        f"{len(chunk_batch)} chunks"
                    )
                if vectors and not vector_dimensions:
                    vector_dimensions = len(vectors[0])
                embedding_rows.extend(
                    (
                        chunk["article_id"],
                        chunk["id"],
                        model,
                        f"[{','.join(map(str, vector))}]",
                        len(vector),
                    )
                    for chunk, vector in zip(chunk_batch, vectors)
                )

            async with conn.transaction():
                written_embeddings += await upsert_embedding_rows(conn, embedding_rows)

            written_chunks += len(flat_chunks)
            processed_articles += len(
                {
                    chunk["article_id"]
                    for chunk in flat_chunks
                }
            )

            if processed_articles % args.progress_every < args.article_batch_size:
                print(
                    "progress "
                    f"articles={processed_articles} "
                    f"chunks={written_chunks} "
                    f"embeddings={written_embeddings}",
                    flush=True,
                )

        if vector_dimensions:
            await ensure_vector_index(conn, vector_dimensions)

        after = await get_counts(conn, model)
        print_counts("After backfill:", after, model)
        print(
            "written "
            f"articles={processed_articles} "
            f"chunks={written_chunks} "
            f"embeddings={written_embeddings} "
            f"dimensions={vector_dimensions}"
        )
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write chunks and embeddings")
    parser.add_argument("--force", action="store_true", help="Rebuild selected articles")
    parser.add_argument("--limit", type=int, default=100, help="Maximum articles to process")
    parser.add_argument("--provider", choices=["fake", "openai"], help="Embedding provider")
    parser.add_argument("--model", help="Stored model name override")
    parser.add_argument("--fake-dimensions", type=int, help="Fake provider vector dimensions")
    parser.add_argument("--openai-model", help="OpenAI embedding model")
    parser.add_argument("--openai-dimensions", type=int, help="OpenAI embedding dimensions")
    parser.add_argument("--max-words", type=int, default=450)
    parser.add_argument("--overlap-words", type=int, default=60)
    parser.add_argument("--article-batch-size", type=int, default=250)
    parser.add_argument("--embedding-batch-size", type=int, default=512)
    parser.add_argument("--progress-every", type=int, default=100)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(backfill(parse_args()))

#!/usr/bin/env python3
"""Generate and publish today's daily digest once.

This is intended for the first real-channel run when a draft for the same
digest date already exists and the regular endpoint skips duplicate creation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import DatabaseManager
from daily_digest_job import DailyDigestConfig, DailyDigestJob


async def publish_once(args: argparse.Namespace) -> None:
    db = DatabaseManager()
    await db.initialize()
    try:
        config = DailyDigestConfig.from_env()
        config.period_days = args.period_days
        config.max_articles = args.max_articles

        job = DailyDigestJob(db, config=config)
        result = await job.run(dry_run=True, publish=False)

        if args.publish:
            published = await job._publish_daily_messages(
                digest_message=result["digest_message"],
                review_message=result["review_message"],
            )
            if not published:
                raise RuntimeError("Telegram publication failed")
        else:
            published = False

        async with db.pool.acquire() as conn:
            review_id = await conn.fetchval(
                """
                UPDATE reviews
                SET review_markdown = $1,
                    telegram_draft = $2,
                    status = CASE WHEN $3 THEN 'published' ELSE status END,
                    metadata = metadata || $4::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE metadata->>'job' = 'daily_digest'
                  AND metadata->>'digest_date' = $5
                RETURNING id
                """,
                result["review_markdown"],
                result["telegram_message"],
                published,
                json.dumps(
                    {
                        "generator": "openai-critical-review-v1",
                        "published_via": "manual_openai_first_run",
                        "publish_requested": args.publish,
                        "telegram_posting": "split_digest_and_review",
                        "digest_message": result["digest_message"],
                        "review_message": result["review_message"],
                    }
                ),
                result["digest_date"],
            )

        print(
            json.dumps(
                {
                    "published": published,
                    "review_id": review_id,
                    "digest_date": result["digest_date"],
                    "best_article_id": result["best_article"]["article_id"],
                    "best_article_title": result["best_article"]["title"],
                },
                ensure_ascii=False,
            )
        )
    finally:
        await db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Send to Telegram")
    parser.add_argument("--period-days", type=int, default=3)
    parser.add_argument("--max-articles", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(publish_once(parse_args()))

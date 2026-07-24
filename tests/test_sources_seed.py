#!/usr/bin/env python3
"""
Checks for the source catalog and SQL seed file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "sources.seed.json"
SEEDS_SQL_PATH = ROOT / "seeds.sql"


def test_source_catalog_is_valid() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    assert catalog["version"] >= 1
    assert catalog["sources"]

    urls = set()
    for source in catalog["sources"]:
        assert source["name"]
        assert source["url"].startswith("https://")
        assert source["source_type"] in {"rss", "modernanalyst_html", "mindtheproduct_json", "ireb_html"}
        assert source["language"] in {"en", "ru"}
        assert source["fetch_interval_hours"] >= 1
        assert source["metadata"]["tier"] == 1
        assert source["metadata"]["editorial_role"]
        urls.add(source["url"])

    assert len(urls) == len(catalog["sources"])


def test_sql_seed_matches_active_catalog_sources() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    active_urls = {source["url"] for source in catalog["sources"] if source["is_active"]}
    seeds_sql = SEEDS_SQL_PATH.read_text(encoding="utf-8")
    sql_urls = set(re.findall(r"'(https://[^']+)'", seeds_sql))

    assert active_urls == sql_urls

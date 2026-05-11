"""Enrich unresolved affiliation regions with ROR organization lookup.

This is deliberately conservative. It only overwrites entries that are still
Other/Multiple and whose top ROR result has enough name overlap with the
affiliation string.
"""
from __future__ import annotations

import csv
import difflib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CLASS_DIR = ROOT / "classification"
TABLE_PATH = CLASS_DIR / "aff_region_table.json"
META_PATH = CLASS_DIR / "aff_region_metadata.json"
CACHE_PATH = CLASS_DIR / "ror_cache.json"
REVIEW_PATH = CLASS_DIR / "aff_region_review.csv"
COUNTS_PATH = CLASS_DIR / "aff_region_counts.csv"

COUNTRY_ALIASES = {
    "United States": "USA",
    "United States of America": "USA",
    "Korea, Republic of": "South Korea",
    "Republic of Korea": "South Korea",
    "United Kingdom": "United Kingdom",
    "Hong Kong": "China",
    "Macao": "China",
    "Macau": "China",
}

STOPWORDS = {
    "the", "of", "and", "for", "in", "at", "to", "from", "department", "school",
    "college", "faculty", "laboratory", "lab", "labs", "institute", "university",
    "research", "center", "centre", "science", "technology", "artificial", "intelligence",
    "computer", "engineering", "inc", "ltd", "co", "corporation", "group",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("&amp;", "&")
    value = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def tokens(value: str) -> set[str]:
    return {t for t in norm(value).split() if len(t) >= 3 and t not in STOPWORDS}


def representative_query(aff: str) -> str:
    parts = [p.strip() for p in re.split(r"\s*(?:/|;|\+|\band\b)\s*", aff) if p.strip()]
    return parts[0] if parts else aff


def display_name(item: dict) -> str:
    names = item.get("names") or []
    for name in names:
        if "ror_display" in name.get("types", []):
            return str(name.get("value") or "")
    return str(names[0].get("value") if names else "")


def country_name(item: dict) -> str:
    locs = item.get("locations") or []
    if not locs:
        return ""
    country = (locs[0].get("geonames_details") or {}).get("country_name") or ""
    return COUNTRY_ALIASES.get(country, country)


def confidence(query: str, candidate: str) -> tuple[float, int]:
    qn, cn = norm(query), norm(candidate)
    ratio = difflib.SequenceMatcher(None, qn, cn).ratio()
    overlap = len(tokens(query) & tokens(candidate))
    return ratio, overlap


def accept_match(query: str, candidate: str) -> bool:
    ratio, overlap = confidence(query, candidate)
    q_tokens = tokens(query)
    if len(q_tokens) <= 2:
        return ratio >= 0.72 or overlap >= len(q_tokens)
    return ratio >= 0.58 or overlap >= 2


def lookup_ror(query: str, cache: dict[str, dict]) -> dict:
    key = norm(query)
    if key in cache:
        return cache[key]
    url = "https://api.ror.org/organizations?" + urlencode({"query": query})
    req = Request(url, headers={"User-Agent": "cvpr2026-explorer-builder/0.1"})
    try:
        data = json.loads(urlopen(req, timeout=20).read().decode("utf-8"))
        item = (data.get("items") or [None])[0]
        if item:
            result = {"name": display_name(item), "country": country_name(item), "id": item.get("id", "")}
        else:
            result = {"name": "", "country": "", "id": ""}
    except Exception as exc:  # network/API failures stay cached as misses for this run
        result = {"name": "", "country": "", "id": "", "error": str(exc)}
    cache[key] = result
    time.sleep(0.08)
    return result


def write_review_and_counts(table: dict[str, str], meta: dict[str, dict]) -> None:
    with COUNTS_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "unique_affiliations", "paper_affiliation_mentions"])
        for region, unique_count in Counter(table.values()).most_common():
            mention_count = sum(int(meta[a]["paper_count"]) for a, r in table.items() if r == region)
            writer.writerow([region, unique_count, mention_count])

    with REVIEW_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["affiliation", "paper_count", "region", "source", "evidence"])
        for aff, m in sorted(meta.items(), key=lambda kv: (-int(kv[1]["paper_count"]), kv[0])):
            if m["region"] in {"Other", "Multiple"} or m["source"] in {"unresolved", "ambiguous"}:
                writer.writerow([aff, m["paper_count"], m["region"], m["source"], m.get("evidence", "")])


def main() -> None:
    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}

    min_count = int(os.environ.get("ROR_MIN_COUNT", "2"))
    candidates = [
        aff for aff, m in sorted(meta.items(), key=lambda kv: -int(kv[1]["paper_count"]))
        if m["region"] in {"Other", "Multiple"} and int(m["paper_count"]) >= 1
        and m["source"] not in {"icra-exact"}
    ]
    candidates = [aff for aff in candidates if int(meta[aff]["paper_count"]) >= min_count]

    changed = 0
    checked = 0
    for aff in candidates:
        query = representative_query(aff)
        result = lookup_ror(query, cache)
        checked += 1
        country = result.get("country") or ""
        name = result.get("name") or ""
        if country and name and accept_match(query, name):
            table[aff] = country
            meta[aff]["region"] = country
            meta[aff]["source"] = "ror"
            ratio, overlap = confidence(query, name)
            meta[aff]["evidence"] = f"{name} | {result.get('id','')} | ratio={ratio:.2f} overlap={overlap}"
            changed += 1
        if checked % 25 == 0:
            TABLE_PATH.write_text(json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    TABLE_PATH.write_text(json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    write_review_and_counts(table, meta)

    summary = {
        "checked": checked,
        "changed": changed,
        "regions": Counter(table.values()).most_common(),
        "sources": Counter(str(m["source"]) for m in meta.values()).most_common(),
        "review_rows": sum(1 for m in meta.values() if m["region"] in {"Other", "Multiple"} or m["source"] in {"unresolved", "ambiguous"}),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

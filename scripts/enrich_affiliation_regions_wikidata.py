"""Enrich unresolved affiliation regions with Wikidata web lookup.

This complements ROR. ROR is strong for universities and research institutes;
Wikidata is often better for companies, products, labs, and acronyms. The
script is conservative and only updates unresolved/ambiguous entries when the
top Wikidata result is name-compatible and yields a country-like claim.
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
REVIEW_PATH = CLASS_DIR / "aff_region_review.csv"
COUNTS_PATH = CLASS_DIR / "aff_region_counts.csv"
CACHE_PATH = CLASS_DIR / "wikidata_cache.json"

COUNTRY_ALIASES = {
    "United States of America": "USA",
    "United States": "USA",
    "People's Republic of China": "China",
    "Republic of China": "Taiwan",
    "South Korea": "South Korea",
    "Republic of Korea": "South Korea",
    "United Kingdom": "United Kingdom",
    "Hong Kong": "China",
    "Macau": "China",
}

STOPWORDS = {
    "the", "of", "and", "for", "in", "at", "to", "from", "department", "school",
    "college", "faculty", "laboratory", "lab", "labs", "institute", "university",
    "research", "center", "centre", "science", "technology", "artificial", "intelligence",
    "computer", "engineering", "inc", "ltd", "co", "corp", "corporation", "group",
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
    parts = [p.strip() for p in re.split(r"\s*(?:/|;|\+|\band\b|,)\s*", aff) if p.strip()]
    if not parts:
        return aff
    # Keep "University of X" phrases intact, but for "Google, TUM" use Google.
    first = parts[0]
    if len(first) <= 3 and len(parts) > 1:
        return aff
    return first


def compatible(query: str, label: str, description: str = "") -> bool:
    qn, ln = norm(query), norm(label)
    ratio = difflib.SequenceMatcher(None, qn, ln).ratio()
    qtok, ltok = tokens(query), tokens(label)
    overlap = len(qtok & ltok)
    if qn == ln:
        return True
    if len(qtok) <= 2:
        return ratio >= 0.72 or overlap >= len(qtok)
    if ratio >= 0.62 or overlap >= 2:
        return True
    desc = norm(description)
    return bool(qtok and len(qtok & set(desc.split())) >= min(2, len(qtok)))


def request_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "cvpr2026-explorer-builder/0.1"})
    return json.loads(urlopen(req, timeout=20).read().decode("utf-8"))


def wikidata_search(query: str, cache: dict) -> list[dict]:
    key = "search:" + norm(query)
    if key in cache:
        return cache[key]
    url = "https://www.wikidata.org/w/api.php?" + urlencode({
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "limit": 5,
    })
    try:
        data = request_json(url)
        results = data.get("search", [])
    except Exception as exc:
        results = [{"error": str(exc)}]
    cache[key] = results
    time.sleep(0.08)
    return results


def entity_data(qid: str, cache: dict) -> dict:
    key = "entity:" + qid
    if key in cache:
        return cache[key]
    try:
        data = request_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
        entity = data.get("entities", {}).get(qid, {})
    except Exception as exc:
        entity = {"error": str(exc)}
    cache[key] = entity
    time.sleep(0.05)
    return entity


def label_for_qid(qid: str, cache: dict) -> str:
    entity = entity_data(qid, cache)
    labels = entity.get("labels", {})
    return (labels.get("en") or {}).get("value", "")


def claim_qids(entity: dict, prop: str) -> list[str]:
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = (((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
        if isinstance(value, dict) and value.get("id"):
            out.append(value["id"])
    return out


def country_from_entity(qid: str, cache: dict, depth: int = 0) -> tuple[str, str]:
    if depth > 2:
        return "", ""
    entity = entity_data(qid, cache)
    # P17 country, P495 country of origin.
    for prop in ("P17", "P495"):
        qids = claim_qids(entity, prop)
        if qids:
            label = label_for_qid(qids[0], cache)
            return COUNTRY_ALIASES.get(label, label), f"{prop}:{qids[0]}:{label}"
    # P159 headquarters location, P276 location, P131 located in admin entity.
    for prop in ("P159", "P276", "P131"):
        for loc_qid in claim_qids(entity, prop)[:2]:
            country, evidence = country_from_entity(loc_qid, cache, depth + 1)
            if country:
                return country, f"{prop}:{loc_qid}->{evidence}"
    return "", ""


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
    min_count = int(os.environ.get("WIKIDATA_MIN_COUNT", "1"))

    candidates = [
        aff for aff, m in sorted(meta.items(), key=lambda kv: -int(kv[1]["paper_count"]))
        if m["region"] in {"Other", "Multiple"}
        and int(m["paper_count"]) >= min_count
        and m["source"] not in {"icra-exact"}
    ]

    checked = 0
    changed = 0
    for aff in candidates:
        query = representative_query(aff)
        results = wikidata_search(query, cache)
        checked += 1
        for result in results:
            qid = result.get("id", "")
            label = result.get("label", "")
            desc = result.get("description", "")
            if not qid or not compatible(query, label, desc):
                continue
            country, evidence = country_from_entity(qid, cache)
            if country:
                table[aff] = country
                meta[aff]["region"] = country
                meta[aff]["source"] = "wikidata"
                meta[aff]["evidence"] = f"{label} | {qid} | {evidence}"
                changed += 1
                break
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

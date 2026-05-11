"""Merge and validate semantic topic chunks produced by worker agents."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import build_html


ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "classification"
OUT = CHUNK_DIR / "semantic_topics.json"
EXPECTED_TOTAL = len(json.loads((ROOT / "data" / "cvpr2026_papers.json").read_text(encoding="utf-8")))
REQUIRED_KEYS = ("phylum", "class", "order", "genus")
ALLOWED = {
    tuple(str(node[k]) for k in REQUIRED_KEYS)
    for node in build_html.TAXONOMY
}
ALLOWED.add(("Unclassified", "Unclassified", "Unclassified", "Unclassified"))


def validate_topic(topic: dict[str, object], paper_id: int) -> dict[str, str]:
    normalized = tuple(str(topic.get(k, "")).strip() for k in REQUIRED_KEYS)
    if normalized not in ALLOWED:
        raise ValueError(f"paper {paper_id}: invalid topic {normalized}")
    return dict(zip(REQUIRED_KEYS, normalized))


def main() -> None:
    rows: list[dict[str, object]] = []
    seen: set[int] = set()
    phylum_counts: Counter[str] = Counter()
    chunk_paths = sorted(CHUNK_DIR.glob("semantic_topics_chunk_*.json"))
    if len(chunk_paths) != 6:
        raise SystemExit(f"expected 6 semantic topic chunks, found {len(chunk_paths)}")

    for path in chunk_paths:
        chunk = json.loads(path.read_text(encoding="utf-8"))
        for row in chunk:
            paper_id = int(row["id"])
            if paper_id in seen:
                raise ValueError(f"duplicate paper id {paper_id}")
            seen.add(paper_id)
            topics = [validate_topic(topic, paper_id) for topic in row.get("topics", [])]
            if not topics:
                raise ValueError(f"paper {paper_id}: no topics")
            topics = topics[:3]
            phylum_counts.update({topic["phylum"] for topic in topics})
            rows.append({"id": paper_id, "topics": topics})

    missing = sorted(set(range(1, EXPECTED_TOTAL + 1)) - seen)
    extra = sorted(paper_id for paper_id in seen if paper_id < 1 or paper_id > EXPECTED_TOTAL)
    if missing or extra:
        raise ValueError(f"missing={missing[:10]} ({len(missing)}), extra={extra[:10]} ({len(extra)})")

    rows.sort(key=lambda row: int(row["id"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"papers {len(rows)}")
    print(f"max_topics {max(len(row['topics']) for row in rows)}")
    print(json.dumps(phylum_counts.most_common(12), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise

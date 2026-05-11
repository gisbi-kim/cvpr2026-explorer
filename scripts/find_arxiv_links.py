import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "https://export.arxiv.org/api/query"
OPENALEX_URL = "https://api.openalex.org/works"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "cvpr2026-explorer/0.1"})


def norm_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"\$([^$]+)\$", r"\1", value)
    value = re.sub(r"\\[a-zA-Z]+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def token_set(value: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "via",
        "with",
    }
    return {t for t in norm_title(value).split() if len(t) > 2 and t not in stop}


def score_titles(query: str, candidate: str) -> float:
    q_norm = norm_title(query)
    c_norm = norm_title(candidate)
    if not q_norm or not c_norm:
        return 0.0
    if q_norm == c_norm:
        return 1.0
    q_tokens = token_set(query)
    c_tokens = token_set(candidate)
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = len(q_tokens & c_tokens)
    precision = overlap / len(c_tokens)
    recall = overlap / len(q_tokens)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    containment = min(len(q_norm), len(c_norm)) / max(len(q_norm), len(c_norm))
    if q_norm in c_norm or c_norm in q_norm:
        return max(f1, 0.92 * containment)
    return f1


def request_json(url: str, params: dict[str, str], timeout: int = 12) -> dict | None:
    try:
        response = SESSION.get(url, params=params, timeout=timeout)
        if response.status_code == 429:
            time.sleep(1)
            return None
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def request_xml(url: str, params: dict[str, str], timeout: int = 8) -> ET.Element | None:
    full_url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full_url, headers={"User-Agent": "cvpr2026-explorer/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return ET.fromstring(response.read())
    except Exception:
        return None


def arxiv_id_from_url(url: str) -> str:
    url = (url or "").strip()
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#\s]+)", url)
    if not match:
        return ""
    arxiv_id = match.group(1).replace(".pdf", "").strip("/")
    return arxiv_id


def arxiv_location(row: dict) -> tuple[str, str] | None:
    locations = []
    if row.get("primary_location"):
        locations.append(row["primary_location"])
    locations.extend(row.get("locations") or [])
    for loc in locations:
        urls = [loc.get("landing_page_url") or "", loc.get("pdf_url") or "", loc.get("id") or ""]
        raw_source = str(loc.get("raw_source_name") or "")
        source = loc.get("source") or {}
        source_name = str(source.get("display_name") or "")
        for url in urls:
            arxiv_id = arxiv_id_from_url(url)
            if arxiv_id:
                return arxiv_id, f"https://arxiv.org/abs/{arxiv_id}"
        if raw_source.lower() == "arxiv" or source_name.lower() == "arxiv":
            for url in urls:
                if url.startswith("https://openalex.org/"):
                    continue
                arxiv_id = arxiv_id_from_url(url)
                if arxiv_id:
                    return arxiv_id, f"https://arxiv.org/abs/{arxiv_id}"
    return None


def find_with_openalex(title: str) -> dict | None:
    data = request_json(
        OPENALEX_URL,
        {
            "search.title": title,
            "per-page": "8",
            "select": "id,title,publication_year,primary_location,locations",
        },
    )
    if not data:
        return None
    best = None
    for row in data.get("results", []):
        matched_title = row.get("title") or ""
        score = score_titles(title, matched_title)
        loc = arxiv_location(row)
        if not loc:
            continue
        arxiv_id, url = loc
        item = {
            "arxiv_id": arxiv_id,
            "url": url,
            "source": "openalex",
            "matched_title": matched_title,
            "score": round(score, 4),
        }
        if best is None or item["score"] > best["score"]:
            best = item
    if best and best["score"] >= 0.88:
        best["confidence"] = "high" if best["score"] >= 0.96 else "medium"
        return best
    return None


def find_with_semantic_scholar(title: str) -> dict | None:
    data = request_json(
        S2_URL,
        {
            "query": title,
            "limit": "5",
            "fields": "title,year,externalIds,url,openAccessPdf",
        },
    )
    if not data:
        return None
    best = None
    for row in data.get("data", []):
        matched_title = row.get("title") or ""
        score = score_titles(title, matched_title)
        arxiv_id = (row.get("externalIds") or {}).get("ArXiv")
        if not arxiv_id:
            continue
        item = {
            "arxiv_id": arxiv_id,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "source": "semantic-scholar",
            "matched_title": matched_title,
            "score": round(score, 4),
        }
        if best is None or item["score"] > best["score"]:
            best = item
    if best and best["score"] >= 0.88:
        best["confidence"] = "high" if best["score"] >= 0.96 else "medium"
        return best
    return None


def find_with_arxiv(title: str) -> dict | None:
    exact = request_xml(
        ARXIV_URL,
        {"search_query": f'ti:"{title}"', "start": "0", "max_results": "5"},
    )
    candidates = []
    if exact is not None:
        candidates.extend(parse_arxiv_entries(exact))

    if not candidates:
        tokens = sorted(token_set(title), key=len, reverse=True)[:7]
        if len(tokens) >= 3:
            query = " AND ".join(f"ti:{token}" for token in tokens)
            loose = request_xml(
                ARXIV_URL,
                {"search_query": query, "start": "0", "max_results": "5"},
            )
            if loose is not None:
                candidates.extend(parse_arxiv_entries(loose))

    best = None
    for candidate in candidates:
        score = score_titles(title, candidate["matched_title"])
        candidate["score"] = round(score, 4)
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    if best and best["score"] >= 0.9:
        best["confidence"] = "high" if best["score"] >= 0.97 else "medium"
        return best
    return None


def parse_arxiv_entries(root: ET.Element) -> list[dict]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        id_el = entry.find("atom:id", ns)
        if title_el is None or id_el is None:
            continue
        url = (id_el.text or "").strip()
        arxiv_id = url.rstrip("/").split("/")[-1]
        out.append(
            {
                "arxiv_id": arxiv_id,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "source": "arxiv-api",
                "matched_title": re.sub(r"\s+", " ", title_el.text or "").strip(),
            }
        )
    return out


def load_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--semantic-scholar", action="store_true")
    parser.add_argument("--arxiv-api", action="store_true")
    args = parser.parse_args()

    chunk_path = Path(args.chunk)
    output_path = Path(args.output)
    rows = json.loads(chunk_path.read_text(encoding="utf-8"))
    if args.limit:
        rows = rows[: args.limit]

    existing = load_existing(output_path)
    by_id = {int(row["id"]): row for row in existing if "id" in row}
    checked = set(by_id)

    for idx, paper in enumerate(rows, 1):
        paper_id = int(paper["id"])
        if paper_id in checked:
            continue
        title = paper.get("title", "")
        match = find_with_openalex(title)
        if match is None and args.semantic_scholar:
            match = find_with_semantic_scholar(title)
        if match is None and args.arxiv_api:
            match = find_with_arxiv(title)
        if match:
            by_id[paper_id] = {
                "id": paper_id,
                "title": title,
                **match,
            }
        if idx % 20 == 0:
            output_path.write_text(
                json.dumps(sorted(by_id.values(), key=lambda row: row["id"]), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"checked {idx}/{len(rows)} matched {len(by_id)}", flush=True)
        time.sleep(args.sleep)

    output_path.write_text(
        json.dumps(sorted(by_id.values(), key=lambda row: row["id"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"done checked {len(rows)} matched {len(by_id)} -> {output_path}", flush=True)


if __name__ == "__main__":
    main()

"""Build an exact affiliation -> region lookup table for CVPR 2026.

The ICRA explorer uses an exact lookup table for affiliation regions. This
script mirrors that workflow for CVPR:

1. Extract every unique affiliation from data/cvpr2026_papers.json.
2. Reuse the ICRA exact lookup table when an affiliation string matches.
3. Classify remaining strings with a conservative, ordered institution/country
   rule set.
4. Write an exact table used by scripts/build_html.py, plus review files for
   unresolved or ambiguous entries.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "cvpr2026_papers.json"
OUT_DIR = ROOT / "classification"
OUT_TABLE = OUT_DIR / "aff_region_table.json"
OUT_META = OUT_DIR / "aff_region_metadata.json"
OUT_REVIEW = OUT_DIR / "aff_region_review.csv"
OUT_COUNTS = OUT_DIR / "aff_region_counts.csv"
ICRA_TABLE = ROOT.parent / "icra2026-explorer" / "classification" / "aff_country_table.json"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("&amp;", "&")
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def has_word(text: str, phrase: str) -> bool:
    phrase_n = norm(phrase)
    if re.fullmatch(r"[a-z0-9]+", phrase_n):
        return re.search(rf"\b{re.escape(phrase_n)}\b", text) is not None
    return phrase_n in text


def load_affiliations() -> Counter[str]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    affiliations: Counter[str] = Counter()
    for item in data:
        for aff in str(item.get("institutions", "")).split(";"):
            aff = aff.strip()
            if aff:
                affiliations[aff] += 1
    return affiliations


def normalize_region(value: str) -> str:
    aliases = {
        "Hong Kong": "China",
        "Macau": "China",
        "China-HK-Macau": "China",
        "UK": "United Kingdom",
        "UAE": "United Arab Emirates",
        "Czech": "Czech Republic",
        "Unknown": "Other",
    }
    return aliases.get(str(value), str(value))


def load_icra_table() -> dict[str, str]:
    if not ICRA_TABLE.exists():
        return {}
    data = json.loads(ICRA_TABLE.read_text(encoding="utf-8"))
    return {k: normalize_region(v) for k, v in data.items()}


COUNTRY_NAME_HINTS: list[tuple[str, list[str]]] = [
    ("USA", ["united states", "usa", "u.s.a", "u.s.", "america"]),
    ("China", ["china", "hong kong", "macau", "macao", "prc"]),
    ("South Korea", ["south korea", "republic of korea", "korea"]),
    ("Japan", ["japan"]),
    ("Germany", ["germany", "deutschland"]),
    ("United Kingdom", ["united kingdom", "u.k.", "uk", "england", "scotland", "wales"]),
    ("France", ["france"]),
    ("Canada", ["canada"]),
    ("Singapore", ["singapore"]),
    ("Australia", ["australia"]),
    ("Switzerland", ["switzerland", "swiss"]),
    ("Italy", ["italy"]),
    ("Netherlands", ["netherlands", "holland"]),
    ("India", ["india"]),
    ("Israel", ["israel"]),
    ("Spain", ["spain"]),
    ("Sweden", ["sweden"]),
    ("Taiwan", ["taiwan"]),
    ("Austria", ["austria"]),
    ("Belgium", ["belgium"]),
    ("Denmark", ["denmark"]),
    ("Finland", ["finland"]),
    ("Norway", ["norway"]),
    ("Poland", ["poland"]),
    ("Portugal", ["portugal"]),
    ("Greece", ["greece"]),
    ("Ireland", ["ireland"]),
    ("Czech Republic", ["czech"]),
    ("Brazil", ["brazil"]),
    ("Mexico", ["mexico"]),
    ("Turkey", ["turkey", "turkiye"]),
    ("Saudi Arabia", ["saudi arabia", "kaust"]),
    ("United Arab Emirates", ["united arab emirates", "uae"]),
    ("Qatar", ["qatar"]),
]


ORG_HINTS: list[tuple[str, list[str]]] = [
    ("China", [
        "tsinghua", "peking university", "zhejiang university", "fudan", "shanghai jiao tong",
        "shanghai jiaotong", "ustc", "university of science and technology of china",
        "chinese academy", "institute of automation", "casia", "ucas", "sun yat-sen",
        "nanjing university", "harbin institute", "beihang", "wuhan university",
        "huazhong university", "xidian", "sichuan university", "tianjin university",
        "tongji", "renmin", "nankai", "southeast university", "hunan university",
        "beijing institute of technology", "beijing university of posts",
        "south china university", "central south university", "northwestern polytechnical",
        "shandong university", "xi'an jiaotong", "xian jiaotong", "dalian university",
        "capital normal", "east china normal", "east china university", "buaa",
        "scut", "sjtu", "hust", "hku", "hkust", "cuhk", "hong kong polytechnic",
        "city university of hong kong", "hong kong university", "huawei", "tencent",
        "alibaba", "bytedance", "byte dance", "kuaishou", "sensetime", "meituan",
        "baidu", "xiaomi", "oppo", "vivo", "jd.com", "ant group", "paddlepaddle",
        "westlake university", "shenzhen", "guangzhou", "shanghai ai laboratory",
        "shanghai artificial intelligence laboratory", "peng cheng", "mbzuai shanghai",
    ]),
    ("USA", [
        "stanford", "mit", "massachusetts institute", "carnegie mellon", "cmu", "berkeley",
        "university of california", "ucla", "ucsd", "uc santa", "uc merced", "uc davis",
        "university of washington", "university of wisconsin", "university of michigan",
        "university of illinois", "uiuc", "georgia tech", "gatech", "cornell", "columbia",
        "princeton", "harvard", "yale", "brown university", "duke university",
        "northwestern university", "purdue", "rutgers", "nyu", "new york university",
        "university of texas", "ut austin", "rice university", "university of maryland",
        "johns hopkins", "caltech", "usc", "university of southern california",
        "university of pennsylvania", "penn state", "virginia tech", "arizona state",
        "university of arizona", "university of minnesota", "university of florida",
        "university of utah", "stony brook", "northeastern university", "boston university",
        "university of rochester", "university of notre dame", "ohio state", "oregon state",
        "google", "deepmind", "meta", "facebook", "microsoft", "nvidia", "apple",
        "adobe", "amazon", "aws", "openai", "salesforce", "qualcomm", "intel",
        "ibm", "netflix", "snap", "waymo", "tesla", "uber", "roblox", "databricks",
        "anthropic", "xai", "mistral ai usa",
    ]),
    ("South Korea", [
        "kaist", "seoul national", "snu", "postech", "yonsei", "korea university",
        "hanyang", "sungkyunkwan", "skku", "unist", "gist", "dgist", "sogang",
        "ewha", "korea advanced institute", "naver", "samsung", "lg ai", "etri",
    ]),
    ("Singapore", [
        "national university of singapore", "nanyang technological", "ntu singapore",
        "a*star", "astar", "singapore management university", "s-lab", "grab",
    ]),
    ("Japan", [
        "university of tokyo", "tokyo institute", "tokyo university", "kyoto university",
        "osaka university", "tohoku university", "nagoya university", "waseda",
        "keio", "riken", "sony", "nec", "preferred networks", "aist",
    ]),
    ("Germany", [
        "tum", "technical university of munich", "university of tubingen", "tuebingen",
        "max planck", "rwth", "heidelberg", "fraunhofer", "university of bonn",
        "university of freiburg", "saarland", "tu darmstadt", "kit", "karlsruhe",
        "university of stuttgart", "hamburg", "bosch", "dfki",
    ]),
    ("United Kingdom", [
        "university of oxford", "oxford", "university of cambridge", "cambridge",
        "imperial college", "ucl", "university college london", "edinburgh",
        "university of surrey", "king's college", "kings college", "university of sheffield",
        "university of bristol", "university of bath", "warwick", "manchester",
        "queen mary", "durham university", "lancaster university", "cardiff",
    ]),
    ("France", [
        "inria", "cnrs", "sorbonne", "ecole polytechnique", "école polytechnique",
        "centrale", "paris-saclay", "universite paris", "université paris",
        "grenoble", "telecom paris", "institut polytechnique de paris", "ens paris",
    ]),
    ("Canada", [
        "university of toronto", "toronto", "university of waterloo", "waterloo",
        "mcgill", "ubc", "university of british columbia", "university of alberta",
        "universite de montreal", "université de montréal", "mila", "simon fraser",
        "concordia", "queen's university", "vector institute", "york university",
    ]),
    ("Australia", [
        "australian national", "university of sydney", "unsw", "monash", "university of melbourne",
        "university of adelaide", "rmit", "university of queensland", "uts", "university of technology sydney",
        "curtin university", "deakin", "anu",
    ]),
    ("Switzerland", ["eth", "epfl", "university of zurich", "zurich", "lausanne", "idiap"]),
    ("Italy", ["politecnico di milano", "politecnico di torino", "sapienza", "university of bologna", "university of trento", "university of padova", "iit italy", "genova"]),
    ("Netherlands", ["tu delft", "delft", "university of amsterdam", "eindhoven", "utrecht university", "leiden", "radboud", "wageningen"]),
    ("India", ["iit ", "iisc", "iiit", "indian institute", "ashoka university", "tata institute", "infosys", "wadhwani"]),
    ("Israel", ["technion", "hebrew university", "tel aviv", "weizmann", "bar-ilan", "ben-gurion"]),
    ("Spain", ["barcelona", "madrid", "upc", "universitat", "university of granada", "basque center", "vicomtech"]),
    ("Sweden", ["kth", "chalmers", "lund university", "uppsala", "linkoping", "liu sweden"]),
    ("Taiwan", ["national taiwan", "academia sinica", "national tsing hua", "national yang ming", "nycu", "nthu", "ntu taiwan", "mediatek"]),
    ("Austria", ["tu wien", "vienna", "graz university", "jku", "ista austria"]),
    ("Belgium", ["ku leuven", "kuleuven", "ugent", "ghent university", "uclouvain", "imec"]),
    ("Denmark", ["technical university of denmark", "aalborg", "aarhus", "university of copenhagen", "dtU".lower()]),
    ("Finland", ["aalto", "university of helsinki", "tampere university", "oulu"]),
    ("Norway", ["ntnu", "university of oslo", "university of bergen", "simula"]),
    ("Poland", ["warsaw university", "jagiellonian", "agh university", "polish academy"]),
    ("Portugal", ["university of porto", "instituto superior tecnico", "lisbon", "inesc"]),
    ("Brazil", ["university of sao paulo", "universidade", "usp brazil", "unicamp"]),
    ("Turkey", ["bilkent", "metu", "koc university", "koç university", "bogazici", "sabanci"]),
    ("Saudi Arabia", ["king abdullah", "kaust", "king saud"]),
    ("United Arab Emirates", ["mbzuai", "mohamed bin zayed", "khalifa university", "uae university"]),
    ("Qatar", ["qatar computing", "qatar university", "hbku"]),
]

ORG_HINTS.extend([
    ("China", [
        "northwest polytechnical", "xi'an university of electronic", "xian university of electronic",
        "beijing university of post", "chongqing university of post", "anhui university",
        "li auto", "wechat", "tiktok", "tik tok", "douyin", "dalian martime", "dalian maritime",
        "institute of computing technology", "kunmimg university", "kunming university",
        "beijing university of technology", "donghua university", "guangming laboratory",
        "hunan normal university", "lanzhou university", "xmu", "xiamen university",
        "zhejiang gongshang", "zhongguancun", "bigai", "beijing academy of artificial intelligence",
        "beingbeyond", "institute of information engineering", "remote sensing application",
        "jd ai", "jingdong", "kling ai", "huazhong agricultural", "megvii",
    ]),
    ("USA", [
        "michigan state", "texas a&m", "texas a & m", "umass", "massachusetts at amherst",
        "university of massachusetts", "north carolina at chapel hill", "unc chapel hill",
        "rochester institute", "dolby", "international business machines", "ibm",
        "oak ridge", "suny buffalo", "state university of new york at buffalo",
        "capital one", "cisco", "disney research", "disney", "emory university",
        "university of alabama at birmingham", "voxel51", "amd", "fair", "fa ir",
    ]),
    ("South Korea", [
        "sung kyun kwan", "dongguk", "electronics and telecommunications research institute",
        "etri", "soongsil",
    ]),
    ("Germany", [
        "mpi informatik", "german research center for ai", "university of munich",
        "lmu munich", "compvis", "ludwig maximilian",
    ]),
    ("Australia", ["la trobe", "canva"]),
    ("Bulgaria", ["insait", "sofia university", "kliment ohridski"]),
    ("Vietnam", ["vinai", "vinuniversity", "vin university"]),
    ("Japan", ["woven by toyota", "konica minolta", "ly corporation"]),
    ("France", ["valeo", "valeo.ai"]),
    ("United Arab Emirates", ["mohamed bin zayed university of artificial intelligence", "technology innovation institute", "tii", "g42"]),
    ("China", [
        "insta360", "xiaohongshu", "yunnan university", "didi research", "didi",
        "dalian minzu", "lenovo", "ningbo university", "shanda ai", "shanghai tech",
        "shanghaitech", "southern medical university", "wenzhou university", "baai",
        "北京人工智能研究院", "xiaobing", "beijing jiaotong", "deepglint", "hikvision",
        "international digital economy academy", "jd", "jd explore", "jiangxi normal",
        "knowin ai", "lishui university", "microsft research asia", "microsoft research asia",
        "minjiang university", "nanjing medical university", "northeast normal",
        "northwestern polytechinical", "qilu university", "shanghai ai lab",
        "shanghai university of finance", "shanghai university of science and technology",
        "sichuan agricultural", "state key laboratory", "teleai", "tianjin normal",
    ]),
    ("USA", [
        "university of tennessee", "university of virginia", "advanced micro devices",
        "applied intuition", "eastern institute of technology", "mitsubishi electric research labs",
        "merl", "oracle", "reality labs", "siemens corporate research", "snowflake",
        "tulane university", "university if colorado", "university of colorado",
        "university of houston", "independent researcher", "independent",
    ]),
    ("Germany", ["rheinisch westfalische", "rwth aachen", "saarlandes", "ruprecht-karls", "german cancer research center", "mpi for informatics"]),
    ("Italy", ["universita di bologna", "università di bologna"]),
    ("Canada", ["university of calgary", "ets montreal", "university of british columbia"]),
    ("United Kingdom", ["aberystwyth", "northumbria"]),
    ("Australia", ["edith cowan", "wollonong", "wollongong"]),
    ("South Korea", ["ajou university", "konkuk"]),
    ("Japan", ["fujitsu", "hokkaido university"]),
    ("India", ["international institute of information technology, bangalore"]),
    ("Russia", ["moscow state", "higher school of economics"]),
    ("France", ["ecole des ponts", "paristech"]),
    ("Greece", ["university of crete"]),
    ("Belgium", ["liege", "liège"]),
    ("Slovenia", ["ljubljana"]),
])

MANUAL_OVERRIDES = {
    "karlsruher institut fur technologie": "Germany",
    "beijing institute of general artificial intelligence": "China",
    "institute for computer science, artificial intelligence and technology": "Bulgaria",
    "inception institute of artificial intelligence": "United Arab Emirates",
    "shanghai aritifcal intelligence laboratory": "China",
    "thinking machines": "USA",
    "aiq": "United Arab Emirates",
    "beijing university": "China",
    "defense innovation institute, academy of military sciences (ams)": "China",
    "disneyresearch|studios": "USA",
    "hkbu": "China",
    "henan institute of science and technology": "China",
    "henan univeristy": "China",
    "mercedes-benz": "Germany",
    "new york university shanghai": "China",
    "shanghai academy of artificial intelligence for science": "China",
    "victoria university of wellington": "New Zealand",
    "washington university in st louis": "USA",
    "xi'an university": "China",
    "xi’an jiaotong-liverpool university": "China",
    "xi'an jiaotong-liverpool university": "China",
    "xi’an research institute of high technology": "China",
    "xi'an research institute of high technology": "China",
    "ecole de technologie superieure, universite du quebec": "Canada",
    "上海交通大学": "China",
    "腾讯科技（北京）有限公司": "China",
    "2077ai": "China",
    "360 ai institute": "China",
    "360 ai research": "China",
    "alipay (hangzhou) digital service technology co., ltd.": "China",
    "antgroup": "China",
    "antgroup group": "China",
    "australian institute for machine learning (aiml)": "Australia",
    "bits pilani, birla institute of technology and science": "India",
    "bupt": "China",
    "beijing electronic science and technology institute": "China",
    "beijing zitiao network technology co., ltd.": "China",
    "bournemouth university": "United Kingdom",
    "cispa helmholtz center for information security": "Germany",
    "cnr-isti": "Italy",
    "cowarobot": "China",
    "chongqing university of technology": "China",
    "chungang university": "South Korea",
    "city st george's, university of london": "United Kingdom",
    "college of computing, georgia institute of technology": "USA",
    "computer network information center": "China",
    "covariant": "USA",
    "cyberagent, inc.": "Japan",
    "denso it laboratory": "Japan",
    "deutsches krebsforschungszentrum": "Germany",
    "forschungszentrum julich": "Germany",
    "fujian university of technology": "China",
    "gbu/cuhksz": "China",
    "georgia state university": "USA",
    "guizhou university": "China",
    "google, tum": "USA",
    "google zurich": "Switzerland",
    "hangzhou alicloud apsara information technology co., ltd.": "China",
    "hithink royalflush information network co.,ltd.": "China",
    "honda r&d co., ltd.": "Japan",
    "huya inc": "China",
    "ieit systems (beijing) co., ltd.": "China",
    "institute of artificial intelligence, hefei comprehensive national science center": "China",
    "jiutian research": "China",
    "kujiale.com": "China",
    "kunlun": "China",
    "kyunghee university": "South Korea",
    "lightspeed studios": "China",
    "lix, polytechnique": "France",
    "luma ai": "USA",
    "mathematical institute for data science (minds) at jhu": "USA",
}


def classify_by_rules(aff: str) -> tuple[str, str, str]:
    text = norm(aff)

    if text in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[text], "manual-exact", "manual"

    if re.search(r"[\u4e00-\u9fff]", aff) and any(token in aff for token in ["大学", "北京", "上海", "腾讯", "有限公司", "研究院"]):
        return "China", "cjk-rule", "Chinese affiliation text"

    for country, hints in COUNTRY_NAME_HINTS:
        if any(has_word(text, h) for h in hints):
            return country, "country-name", next(h for h in hints if has_word(text, h))

    matches: list[tuple[str, str]] = []
    for country, hints in ORG_HINTS:
        for h in hints:
            if has_word(text, h):
                matches.append((country, h))
                break

    unique_countries = []
    for country, _ in matches:
        if country not in unique_countries:
            unique_countries.append(country)

    if len(unique_countries) == 1:
        return unique_countries[0], "rule", matches[0][1]

    if len(unique_countries) > 1:
        # If a combined affiliation string is written as "ETH Zurich / Microsoft"
        # or "Google, TUM", assign a representative region from the first segment
        # and keep all matches in metadata for audit.
        segments = [s for s in re.split(r"\s*(?:/|;|\band\b|\+)\s*", aff) if s.strip()]
        if len(segments) > 1:
            first_region, _, first_evidence = classify_by_rules(segments[0])
            if first_region not in {"Other", "Multiple"}:
                evidence = "|".join(f"{c}:{h}" for c, h in matches)
                return first_region, "combined-first-segment", f"{first_evidence}; all={evidence}"
        return "Multiple", "ambiguous", "|".join(f"{c}:{h}" for c, h in matches)

    return "Other", "unresolved", ""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    affiliations = load_affiliations()
    icra = load_icra_table()

    table: dict[str, str] = {}
    metadata: dict[str, dict[str, str | int]] = {}

    for aff, count in affiliations.most_common():
        if aff in icra:
            region, source, evidence = icra[aff], "icra-exact", "exact"
        else:
            region, source, evidence = classify_by_rules(aff)
        table[aff] = region
        metadata[aff] = {"region": region, "source": source, "evidence": evidence, "paper_count": count}

    OUT_TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    OUT_META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    with OUT_COUNTS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "unique_affiliations", "paper_affiliation_mentions"])
        for region, unique_count in Counter(table.values()).most_common():
            mention_count = sum(affiliations[a] for a, r in table.items() if r == region)
            writer.writerow([region, unique_count, mention_count])

    with OUT_REVIEW.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["affiliation", "paper_count", "region", "source", "evidence"])
        for aff, meta in sorted(metadata.items(), key=lambda kv: (-int(kv[1]["paper_count"]), kv[0])):
            if meta["region"] in {"Other", "Multiple"} or meta["source"] in {"unresolved", "ambiguous"}:
                writer.writerow([aff, meta["paper_count"], meta["region"], meta["source"], meta["evidence"]])

    summary = {
        "unique_affiliations": len(affiliations),
        "regions": Counter(table.values()).most_common(),
        "sources": Counter(str(m["source"]) for m in metadata.values()).most_common(),
        "review_rows": sum(1 for m in metadata.values() if m["region"] in {"Other", "Multiple"} or m["source"] in {"unresolved", "ambiguous"}),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

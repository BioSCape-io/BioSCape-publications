"""
Enrichment pipeline for BioSCape publications.

For each item in the Zotero collection:
  1. Extract DOI (from Zotero DOI field or URL patterns).
  2. If DOI present, look up the work in OpenAlex to obtain per-author
     canonical IDs, institutions, and country codes.
  3. If an abstract is present, classify the item across the three
     topic dimensions (ecosystem / taxa / method) using the classifier
     already defined in topic_modeling.py.

Two CSV caches are produced under ``dimension_analysis/``:

  - enriched_items.csv    one row per Zotero item
  - enriched_authors.csv  one row per (item, author) pair

The pipeline is incremental: on subsequent runs, only Zotero items
whose ``dateModified`` differs from the cached copy trigger a fresh
OpenAlex lookup or topic classification.

Environment variables:
  ZOTERO_API_KEY   (optional; public library works without)
  OPENALEX_MAILTO  (optional; enrolls calls in the OpenAlex "polite pool")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd
import requests
from pyzotero import zotero

# Configuration
LIBRARY_ID = "2810748"
LIBRARY_TYPE = "group"
TARGET_COLLECTION = "U4SW8TCS"
OUTPUT_DIR = "dimension_analysis"
ITEMS_CACHE = os.path.join(OUTPUT_DIR, "enriched_items.csv")
AUTHORS_CACHE = os.path.join(OUTPUT_DIR, "enriched_authors.csv")

OPENALEX_BASE = "https://api.openalex.org/works"
REQUEST_TIMEOUT = 30
REQUEST_SLEEP = 0.11  # be gentle even without a mailto

# Country codes we want to spotlight in the dashboard.
US_CODES = {"US"}
SA_CODES = {"ZA"}

# Columns of the per-item cache (order preserved on write).
ITEM_COLUMNS = [
    "zotero_key",
    "date_modified",
    "title",
    "item_type",
    "year",
    "url",
    "doi",
    "abstract",
    "openalex_id",
    "num_authors_openalex",
    "author_country_codes",  # semicolon-joined, one per author (may be empty)
    "has_us_author",
    "has_sa_author",
    "is_us_sa_collab",
    "openalex_status",  # "ok" | "no_doi" | "not_found" | "error"
    "ecosystem",
    "ecosystem_confidence",
    "ecosystem_sims",  # JSON: {category: similarity}
    "taxa",
    "taxa_confidence",
    "taxa_sims",
    "method",
    "method_confidence",
    "method_sims",
]

# Dimensions we expect on every classified item; used to detect cache rows
# that predate the per-category similarity columns.
TOPIC_DIMS = ("ecosystem", "taxa", "method")

# Curated corrections for records whose semantic score alone misses their
# substantive BioSCape topic. Keys are stable Zotero item identifiers.
TOPIC_OVERRIDES = {
    "BE727DXZ": {"taxa": "Plants"},
}

AUTHOR_COLUMNS = [
    "zotero_key",
    "author_position",  # 0-based ordering in authorship list
    "openalex_author_id",
    "display_name",
    "country_code",
    "institution",
]


# --------------------------------------------------------------------------- #
# DOI extraction
# --------------------------------------------------------------------------- #

# Patterns to pull a DOI out of a URL when the Zotero DOI field is empty.
# The generic DOI regex is used last as a catch-all.
_DOI_URL_PATTERNS = [
    re.compile(r"doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"onlinelibrary\.wiley\.com/doi/(?:abs/|full/)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"nature\.com/articles/([A-Za-z0-9\-]+)", re.IGNORECASE),
    re.compile(r"mdpi\.com/(\d{4}-\d{4}/\d+/\d+/\d+)", re.IGNORECASE),
    re.compile(r"sciencedirect\.com/science/article/(?:pii|abs/pii)/(S\w+)", re.IGNORECASE),
    re.compile(r"besjournals\.onlinelibrary\.wiley\.com/doi/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"esajournals\.onlinelibrary\.wiley\.com/doi/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"agupubs\.onlinelibrary\.wiley\.com/doi/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"bg\.copernicus\.org/articles/(\d+/\d+/\d+/\d+)", re.IGNORECASE),
    re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE),  # generic
]

# Domains where the URL path isn't directly a DOI but maps to a nature.com-style
# article ID that OpenAlex can still resolve when prefixed. Kept minimal to
# avoid false positives.
_NATURE_ARTICLE_PREFIX = "10.1038/"


def extract_doi(data: dict) -> str:
    """Return the DOI for a Zotero item, or empty string if not found."""
    doi = (data.get("DOI") or "").strip()
    if doi:
        return _normalize_doi(doi)

    # Some entries stash a DOI in the "extra" field as "DOI: 10.xxxx/..."
    extra = data.get("extra") or ""
    m = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", extra, re.IGNORECASE)
    if m:
        return _normalize_doi(m.group(0))

    url = data.get("url") or ""
    if not url:
        return ""

    for pat in _DOI_URL_PATTERNS:
        m = pat.search(url)
        if not m:
            continue
        captured = m.group(1)
        if pat.pattern.startswith(r"nature\.com"):
            # Nature short-article IDs (e.g., s44185-024-00071-5) resolve
            # to a DOI under the 10.1038 prefix.
            return _normalize_doi(_NATURE_ARTICLE_PREFIX + captured)
        if pat.pattern.startswith(r"sciencedirect"):
            # PII isn't a DOI; skip.
            continue
        if pat.pattern.startswith(r"mdpi"):
            # MDPI URLs contain the DOI segment after the base prefix but
            # only OpenAlex/CrossRef can canonicalize reliably; skip if we
            # can't reconstruct.
            continue
        if pat.pattern.startswith(r"bg\.copernicus"):
            continue
        return _normalize_doi(captured)

    return ""


def _normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.lower()


# --------------------------------------------------------------------------- #
# OpenAlex client
# --------------------------------------------------------------------------- #


@dataclass
class OpenAlexResult:
    status: str  # "ok" | "not_found" | "error"
    openalex_id: str = ""
    authors: list[dict] = field(default_factory=list)


class OpenAlexClient:
    def __init__(self, mailto: str | None = None, sleep_between: float = REQUEST_SLEEP):
        self.session = requests.Session()
        ua = "BioSCape-publications enrichment (+https://github.com/BioSCape-io/BioSCape-publications)"
        if mailto:
            ua += f"; mailto:{mailto}"
        self.session.headers["User-Agent"] = ua
        self.mailto = mailto
        self.sleep_between = sleep_between

    def fetch_by_doi(self, doi: str) -> OpenAlexResult:
        url = f"{OPENALEX_BASE}/https://doi.org/{doi}"
        params = {"mailto": self.mailto} if self.mailto else None
        try:
            resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            print(f"    OpenAlex request failed for {doi}: {exc}", file=sys.stderr)
            return OpenAlexResult(status="error")
        finally:
            time.sleep(self.sleep_between)

        if resp.status_code == 404:
            return OpenAlexResult(status="not_found")
        if resp.status_code != 200:
            print(f"    OpenAlex {resp.status_code} for {doi}", file=sys.stderr)
            return OpenAlexResult(status="error")

        payload = resp.json()
        authors = []
        for pos, authorship in enumerate(payload.get("authorships") or []):
            author = authorship.get("author") or {}
            institutions = authorship.get("institutions") or []
            if institutions:
                for inst in institutions:
                    authors.append(
                        {
                            "author_position": pos,
                            "openalex_author_id": (author.get("id") or "").replace(
                                "https://openalex.org/", ""
                            ),
                            "display_name": author.get("display_name") or "",
                            "country_code": (inst.get("country_code") or "").upper(),
                            "institution": inst.get("display_name") or "",
                        }
                    )
            else:
                authors.append(
                    {
                        "author_position": pos,
                        "openalex_author_id": (author.get("id") or "").replace(
                            "https://openalex.org/", ""
                        ),
                        "display_name": author.get("display_name") or "",
                        "country_code": "",
                        "institution": "",
                    }
                )
        return OpenAlexResult(
            status="ok",
            openalex_id=(payload.get("id") or "").replace("https://openalex.org/", ""),
            authors=authors,
        )


# --------------------------------------------------------------------------- #
# Zotero helpers
# --------------------------------------------------------------------------- #


def fetch_zotero_items() -> list[dict]:
    api_key = os.environ.get("ZOTERO_API_KEY", "")
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, api_key)
    all_items: list[dict] = []
    start = 0
    page_size = 100
    while True:
        page = zot.collection_items_top(TARGET_COLLECTION, limit=page_size, start=start)
        if not page:
            break
        all_items.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return all_items


def _reformat_year(date_str: str) -> str:
    if not date_str:
        return ""
    m = re.findall(r"\d{4}", date_str)
    return m[0] if m else ""


# --------------------------------------------------------------------------- #
# Cache I/O
# --------------------------------------------------------------------------- #


def load_items_cache() -> dict[str, dict]:
    if not os.path.exists(ITEMS_CACHE):
        return {}
    df = pd.read_csv(ITEMS_CACHE, keep_default_na=False, dtype=str)
    return {row["zotero_key"]: row.to_dict() for _, row in df.iterrows()}


def load_authors_cache() -> dict[str, list[dict]]:
    if not os.path.exists(AUTHORS_CACHE):
        return {}
    df = pd.read_csv(AUTHORS_CACHE, keep_default_na=False, dtype=str)
    by_key: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        by_key.setdefault(row["zotero_key"], []).append(row.to_dict())
    return by_key


def write_items_cache(rows: Iterable[dict]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.DataFrame(list(rows), columns=ITEM_COLUMNS)
    df.to_csv(ITEMS_CACHE, index=False)


def write_authors_cache(rows: Iterable[dict]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.DataFrame(list(rows), columns=AUTHOR_COLUMNS)
    df.to_csv(AUTHORS_CACHE, index=False)


# --------------------------------------------------------------------------- #
# Enrichment orchestration
# --------------------------------------------------------------------------- #


def summarize_countries(authors: list[dict]) -> tuple[str, bool, bool, bool]:
    """Return (semicolon-joined country codes, has_us, has_sa, is_us_sa)."""
    if not authors:
        return "", False, False, False
    # Deduplicate country_code per author position (multiple institutions per
    # author each get their own row; we care about the set per author for the
    # collab flag but we also record all codes for transparency).
    codes = [a.get("country_code", "") for a in authors]
    codes = [c for c in codes if c]
    per_author_codes = {}
    for a in authors:
        pos = a.get("author_position")
        cc = a.get("country_code", "")
        per_author_codes.setdefault(pos, set()).add(cc)
    has_us = any(US_CODES & s for s in per_author_codes.values())
    has_sa = any(SA_CODES & s for s in per_author_codes.values())
    return ";".join(codes), has_us, has_sa, has_us and has_sa


def build_item_row(
    item: dict,
    openalex: OpenAlexResult | None,
    cached_topics: dict | None,
) -> tuple[dict, list[dict]]:
    data = item["data"]
    key = data["key"]
    doi = extract_doi(data)
    abstract = (data.get("abstractNote") or "").strip()

    author_rows: list[dict] = []
    if openalex and openalex.status == "ok":
        codes_str, has_us, has_sa, is_collab = summarize_countries(openalex.authors)
        num_authors = len({a["author_position"] for a in openalex.authors})
        for a in openalex.authors:
            author_rows.append({"zotero_key": key, **a})
        oa_status = "ok"
        oa_id = openalex.openalex_id
    elif openalex and openalex.status in ("not_found", "error"):
        codes_str, has_us, has_sa, is_collab = "", False, False, False
        num_authors = 0
        oa_status = openalex.status
        oa_id = ""
    else:
        codes_str, has_us, has_sa, is_collab = "", False, False, False
        num_authors = 0
        oa_status = "no_doi"
        oa_id = ""

    topics = apply_topic_overrides(key, cached_topics or {})

    row = {
        "zotero_key": key,
        "date_modified": data.get("dateModified", ""),
        "title": data.get("title", ""),
        "item_type": data.get("itemType", ""),
        "year": _reformat_year(data.get("date", "")),
        "url": data.get("url", ""),
        "doi": doi,
        "abstract": abstract,
        "openalex_id": oa_id,
        "num_authors_openalex": num_authors,
        "author_country_codes": codes_str,
        "has_us_author": bool(has_us),
        "has_sa_author": bool(has_sa),
        "is_us_sa_collab": bool(is_collab),
        "openalex_status": oa_status,
        "ecosystem": topics.get("ecosystem", ""),
        "ecosystem_confidence": topics.get("ecosystem_confidence", ""),
        "ecosystem_sims": topics.get("ecosystem_sims", ""),
        "taxa": topics.get("taxa", ""),
        "taxa_confidence": topics.get("taxa_confidence", ""),
        "taxa_sims": topics.get("taxa_sims", ""),
        "method": topics.get("method", ""),
        "method_confidence": topics.get("method_confidence", ""),
        "method_sims": topics.get("method_sims", ""),
    }
    return row, author_rows


def cached_topics_from_row(row: dict) -> dict:
    out: dict = {}
    for dim in TOPIC_DIMS:
        out[dim] = row.get(dim, "")
        out[f"{dim}_confidence"] = row.get(f"{dim}_confidence", "")
        out[f"{dim}_sims"] = row.get(f"{dim}_sims", "")
    return out


def apply_topic_overrides(zotero_key: str, topics: dict) -> dict:
    """Apply curated topic corrections while preserving incremental caches."""
    overrides = TOPIC_OVERRIDES.get(zotero_key)
    if not overrides:
        return topics

    corrected = dict(topics)
    for dimension, category in overrides.items():
        corrected[dimension] = category
        corrected[f"{dimension}_confidence"] = 1.0
        corrected[f"{dimension}_sims"] = json.dumps({category: 1.0})
    return corrected


def _needs_openalex_refresh(cached: dict | None, item: dict) -> bool:
    if cached is None:
        return True
    return cached.get("date_modified", "") != item["data"].get("dateModified", "")


def _needs_topic_refresh(cached: dict | None, item: dict) -> bool:
    has_abstract = bool((item["data"].get("abstractNote") or "").strip())
    if not has_abstract:
        return False
    if cached is None:
        return True
    if cached.get("date_modified", "") != item["data"].get("dateModified", ""):
        return True
    # Refresh if any expected topic field is missing (e.g., cache pre-dates
    # the per-category similarity columns).
    for dim in TOPIC_DIMS:
        if not cached.get(dim) or not cached.get(f"{dim}_sims"):
            return True
    return False


def _classify_topics(items_needing_topics: list[dict]) -> dict[str, dict]:
    """Run the semantic classifier on the given Zotero items; return a
    dict keyed by zotero_key with the six topic fields."""
    if not items_needing_topics:
        return {}
    # Delayed import: SentenceTransformer + torch are heavy and only needed
    # when at least one item requires classification.
    from topic_modeling import classify_documents_by_semantic_similarity

    df = pd.DataFrame(
        [
            {
                "zotero_key": it["data"]["key"],
                "title": it["data"].get("title", ""),
                "abstract": (it["data"].get("abstractNote") or "").strip(),
            }
            for it in items_needing_topics
        ]
    )
    df = classify_documents_by_semantic_similarity(df)

    # Discover the per-category similarity columns produced by
    # classify_documents_by_semantic_similarity (e.g., ecosystem_Marine_similarity).
    sim_cols = {dim: [] for dim in TOPIC_DIMS}
    for col in df.columns:
        for dim in TOPIC_DIMS:
            prefix = f"{dim}_"
            suffix = "_similarity"
            if col.startswith(prefix) and col.endswith(suffix):
                cat = col[len(prefix): -len(suffix)]
                sim_cols[dim].append((cat, col))
                break

    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        entry: dict = {}
        for dim in TOPIC_DIMS:
            entry[dim] = row.get(dim, "")
            entry[f"{dim}_confidence"] = float(
                row.get(f"{dim}_confidence", 0.0) or 0.0
            )
            sims = {
                cat: float(row[col]) for cat, col in sim_cols[dim]
            }
            entry[f"{dim}_sims"] = json.dumps(sims, sort_keys=True)
        out[row["zotero_key"]] = entry
    return out


def enrich(
    force: bool = False,
    mailto: str | None = None,
) -> tuple[list[dict], list[dict]]:
    print("Fetching Zotero collection ...", flush=True)
    items = fetch_zotero_items()
    print(f"  {len(items)} items in collection", flush=True)

    items_cache = {} if force else load_items_cache()
    authors_cache = {} if force else load_authors_cache()

    client = OpenAlexClient(mailto=mailto or os.environ.get("OPENALEX_MAILTO"))

    # First pass: determine what needs OpenAlex + topic refresh.
    items_needing_oa: list[dict] = []
    items_needing_topics: list[dict] = []
    for item in items:
        key = item["data"]["key"]
        cached = items_cache.get(key)
        if _needs_openalex_refresh(cached, item):
            items_needing_oa.append(item)
        if _needs_topic_refresh(cached, item):
            items_needing_topics.append(item)

    print(
        f"  {len(items_needing_oa)} item(s) need OpenAlex lookup; "
        f"{len(items_needing_topics)} need topic classification.",
        flush=True,
    )

    # OpenAlex lookups.
    openalex_by_key: dict[str, OpenAlexResult] = {}
    for i, item in enumerate(items_needing_oa, start=1):
        data = item["data"]
        key = data["key"]
        doi = extract_doi(data)
        if not doi:
            openalex_by_key[key] = OpenAlexResult(status="")  # marker: no_doi
            continue
        print(f"  [{i}/{len(items_needing_oa)}] OpenAlex: {doi}", flush=True)
        openalex_by_key[key] = client.fetch_by_doi(doi)

    # Topic classification (batched).
    topics_by_key = _classify_topics(items_needing_topics)

    # Assemble rows for every item.
    new_item_rows: list[dict] = []
    new_author_rows: list[dict] = []
    for item in items:
        key = item["data"]["key"]
        cached = items_cache.get(key)

        if key in openalex_by_key:
            oa = openalex_by_key[key]
            if oa.status == "":  # sentinel meaning we skipped due to missing DOI
                oa = None
        else:
            # Reuse cached OpenAlex data by reconstructing authors from
            # the cached authors CSV; item-level fields are already stored.
            oa = None

        if key in topics_by_key:
            topics = topics_by_key[key]
        else:
            topics = cached_topics_from_row(cached) if cached else {}

        row, author_rows = build_item_row(item, oa, topics)

        # If we didn't just refresh OpenAlex, keep the previously cached
        # item-level OpenAlex fields and author rows.
        if oa is None and cached is not None:
            for f in (
                "openalex_id",
                "num_authors_openalex",
                "author_country_codes",
                "has_us_author",
                "has_sa_author",
                "is_us_sa_collab",
                "openalex_status",
            ):
                row[f] = cached.get(f, row[f])
            author_rows = authors_cache.get(key, [])
            # Ensure the author rows carry the current key (they already do,
            # but be defensive when the CSV was hand-edited).
            for ar in author_rows:
                ar["zotero_key"] = key

        # Coerce booleans back to bool (CSV read gives strings).
        for f in ("has_us_author", "has_sa_author", "is_us_sa_collab"):
            v = row[f]
            if isinstance(v, str):
                row[f] = v.strip().lower() in {"true", "1", "yes"}

        new_item_rows.append(row)
        new_author_rows.extend(author_rows)

    write_items_cache(new_item_rows)
    write_authors_cache(new_author_rows)
    print(
        f"Wrote {ITEMS_CACHE} ({len(new_item_rows)} items) and "
        f"{AUTHORS_CACHE} ({len(new_author_rows)} author rows).",
        flush=True,
    )
    return new_item_rows, new_author_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the cache and re-enrich every item.",
    )
    parser.add_argument(
        "--mailto",
        default=None,
        help="Email address for the OpenAlex polite pool (defaults to $OPENALEX_MAILTO).",
    )
    args = parser.parse_args()
    enrich(force=args.force, mailto=args.mailto)


if __name__ == "__main__":
    main()

"""Build index.html from the Zotero collection + enrichment CSVs.

Adds three topic columns (Ecosystem, Taxa, Method) as badge chips, and
injects a JSON stats blob for the front-end dashboard (unique authors,
US/SA breakdown, US-SA collaboration rate, topic distribution).
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter

import dateparser
import pandas as pd
from pyzotero import zotero

# Written with assistance from ChatGPT

# Get the API key from the environment variable
# API key seems to be unnecessary for public libraries
API_KEY = os.environ.get('ZOTERO_API_KEY', "")
LIBRARY_ID = "2810748"
LIBRARY_TYPE = "group"
TARGET_COLLECTION = "U4SW8TCS"
AUTHOR_COUNT_THRESHOLD = 3
REPLACE_TOKEN = '<!-- TABLE_CONTENT -->'
STATS_TOKEN = '<!-- STATS_JSON -->'

# Enrichment cache locations (see enrich_publications.py).
OUTPUT_DIR = "dimension_analysis"
ITEMS_CACHE = os.path.join(OUTPUT_DIR, "enriched_items.csv")
AUTHORS_CACHE = os.path.join(OUTPUT_DIR, "enriched_authors.csv")

# Topic tagging: include the top category plus any others whose similarity
# is within TOPIC_TAG_MARGIN of the top. When two categories are this close
# we surface both instead of collapsing them into an opaque "Mixed" bucket.
# Per-dimension: taxa scores are tightly bunched so a tighter margin is
# needed to avoid spurious secondary tags.
TOPIC_TAG_MARGIN = {
    'ecosystem': 0.05,
    'taxa': 0.025,
    'method': 0.05,
}

# Absolute similarity floor per dimension. If the top similarity for a
# dimension falls below the floor, we treat the paper as not really about
# that dimension and drop all tags for it. This prevents the classifier from
# force-fitting (e.g.) a "Plantae" tag onto an atmospheric-correction paper
# just because Plantae was the least-worst taxonomic match.
TOPIC_MIN_SIMILARITY = {
    'ecosystem': 0.25,
    'taxa': 0.25,
    'method': 0.10,
}

# Dimension categories to always include in the dashboard distribution
# (even when zero) so charts stay comparable across builds. Order here
# also drives the badge display order when multiple tags apply.
TOPIC_CATEGORIES = {
    'ecosystem': [
        'Terrestrial',
        'Freshwater',
        'Estuarine/Coastal',
        'Marine',
    ],
    'taxa': [
        'Plants & vegetation',
        'Phytoplankton',
        'Vocal fauna',
    ],
    'method': [
        'Field observation',
        'Remote sensing',
        'Machine learning',
        'Molecular / eDNA',
        'Statistical modeling',
        'Physics-based modeling',
        'Perspective & synthesis',
    ],
}

TOPIC_COLUMNS = [
    ('Ecosystem', 'ecosystem'),
    ('Taxa', 'taxa'),
    ('Method', 'method'),
]


def fix_word_spaces(s: str) -> str:
    words = []
    last_i = 0
    for i, c in enumerate(s):
        if c.isupper():
            words.append(s[last_i:i])
            last_i = i

    if last_i < len(s):
        words.append(s[last_i:])

    return ' '.join([w.capitalize() for w in words])


def reformat_date(date_str: str) -> str:
    if not date_str:
        return ''

    formatted_date = None

    # First try parsing with python built-in datatime parser
    datetime_obj = dateparser.parse(date_str)
    if datetime_obj is not None:
        # Format it as YYYY
        formatted_date = datetime_obj.strftime('%Y')

    # Backup: just take the 4-digit number
    if formatted_date is None:
        match = re.findall(r"\d{4}", date_str)
        if match:
            formatted_date = match[0]
            print(f"Using backup date parsing for {date_str} -> {formatted_date}")
        else:
            formatted_date = ''

    return formatted_date


def _topic_labels(row: dict | None, dim: str) -> list[str]:
    """Return every category whose similarity is within TOPIC_TAG_MARGIN of
    the top category for this dimension. Empty list means "no data" (no
    abstract classified)."""
    if not row:
        return []
    sims_raw = row.get(f'{dim}_sims', '') or ''
    if sims_raw:
        try:
            sims = json.loads(sims_raw)
        except (TypeError, ValueError):
            sims = {}
    else:
        sims = {}
    if sims:
        # Filter to categories we know about (defensive) and pick everything
        # within the margin of the top score.
        pairs = [(cat, float(v)) for cat, v in sims.items()]
        if not pairs:
            return []
        pairs.sort(key=lambda p: p[1], reverse=True)
        top_score = pairs[0][1]
        # Below the absolute floor, treat this dimension as not applicable.
        if top_score < TOPIC_MIN_SIMILARITY.get(dim, 0.0):
            return []
        cutoff = top_score - TOPIC_TAG_MARGIN.get(dim, 0.05)
        strong = [cat for cat, v in pairs if v >= cutoff]
        # Preserve the canonical display order when possible so multiple
        # badges appear consistently across rows.
        canonical = TOPIC_CATEGORIES.get(dim, [])
        ordered = [c for c in canonical if c in strong]
        # Include any strong categories that don't appear in the canonical list.
        for cat in strong:
            if cat not in ordered:
                ordered.append(cat)
        return ordered
    # Fall back to the single stored top pick when raw similarities are not
    # available (e.g., cache row predates the sims column).
    label = str(row.get(dim, '') or '').strip()
    if not label or label.lower() == 'mixed':
        return []
    return [label]


def _topic_badges(labels: list[str], dim: str) -> str:
    if not labels:
        return '<span class="topic-badge topic-empty">—</span>'
    chips = []
    for label in labels:
        safe = html.escape(label)
        slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
        chips.append(
            f'<span class="topic-badge topic-{dim} topic-{dim}-{slug}">{safe}</span>'
        )
    return '<span class="topic-badges">' + ''.join(chips) + '</span>'


def process_input(d: dict, enrichment: dict | None) -> dict:
    def process_creators(creators: list) -> str:
        formatted = []
        for c in creators:
            first_name = c.get('firstName', None)
            last_name = c.get('lastName', None)
            name = c.get('name', None)

            if first_name and last_name:
                formatted.append(f"{first_name} {last_name}")
            elif first_name:
                formatted.append(first_name)
            elif last_name:
                formatted.append(last_name)
            elif name:
                formatted.append(name)

        if len(formatted) < AUTHOR_COUNT_THRESHOLD:
            return ', '.join(formatted)
        else:
            return f"<span title=\"{', '.join(formatted)}\">{formatted[0]} et al.</span>"

    # map different fields to the 'source' column
    def get_source(data: dict) -> str:
        if data["itemType"] == "journalArticle":
            return data.get('publicationTitle', '')
        elif data["itemType"] == "conferencePaper":
            a = data.get('publicationTitle', '')
            # Some entries have conferenceName instead of publicationTitle
            if len(a) == 0:
                a = data.get('conferenceName', '')
            # Some entries have proceedingsTitle instead
            if len(a) == 0:
                a = data.get('proceedingsTitle', '')
            return a
        elif data["itemType"] == "presentation":
            return data.get('meetingName', '')
        elif data["itemType"] == "preprint":
            return data.get('repository', '')
        elif data["itemType"] == "dataset":
            return data.get('repository', '')
        elif data["itemType"] == "thesis":
            return data.get('university', '')
        else:
            return ''

    data = d['data']
    title = data.get('title', '')
    url = data.get('url', '')

    row = {
        'Title': f'<a target="_blank" rel="noopener noreferrer" href=\"{url}\">{title}</a>' if len(url) > 0 else title,
        'Item Type': fix_word_spaces(data['itemType']),
        'Journal/Conference/Source': get_source(data),
        'Creators': process_creators(data.get('creators', [])),
        'Year': reformat_date(data.get('date', '')),
    }

    for label, dim in TOPIC_COLUMNS:
        row[label] = _topic_badges(_topic_labels(enrichment, dim), dim)

    return row


zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)


def fetch_all_collection_items_top(collection_key: str, page_size: int = 100) -> list:
    all_items = []
    start = 0

    while True:
        page = zot.collection_items_top(collection_key, limit=page_size, start=start)
        if not page:
            break

        all_items.extend(page)

        if len(page) < page_size:
            break

        start += page_size

    return all_items


# --------------------------------------------------------------------------- #
# Enrichment loading + stats
# --------------------------------------------------------------------------- #


def _load_enrichment() -> tuple[dict, pd.DataFrame]:
    """Return (items_by_key, authors_df). Missing files → empty."""
    if os.path.exists(ITEMS_CACHE):
        items_df = pd.read_csv(ITEMS_CACHE, keep_default_na=False, dtype=str)
        items_by_key = {row["zotero_key"]: row.to_dict() for _, row in items_df.iterrows()}
    else:
        items_by_key = {}

    if os.path.exists(AUTHORS_CACHE):
        authors_df = pd.read_csv(AUTHORS_CACHE, keep_default_na=False, dtype=str)
    else:
        authors_df = pd.DataFrame(
            columns=[
                "zotero_key",
                "author_position",
                "openalex_author_id",
                "display_name",
                "country_code",
                "institution",
            ]
        )
    return items_by_key, authors_df


def _run_enrichment(force: bool = False) -> None:
    """Invoke enrich_publications.py as a subprocess so heavy imports
    (torch, sentence_transformers) don't touch this process."""
    cmd = [sys.executable, "enrich_publications.py"]
    if force:
        cmd.append("--force")
    print(f"Running enrichment: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def _bool(v):
    return str(v).strip().lower() in {"true", "1", "yes"}


def _compute_stats(
    items: list,
    items_by_key: dict,
    authors_df: pd.DataFrame,
) -> dict:
    """Assemble the dashboard stats payload."""

    total_outputs = len(items)

    # Author scope: only items with a DOI *and* a successful OpenAlex lookup.
    doi_keys = {
        k for k, r in items_by_key.items()
        if r.get("doi") and r.get("openalex_status") == "ok"
    }
    outputs_with_doi = len(doi_keys)

    doi_items_df = pd.DataFrame(
        [items_by_key[k] for k in doi_keys if k in items_by_key]
    )

    # Distinct OpenAlex author IDs across DOI'd items (deduplicates authors
    # who appear on multiple papers).
    doi_authors_df = authors_df[authors_df["zotero_key"].isin(doi_keys)]
    unique_author_ids = doi_authors_df.loc[
        doi_authors_df["openalex_author_id"] != "", "openalex_author_id"
    ].unique()
    unique_authors = int(len(unique_author_ids))

    # Country breakdown: count distinct (author_id, country_code) pairs
    # so a single author affiliated with US and ZA counts once per country.
    country_pairs = doi_authors_df[
        (doi_authors_df["openalex_author_id"] != "")
        & (doi_authors_df["country_code"] != "")
    ][["openalex_author_id", "country_code"]].drop_duplicates()
    country_counts = Counter(country_pairs["country_code"].tolist())
    country_breakdown = [
        {"country": cc, "count": n}
        for cc, n in country_counts.most_common()
    ]

    # Per-paper collaboration mix.
    us_only = sa_only = us_sa_collab = intl_other = neither = 0
    if not doi_items_df.empty:
        for _, r in doi_items_df.iterrows():
            has_us = _bool(r.get("has_us_author"))
            has_sa = _bool(r.get("has_sa_author"))
            codes = [c for c in (r.get("author_country_codes") or "").split(";") if c]
            has_other = any(c not in ("US", "ZA") for c in codes)
            if has_us and has_sa:
                us_sa_collab += 1
            elif has_us and not has_sa and not has_other:
                us_only += 1
            elif has_sa and not has_us and not has_other:
                sa_only += 1
            elif has_us or has_sa or has_other:
                intl_other += 1
            else:
                neither += 1

    us_sa_collab_pct = (
        round(100.0 * us_sa_collab / outputs_with_doi, 1)
        if outputs_with_doi else 0.0
    )

    # Topic distribution across ALL items with a classification (whether or
    # not they have a DOI). The dashboard donut uses the *top pick only*
    # per item so the slices sum to the number of classified items and are
    # easy to interpret. Multi-tag rendering still applies in the table.
    topic_distribution = {dim: Counter() for _, dim in TOPIC_COLUMNS}
    for row in items_by_key.values():
        for _, dim in TOPIC_COLUMNS:
            labels = _topic_labels(row, dim)
            if not labels:
                continue
            topic_distribution[dim][labels[0]] += 1

    # Serialize in a stable category order.
    topic_distribution_out = {}
    for _, dim in TOPIC_COLUMNS:
        counts = topic_distribution[dim]
        ordered = []
        seen = set()
        for cat in TOPIC_CATEGORIES.get(dim, []):
            ordered.append({"category": cat, "count": int(counts.get(cat, 0))})
            seen.add(cat)
        for cat, n in counts.items():
            if cat not in seen:
                ordered.append({"category": cat, "count": int(n)})
        topic_distribution_out[dim] = ordered

    outputs_classified = sum(
        1 for row in items_by_key.values()
        if any(_topic_labels(row, dim) for _, dim in TOPIC_COLUMNS)
    )

    # Authorships × role, grouped as US / ZA / Rest of world. Uses the same
    # first / last / middle logic as author_contribution.py.
    role_by_group = _authorships_by_group_role()

    return {
        "total_outputs": total_outputs,
        "outputs_with_doi": outputs_with_doi,
        "outputs_classified": outputs_classified,
        "unique_authors": unique_authors,
        "us_only_papers": us_only,
        "sa_only_papers": sa_only,
        "us_sa_collab_papers": us_sa_collab,
        "international_other_papers": intl_other,
        "unaffiliated_papers": neither,
        "us_sa_collab_pct": us_sa_collab_pct,
        "country_breakdown": country_breakdown,
        "topic_distribution": topic_distribution_out,
        "authorships_by_group_role": role_by_group,
    }


def _authorships_by_group_role() -> dict:
    """Build a stacked-bar-friendly summary of authorships aggregated as
    US / South Africa / Rest of world, split by first / last / middle role.
    Delegates to author_contribution.analyze() so the numbers on the page
    always match the CLI report."""
    try:
        from author_contribution import ROLES, analyze
    except Exception as exc:
        print(f"Warning: authorship rollup unavailable ({exc}).", file=sys.stderr)
        return {}

    analysis = analyze()
    per_country = analysis.get("authorships", {})

    groups = {"US": "US", "ZA": "South Africa", "REST": "Rest of world"}
    totals = {label: {role: 0 for role in ROLES} for label in groups.values()}
    for cc, counts in per_country.items():
        if cc == "US":
            bucket = groups["US"]
        elif cc == "ZA":
            bucket = groups["ZA"]
        else:
            bucket = groups["REST"]
        for role in ROLES:
            totals[bucket][role] += int(counts.get(role, 0))

    return {
        "groups": [groups["US"], groups["ZA"], groups["REST"]],
        "roles": list(ROLES),
        "counts": {
            label: [totals[label][role] for role in ROLES]
            for label in totals
        },
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip running enrich_publications.py before building.",
    )
    parser.add_argument(
        "--force-enrich",
        action="store_true",
        help="Re-enrich every item (passes --force to enrich_publications.py).",
    )
    args = parser.parse_args()

    if not args.skip_enrich:
        try:
            _run_enrichment(force=args.force_enrich)
        except subprocess.CalledProcessError as exc:
            print(
                f"Warning: enrichment step failed ({exc}); building with "
                "existing cache.",
                file=sys.stderr,
            )

    items = fetch_all_collection_items_top(TARGET_COLLECTION)
    items_by_key, authors_df = _load_enrichment()

    input_list = [process_input(e, items_by_key.get(e['data']['key'])) for e in items]

    # Store lines of HTML table in a list
    table_lines = []
    # Create the table header
    if input_list:
        header = input_list[0].keys()
        table_lines.append('<thead>')
        table_lines.append('<tr>')
        for col in header:
            table_lines.append(f'<th class="column-{col}">{col}</th>')
        table_lines.append('</tr>')
        table_lines.append('</thead>')

    # Create table rows for each input element
    table_lines.append('<tbody id="tableBody">')
    for row in input_list:
        table_lines.append('<tr>')
        for key, value in row.items():
            table_lines.append(f'<td class="column-{key}">{value}</td>')
        table_lines.append('</tr>')
    table_lines.append('</tbody>')

    stats = _compute_stats(items, items_by_key, authors_df)
    stats_json = json.dumps(stats)

    # Read the template file into list of lines
    with open('template.html', 'r') as f:
        template_lines = f.readlines()

    # Write the output file
    with open('index.html', 'w') as f:
        for line in template_lines:
            stripped = line.strip()
            if stripped == REPLACE_TOKEN:
                f.write(line.rstrip().replace(REPLACE_TOKEN, ''))  # preserve indentation
                f.writelines(table_lines)
                f.write('\n')
            elif STATS_TOKEN in line:
                f.write(line.replace(STATS_TOKEN, stats_json))
            else:
                f.write(line)

    print(
        "Wrote index.html "
        f"({stats['total_outputs']} items, {stats['unique_authors']} unique authors, "
        f"{stats['us_sa_collab_pct']}% US-SA collabs).",
        flush=True,
    )


if __name__ == "__main__":
    main()

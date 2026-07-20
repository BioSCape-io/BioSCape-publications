"""Author contribution analysis for BioSCape outputs.

Reads the enrichment caches produced by enrich_publications.py and prints
a breakdown of authorships and unique people by country and role:

  - first author (author_position == 0)
  - last author  (author_position == num_authors - 1)
  - middle       (everyone else)

Sole-author papers count once, as first author. Authors affiliated with
institutions in multiple countries on the same paper count in every one
of those countries (so an author with dual US+ZA affiliations shows up
in both US and ZA totals).

Run:
    python author_contribution.py
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict

import pandas as pd

OUTPUT_DIR = "dimension_analysis"
ITEMS_CACHE = os.path.join(OUTPUT_DIR, "enriched_items.csv")
AUTHORS_CACHE = os.path.join(OUTPUT_DIR, "enriched_authors.csv")

ROLES = ("first", "last", "middle")


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    items = pd.read_csv(ITEMS_CACHE, keep_default_na=False, dtype=str)
    authors = pd.read_csv(AUTHORS_CACHE, keep_default_na=False, dtype=str)
    return items, authors


def _role_for(position: int, num_authors: int) -> str:
    if num_authors <= 1:
        return "first"
    if position == 0:
        return "first"
    if position == num_authors - 1:
        return "last"
    return "middle"


def _bool(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def analyze() -> dict:
    items, authors = _load()

    # Scope: DOI'd items with a successful OpenAlex lookup.
    doi_items = items[
        (items.doi != "") & (items.openalex_status == "ok")
    ].copy()
    doi_items["num_authors"] = pd.to_numeric(
        doi_items["num_authors_openalex"], errors="coerce"
    ).fillna(0).astype(int)
    num_authors_by_key = dict(zip(doi_items.zotero_key, doi_items.num_authors))

    doi_keys = set(doi_items.zotero_key)
    doi_authors = authors[authors.zotero_key.isin(doi_keys)].copy()
    doi_authors["author_position"] = pd.to_numeric(
        doi_authors.author_position, errors="coerce"
    ).fillna(-1).astype(int)

    # authorships_by_country_role[country][role] = count of (paper, author)
    # pairs from that country in that role. Bridge authors contribute to
    # every country they're affiliated with on that paper.
    authorships: dict[str, dict[str, int]] = defaultdict(
        lambda: {r: 0 for r in ROLES}
    )
    # unique_by_country_role[country][role] = set of OpenAlex author IDs
    # who have ever held that role from that country.
    unique_people: dict[str, dict[str, set]] = defaultdict(
        lambda: {r: set() for r in ROLES}
    )

    # For bridge-author reporting: openalex_author_id -> {countries, roles, papers, names}
    bridge_activity: dict[str, dict] = defaultdict(
        lambda: {
            "countries": set(),
            "roles": {r: 0 for r in ROLES},
            "papers": set(),
            "names": Counter(),
        }
    )

    # For "leadership" metrics keyed by paper.
    paper_leadership: dict[str, dict] = {}

    # Group author rows by (paper, position); each group represents one
    # authorship (possibly across multiple institutions/countries).
    for key, group in doi_authors.groupby("zotero_key"):
        num_authors = num_authors_by_key.get(key, 0)
        first_countries: set[str] = set()
        last_countries: set[str] = set()
        for position, subgroup in group.groupby("author_position"):
            role = _role_for(int(position), int(num_authors))
            countries = {
                c for c in subgroup.country_code.tolist() if c
            }
            author_ids = [
                aid for aid in subgroup.openalex_author_id.tolist() if aid
            ]
            author_id = author_ids[0] if author_ids else ""
            display_name = subgroup.display_name.iloc[0] if len(subgroup) else ""

            for cc in countries:
                authorships[cc][role] += 1
                if author_id:
                    unique_people[cc][role].add(author_id)

            if role == "first":
                first_countries |= countries
            if role == "last":
                last_countries |= countries

            if author_id and len(countries) > 1:
                entry = bridge_activity[author_id]
                entry["countries"] |= countries
                entry["roles"][role] += 1
                entry["papers"].add(key)
                if display_name:
                    entry["names"][display_name] += 1

        paper_leadership[key] = {
            "first_countries": first_countries,
            "last_countries": last_countries,
            "any_countries": {
                c for c in
                (doi_items.set_index("zotero_key").loc[key, "author_country_codes"] or "").split(";")
                if c
            },
        }

    return {
        "num_doi_items": int(len(doi_items)),
        "num_unique_authors": int(
            len({a for a in doi_authors.openalex_author_id if a})
        ),
        "authorships": {k: dict(v) for k, v in authorships.items()},
        "unique_people": {
            k: {r: len(s) for r, s in v.items()}
            for k, v in unique_people.items()
        },
        "bridge_activity": bridge_activity,
        "paper_leadership": paper_leadership,
    }


def _fmt_pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:5.1f}%" if total else "  0.0%"


def _print_country_table(
    title: str,
    per_country: dict[str, dict[str, int]],
    caveat: str = "",
) -> None:
    rows = []
    for cc, counts in per_country.items():
        total = sum(counts.values())
        rows.append((cc, counts["first"], counts["last"], counts["middle"], total))
    rows.sort(key=lambda r: r[4], reverse=True)

    print(f"\n{title}")
    if caveat:
        print(f"  ({caveat})")
    print(f"  {'Country':<8}  {'First':>6}  {'Last':>6}  {'Middle':>7}  {'Total':>6}")
    print(f"  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*7}  {'-'*6}")
    for cc, first, last, middle, total in rows:
        print(
            f"  {cc:<8}  {first:>6}  {last:>6}  {middle:>7}  {total:>6}"
        )


def print_report(analysis: dict) -> None:
    n_items = analysis["num_doi_items"]
    print(
        f"BioSCape author contribution index "
        f"({n_items} DOI'd outputs, "
        f"{analysis['num_unique_authors']} unique authors)"
    )

    _print_country_table(
        "Authorships by country \u00d7 role",
        analysis["authorships"],
        "authors with dual affiliations count in each country",
    )

    _print_country_table(
        "Unique people by country \u00d7 role",
        {k: v for k, v in analysis["unique_people"].items()},
        "distinct OpenAlex authors who have ever held that role from this country",
    )

    # Leadership summary.
    us_led = sa_led = us_sa_led = us_and_sa_led = neither_led = 0
    for _, p in analysis["paper_leadership"].items():
        first_cc = p["first_countries"]
        last_cc = p["last_countries"]
        leadership_cc = first_cc | last_cc
        if not leadership_cc:
            neither_led += 1
            continue
        # "Dual leadership" = first author from one of {US,ZA} and last from
        # the other. Requires both a first and a last (i.e. >=2 authors).
        if last_cc:  # multi-author paper
            dual = (
                ("US" in first_cc and "ZA" in last_cc)
                or ("ZA" in first_cc and "US" in last_cc)
            )
        else:
            dual = False
        if dual:
            us_sa_led += 1
        us_only_lead = leadership_cc <= {"US"}
        sa_only_lead = leadership_cc <= {"ZA"}
        if us_only_lead:
            us_led += 1
        elif sa_only_lead:
            sa_led += 1
        elif "US" in leadership_cc and "ZA" in leadership_cc and not dual:
            us_and_sa_led += 1

    print("\nLeadership breakdown (first OR last author's country of affiliation)")
    print(f"  US-only leadership (first & last both US only):        {us_led:>3} / {n_items}  ({_fmt_pct(us_led, n_items)})")
    print(f"  SA-only leadership (first & last both ZA only):        {sa_led:>3} / {n_items}  ({_fmt_pct(sa_led, n_items)})")
    print(f"  Dual US\u2013SA leadership (first & last from opposite):   {us_sa_led:>3} / {n_items}  ({_fmt_pct(us_sa_led, n_items)})")
    print(f"  US+SA leadership (both in first/last but not opposite):{us_and_sa_led:>3} / {n_items}  ({_fmt_pct(us_and_sa_led, n_items)})")
    print(f"  Missing leadership country data:                        {neither_led:>3} / {n_items}  ({_fmt_pct(neither_led, n_items)})")

    # Bridge authors (with dual affiliations on at least one paper).
    print("\nBridge authors (dual affiliation on at least one paper)")
    print("  Note: OpenAlex occasionally assigns two IDs to the same real person,")
    print("  which shows up as near-duplicate rows here. Grouping is by OpenAlex ID.")
    bridge = analysis["bridge_activity"]
    if not bridge:
        print("  (none)")
    else:
        rows = []
        for author_id, info in bridge.items():
            name = info["names"].most_common(1)[0][0] if info["names"] else author_id
            rows.append((name, info))
        rows.sort(key=lambda kv: (-len(kv[1]["papers"]), kv[0]))
        print(f"  {'Name':<32}  {'Countries':<12}  {'First':>5}  {'Last':>4}  {'Mid':>3}  {'Papers':>6}")
        print(f"  {'-'*32}  {'-'*12}  {'-'*5}  {'-'*4}  {'-'*3}  {'-'*6}")
        for name, info in rows:
            countries = "+".join(sorted(info["countries"]))
            r = info["roles"]
            print(
                f"  {name[:32]:<32}  {countries:<12}  {r['first']:>5}  {r['last']:>4}  {r['middle']:>3}  {len(info['papers']):>6}"
            )


def main() -> None:
    analysis = analyze()
    print_report(analysis)


if __name__ == "__main__":
    main()

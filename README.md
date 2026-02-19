# BioSCape publications

This repository builds a static publications table from the BioSCape Zotero group collection and publishes it as HTML for embedding on bioscape.io.

## What the script does

- Reads top-level items from the target Zotero collection: <https://www.zotero.org/groups/2810748/bioscape/collections/U4SW8TCS>
- Paginates through the Zotero API (`limit`/`start`) so all records in the collection are included (not just the first 100)
- Maps Zotero fields into the table columns:
	- `Title`
	- `Item Type`
	- `Journal/Conference/Source`
	- `Creators`
	- `Year`
- Injects the generated table HTML into `template.html` at `<!-- TABLE_CONTENT -->`
- Writes the final page to `index.html`

## Requirements

- Python dependencies in `requirements.txt`:
	- `pyzotero~=1.5.16`
	- `dateparser~=1.2.0`
- Optional environment variable:
	- `ZOTERO_API_KEY` (not required for this public library)

## Automation

GitHub Actions workflow `.github/workflows/update-page.yml` rebuilds and publishes the page when:

- A push is made to `main`
- Run manually via `workflow_dispatch`
- On a daily schedule at `00:00 UTC` (`cron: 0 0 * * *`)

# BioSCape R Pipeline - Quick Start Guide

## What Is This?

The `biospace_network_pipeline.R` script consolidates 4 separate Python scripts into a single unified R workflow:

| Python Files | Purpose | R Equivalent |
|--------------|---------|--------------|
| `topic_modeling.py` | Extract from Zotero + semantic classification | `extract_zotero_data()` + `classify_documents_semantic()` |
| `author_deduplication.py` | Fuzzy-match and deduplicate authors | `group_authors_fuzzy()` + `create_author_mapping()` |
| `generate_kumu_semantic.py` | Create Kumu network data | `create_papers_authors_df()` |
| `verify_semantic_network.py` | Validate output | CSV files are self-validating |

**Result:** Single script that does everything, outputs Kumu CSVs directly.

## Quick Start (5 minutes)

### 1. Install R Packages (first time only)

Copy-paste into R console:

```r
packages <- c("httr", "jsonlite", "dplyr", "tidyr", "stringr", 
              "stringdist", "reticulate", "readr", "tibble")
install.packages(packages)
```

### 2. Install Python Packages

```bash
pip install sentence-transformers scikit-learn numpy
```

### 3. Set Zotero API Key

```bash
# Terminal/Command line
export ZOTERO_API_KEY="your-api-key-from-zotero.org"

# Or in R, before running:
Sys.setenv(ZOTERO_API_KEY = "your-api-key")
```

### 4. Run the Pipeline

```bash
Rscript biospace_network_pipeline.R
```

### 5. Find Your Output

```
network_analysis/kumu_import/
├── nodes.csv          ← Import this to Kumu
└── connections.csv    ← Import this to Kumu
```

### 6. Import to Kumu

1. Go to https://kumu.io
2. Create a new map
3. Settings → Import → CSV
4. Upload `nodes.csv` and `connections.csv`
5. Done! Your network is ready.

---

## Data Flow Comparison

### Python Pipeline (4 separate scripts)

```
1. topic_modeling.py
   ├─ Extract from Zotero API
   ├─ Classify documents (semantic similarity)
   └─ Output: extracted_data.csv

2. author_deduplication.py
   ├─ Load extracted_data.csv
   ├─ Fuzzy-match author names
   └─ Output: author_lookup.csv

3. generate_kumu_semantic.py
   ├─ Load extracted_data.csv + author_lookup.csv
   ├─ Build network data structures
   └─ Output: biospace_semantic_network.json

4. verify_semantic_network.py
   ├─ Load biospace_semantic_network.json
   └─ Validate completeness
```

**Dependencies:**
- Requires running scripts 1→2→3→4 in sequence
- Each script reads files output by previous scripts
- Python, pandas, sentence_transformers, scikit-learn required

### R Pipeline (single script)

```
biospace_network_pipeline.R
├─ extract_zotero_data()
│  └─ Output: df (in-memory)
│
├─ classify_documents_semantic()
│  └─ Output: df with classifications (in-memory)
│
├─ create_author_mapping()
│  └─ Output: author_mapping (in-memory)
│
├─ create_papers_authors_df()
│  └─ Output: papers_df, authors_df (in-memory)
│
└─ generate_kumu_csv()
   ├─ Output: nodes.csv
   ├─ Output: connections.csv
   ├─ Output: papers.csv
   ├─ Output: authors.csv
   └─ Output: extracted_data.csv
```

**Advantages:**
- Single execution: one command runs entire pipeline
- No intermediate file dependencies
- Faster (no disk I/O between steps)
- Easier to debug (all in one place)
- In-memory data handling
- Direct CSV output for Kumu (no JSON conversion needed)

---

## What Each Function Does

### `extract_zotero_data()`
- Connects to Zotero API
- Fetches publications from TARGET_COLLECTION
- Extracts: title, authors (semicolon-separated), abstract, year, item_type, url
- Returns: data frame with ~73 publications

### `classify_documents_semantic()`
- Uses Python's `sentence_transformers` (all-MiniLM-L6-v2 model)
- Embeds publication titles + abstracts
- Compares similarity to dimension category descriptions
- Assigns and scores: Ecosystem, Taxa, Method
- Alternative: keyword-based classification (if Python unavailable)
- Returns: data frame with classifications + similarity scores

### `group_authors_fuzzy()`
- Takes 358 raw author name strings
- Uses 3-strategy fuzzy matching:
  1. Jaro-Winkler string similarity (threshold: 0.85)
  2. Last name + initials matching
  3. Name variation detection (James/Jim/J., etc.)
- Groups similar names together
- Returns: list of author groups

### `create_author_mapping()`
- Selects canonical name for each author group
- Creates mapping: raw_name → canonical_name
- Returns: list with mapping and canonical author summary

### `create_papers_authors_df()`
- Builds PAPERS data frame
  - One row per publication
  - Includes all classifications and similarity scores
  - Color-coded by ecosystem (size 50)
- Builds AUTHORS data frame
  - One row per unique author
  - Scaled size by publication count (5-20px)
  - Deduplicated names

### `generate_kumu_csv()`
- Creates NODES CSV:
  - Combines papers + authors
  - Adds metadata, colors, sizes, tags
- Creates CONNECTIONS CSV:
  - Paper → Author (directed "Authored By")
  - Author ↔ Author (mutual "Collaborated With")
  - Includes strength (collaboration frequency)
- Writes 4 CSV files to output directories

---

## Example Output

### Input (from Zotero)

```
Author 1: "John Smith; Jane Doe; J. Smith"
Author 2: "J. Smith; Jane Doe"
Publication: "Coastal Biodiversity Study"
Abstract: "We studied marine ecosystems..."
```

### Processing

```
Raw authors detected: ["John Smith", "Jane Doe", "J. Smith", "J. Smith", "Jane Doe"]
                      → 358 total raw author strings from all papers

Fuzzy matching:
  "John Smith" (0.95) ← --
  "J. Smith"   (0.88) ← --  matched → Canonical: "John Smith"
  
  "Jane Doe"   (1.00) ← --
  "Jane Doe"   (1.00) ← --  matched → Canonical: "Jane Doe"

Result: 269 unique canonical authors
```

### Output (nodes.csv)

```csv
Name,Type,Color,Size,Research Ecosystem,...
"Coastal Biodiversity Study",Publication,#1f77b4,50,Marine,...
"John Smith",Author,#999999,8,...
"Jane Doe",Author,#999999,9,...
```

### Output (connections.csv)

```csv
From,To,Type,Relationship,Strength
"Coastal Biodiversity Study","John Smith","Authored By","Publication written by Author",1
"Coastal Biodiversity Study","Jane Doe","Authored By","Publication written by Author",1
"John Smith","Jane Doe","Collaborated With","Authors collaborated",1
```

---

## Customization Examples

### Run with specific Zotero collection

```r
# Edit at top of script:
TARGET_COLLECTION <- "YOUR_COLLECTION_ID"

# Then run:
Rscript biospace_network_pipeline.R
```

### Use looser author fuzzy matching

```r
# In R session:
source("biospace_network_pipeline.R")

# Extract and classify
df_classified <- extract_zotero_data() %>% classify_documents_semantic()

# Use looser threshold (0.80 instead of 0.85)
authors <- c(...)  # your author list
result <- group_authors_fuzzy(authors, similarity_threshold = 0.80)
```

### Skip Zotero, load from existing CSV

```r
# Comment out Zotero fetch, instead:
df <- readr::read_csv("dimension_analysis/extracted_data.csv")
df_classified <- classify_documents_semantic(df)
# ... continue with rest of pipeline
```

### Add custom dimension

```r
# In classify_documents_semantic(), add to dimensions list:
"conservation_status" = list(
  "Endangered" = "endangered threatened vulnerable at-risk extinction",
  "Stable" = "stable population robust viable healthy"
)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Error: Package 'httr' not found` | Run: `install.packages("httr")` |
| `Error: ZOTERO_API_KEY not found` | Set env var: `export ZOTERO_API_KEY="..."` |
| `ImportError: No module named 'sentence_transformers'` | Run: `pip install sentence-transformers` |
| Script runs very slowly | Python embeddings are slow first time (downloads model). Subsequent runs are faster. |
| "Low confidence (Mixed)" warnings | Normal - papers fitting multiple categories well. |
| Author count doesn't match Python output | Different fuzzy matching algorithms (Jaro-Winkler vs SequenceMatcher). Usually within 1-2 authors. |

---

## Output Specifications

### nodes.csv Format

| Column | Type | Source | Example |
|--------|------|--------|---------|
| Name | String | Paper title or Author name | "Gulf Stream Dynamics in the North Atlantic" |
| Type | String | "Publication" or "Author" | "Publication" |
| Color | Hex color | Ecosystem color map | "#1f77b4" |
| Size | Integer | 50 (papers), 5-20 (authors) | "50" |
| Year | Integer | From publication data | "2023" |
| Research Ecosystem | String | Marine/Freshwater/Terrestrial/Mixed | "Marine" |
| Primary Organism Group | String | Bacteria/Archaea/Protozoa/Chromista/Plantae/Fungi/Animalia | "Plantae" |
| Research Method | String | Measurement/Inferential | "Measurement" |
| Author Count | Integer | Number of authors | "5" |
| Publications Authored | Integer | (Authors only) publication count | "8" |
| Tags | String | Semicolon-separated classifications | "Publication;Marine;Plantae;Measurement" |

### connections.csv Format

| Column | Type | Example |
|--------|------|---------|
| From | String | Publication title or Author name |
| To | String | Author name or Author name |
| Type | String | "Authored By" or "Collaborated With" |
| Relationship | String | "Publication written by Author" or "Authors collaborated" |
| Strength | Integer | 1 (authorship), 1-20+ (collaborations) |

---

## Verification

After running, check these files exist:

```bash
ls -lh network_analysis/kumu_import/
# Should show:
# - nodes.csv (>100KB)
# - connections.csv (>200KB)
# - papers.csv
# - authors.csv

ls dimension_analysis/
# Should show:
# - extracted_data.csv
```

Quick validation in R:

```r
nodes <- read.csv("network_analysis/kumu_import/nodes.csv")
conns <- read.csv("network_analysis/kumu_import/connections.csv")

nrow(nodes)  # Should be ~341 (73 papers + 268 authors)
nrow(conns)  # Should be ~3,241
```

---

## Next Steps

1. ✅ Run pipeline: `Rscript biospace_network_pipeline.R`
2. ✅ Export files created in `network_analysis/kumu_import/`
3. → Go to https://kumu.io
4. → Create new map
5. → Import nodes.csv and connections.csv
6. → Explore network, apply decorations, filter by dimension
7. → Share with collaborators

---

## More Information

- Full documentation: See `BIOSPACE_R_PIPELINE_README.md`
- Kumu settings: See `KUMU_RECOMMENDED_SETTINGS.md`
- Kumu setup guide: See `KUMU_IMPORT_GUIDE.md`

---

**Version:** 1.0  
**Language:** R 4.0+  
**Last Updated:** February 16, 2026  
**Status:** Production Ready ✓  

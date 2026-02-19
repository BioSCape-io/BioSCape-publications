# BioSCape Publication Network Pipeline - R Implementation

## Overview

The `biospace_network_pipeline.R` script is a unified R implementation that consolidates all the functionality from the Python pipeline:

1. **Zotero Integration** - Fetches publication data from Zotero library
2. **Semantic Classification** - Assigns publications to research dimensions using sentence embeddings
3. **Author Deduplication** - Uses fuzzy matching to consolidate author name variations
4. **Network Data Preparation** - Creates structured data frames for network analysis
5. **Kumu Export** - Generates CSV files in Kumu format for visualization

## Installation

### 1. Install Required R Packages

```r
required_packages <- c(
  "httr",             # Zotero API communication
  "jsonlite",         # JSON parsing
  "dplyr",            # Data manipulation
  "tidyr",            # Data tidying
  "stringr",          # String processing
  "stringdist",       # Fuzzy string matching (Jaro-Winkler)
  "reticulate",       # Python integration
  "readr",            # CSV reading/writing
  "tibble"            # Modern data frames
)

# Install packages
install.packages(required_packages)
```

### 2. Python Setup (for Semantic Embeddings)

The script uses Python's `sentence_transformers` for semantic similarity:

```bash
# Install Python packages
pip install sentence-transformers scikit-learn numpy

# Or use conda
conda install -c conda-forge sentence-transformers scikit-learn
```

### 3. Zotero Configuration

Set your Zotero API key as an environment variable:

```bash
# In ~/.bashrc or ~/.zshrc
export ZOTERO_API_KEY="your-api-key-here"

# Or set in R session
Sys.setenv(ZOTERO_API_KEY = "your-api-key-here")
```

Get your API key from: https://www.zotero.org/settings/keys

Make sure these settings are configured in the script:
- `LIBRARY_ID`: Your Zotero library ID (default: "2810748")
- `LIBRARY_TYPE`: "user" or "group" (default: "group")
- `TARGET_COLLECTION`: Collection ID to read from (default: "U4SW8TCS")

## Usage

### Command Line

```bash
# Make script executable
chmod +x biospace_network_pipeline.R

# Run the pipeline
Rscript biospace_network_pipeline.R
```

### In R Session

```r
# Source the script
source("biospace_network_pipeline.R")

# Run main pipeline
result <- main()

# Access results
papers <- result$papers
authors <- result$authors
```

## Output Files

### Kumu Import Files (in `network_analysis/kumu_import/`)

1. **nodes.csv**
   - Contains all nodes (publications and authors)
   - Columns: Name, Type, Color, Size, [metadata]
   - Ready for direct import to Kumu
   - Publications: size 50, color-coded by ecosystem
   - Authors: size 5-20, scaled by publication count

2. **connections.csv**
   - Contains all relationships between nodes
   - Columns: From, To, Type, Relationship, Strength
   - Two connection types:
     - "Authored By": Publications → Authors (directed)
     - "Collaborated With": Author ↔ Author (undirected)
   - Strength value shows collaboration frequency

### Reference Files

3. **papers.csv** (in `network_analysis/kumu_import/`)
   - Full publication data with semantic dimensions
   - Columns: paper_id, Label, Type, Color, Size, Year, Ecosystem, Taxa, Method, Author_Count, + all semantic similarity scores
   - One row per publication

4. **authors.csv** (in `network_analysis/kumu_import/`)
   - Full author data with publication counts
   - Columns: author_id, Label, Type, Color, Size, Publications, num_variations, variations
   - One row per unique author

5. **extracted_data.csv** (in `dimension_analysis/`)
   - Same as papers.csv
   - Backup location for classified publication data

## Data Processing Steps

### Step 1: Data Extraction

```
Zotero API → Extract title, authors, abstract, year, URL, item_type
         ↓
        73 publications from BioSCape collection
```

**Function:** `extract_zotero_data()`

### Step 2: Semantic Classification

```
Publication abstracts + titles
         ↓
Sentence embeddings (all-MiniLM-L6-v2)
         ↓
Cosine similarity against dimension category embeddings
         ↓
Assign: Ecosystem (Marine/Freshwater/Terrestrial/Mixed)
        Taxa (7 kingdoms)
        Method (Measurement/Inferential)
        Confidence scores for each dimension
```

**Function:** `classify_documents_semantic()`

**Dimensions:**

1. **Ecosystem** (3 categories + Mixed):
   - Marine: Ocean, coastal, saltwater
   - Freshwater: Rivers, lakes, wetlands, ponds
   - Terrestrial: Forests, grasslands, woodlands, soil

2. **Taxa** (7 categories):
   - Bacteria: Prokaryotic organisms
   - Archaea: Archaeal organisms
   - Protozoa: Single-celled eukaryotes
   - Chromista: Algae, diatoms, kelp
   - Plantae: Plants, vegetation, flora
   - Fungi: Fungi, mushrooms, yeasts
   - Animalia: Animals, fauna, wildlife

3. **Method** (2 categories):
   - Measurement: Physical observation, instruments, sensors
   - Inferential: Statistical modeling, machine learning, prediction

### Step 3: Author Deduplication

```
358 raw author strings (from semicolon-separated list)
         ↓
Normalize names (lowercase, trim, squish spaces)
         ↓
Fuzzy matching strategies (in order):
  1. Jaro-Winkler string similarity (threshold: 0.85)
  2. Last name + initials matching
  3. Name variation detection (Jim ↔ James, Bob ↔ Robert, etc.)
         ↓
Group similar authors into clusters
         ↓
Select canonical name (prefer longer, less abbreviated)
         ↓
269 unique canonical author names
```

**Function:** `group_authors_fuzzy()`, `create_author_mapping()`

**Matching Algorithm:**

- **Jaro-Winkler Distance:** Measures string similarity (0-1)
  - "John Smith" vs "Jon Smith" → 0.93 (high match)
  - "John Smith" vs "John S." → 0.85 (threshold match)

- **Name Part Matching:** 
  - Last names must match exactly
  - First name initials must match (or variations like Jim/James)

- **Canonical Selection:**
  - Prefer longer names (more complete information)
  - Deprioritize highly abbreviated names
  - Example: "John Q. Smith" preferred over "J. Q. S."

### Step 4: Network Data Frame Creation

```
Classified publications + Author mapping
         ↓
PAPERS DATA FRAME:
  - paper_id, Label (title), Type=Publication
  - Color (ecosystem), Size=50
  - Year, Ecosystem, Taxa, Method
  - All semantic similarity scores
  - author_count
  
AUTHORS DATA FRAME:
  - author_id, Label (name), Type=Author
  - Color=#999999, Size (5-20, scaled by publications)
  - Publications (count)
  - num_variations, variations (for reference)
```

**Function:** `create_papers_authors_df()`

### Step 5: Kumu CSV Export

```
Papers DF + Authors DF
         ↓
Create NODES:
  - Combine papers and authors
  - Add taxonomic metadata
  - Add classification tags
         ↓
Create CONNECTIONS:
  - Author ← Published ← Paper (directed)
  - Author1 ← Collaborated ← Author2 (mutual)
  - Add collaboration strength (frequency)
         ↓
Write nodes.csv and connections.csv
```

**Function:** `generate_kumu_csv()`

## Kumu CSV Format

### nodes.csv

```csv
Name,Type,Color,Size,Year,Research Ecosystem,Primary Organism Group,Research Method,Author Count,Tags,Publications Authored
"BioSCape Coastal Carbon",Publication,#ff7f0e,50,2023,Mixed,Mixed,Measurement,2,"Publication;Mixed;Mixed;Measurement",
"Guild, Liane",Author,#999999,12,,,,,"Author",1
```

### connections.csv

```csv
From,To,Type,Relationship,Strength
"BioSCape Coastal Carbon","Guild, Liane","Authored By","Publication written by Author",1
"Guild, Liane","Tzortziou, Maria","Collaborated With","Authors collaborated",1
```

## Important Notes

### Python Integration

The script uses `reticulate` to call Python's `sentence_transformers` for semantic embeddings. This provides better classification than keyword-based approaches but requires:

1. Python 3.7+ installed
2. `sentence_transformers` package
3. `scikit-learn` package

**Fallback Mode:** If Python packages are not available, the script automatically switches to keyword-based classification (less accurate but functional).

### Fuzzy Matching

The Jaro-Winkler algorithm is used instead of simple string distance because it:
- Weights prefix differences more heavily (similar names often differ at the end)
- Handles abbreviations better
- Works well with full names vs. partial names

Threshold of 0.85 is conservative - catches clear matches while avoiding false positives.

### Dimension Confidence

Each classification includes a confidence score (0-1):
- Confidence = Top similarity - Second-highest similarity
- High confidence: 0.3+ (clear classification)
- Low confidence: 0.05-0.2 (document fits multiple categories equally)
- **Mixed:** Low-confidence categories are relabeled as "Mixed"

This prevents forcing ambiguous papers into a single category.

## Customization

### Adjust Similarity Threshold

In `group_authors_fuzzy()`, change threshold:

```r
group_authors_fuzzy(authors, similarity_threshold = 0.90)  # Stricter
group_authors_fuzzy(authors, similarity_threshold = 0.80)  # Looser
```

### Add Custom Dimensions

In `classify_documents_semantic()`, extend the `dimensions` list:

```r
dimensions <- list(
  # ... existing dimensions ...
  conservation_status = list(
    "Endangered" = "endangered threatened vulnerable extinction risk",
    "Stable" = "stable population viable healthy robust"
  )
)
```

### Change Output Directory

```r
KUMU_OUTPUT_DIR <- "path/to/output"
OUTPUT_DIR <- "path/to/dimension/output"
```

### Load from Existing CSV

If Zotero connection isn't available:

```r
df <- readr::read_csv("dimension_analysis/extracted_data.csv")
```

## Troubleshooting

### Python packages not found

**Error:** `ImportError: No module named 'sentence_transformers'`

**Solution:**
```bash
# Install via pip
pip install sentence-transformers scikit-learn

# Or check Python path in R
reticulate::py_config()
```

### Zotero API connection fails

**Error:** `Error in httr::GET()`

**Solutions:**
1. Check `ZOTERO_API_KEY` is set: `Sys.getenv("ZOTERO_API_KEY")`
2. Verify Library ID and Collection ID
3. Try loading from existing CSV instead of fetching from Zotero

### Fuzzy matching too slow

**Issue:** Script takes long time on author deduplication

**Solution:** The algorithm is O(n²) for n authors. For 350+ authors:
- To speed up: Use lower similarity threshold (e.g., 0.90 instead of 0.85)
- Use existing results if available
- Consider pre-filtering obviously different authors

### Memory issues with large datasets

**Issue:** R running out of memory during embeddings

**Solution:**
1. Process in batches (modify `classify_documents_semantic()`)
2. Use smaller embedding model: `'all-MiniLM-L6-v2'` (already used, lighter than `'all-mpnet-base-v2'`)

## Performance Characteristics

| Step | Time | Bottleneck |
|------|------|-----------|
| Zotero fetch | ~5-10s | Network + API |
| Semantic embeddings | ~30-60s | Python model loading + inference (batch size 32) |
| Author deduplication | ~10-20s | O(n²) fuzzy matching on 350 authors |
| Data frame creation | ~5s | Data manipulation |
| CSV export | ~2s | File I/O |
| **Total** | **~60-100s** | Semantic embeddings |

## Example Workflow

```r
# 1. Set up Zotero key
Sys.setenv(ZOTERO_API_KEY = "your-key")

# 2. Run pipeline
source("biospace_network_pipeline.R")
result <- main()

# 3. Review results
papers <- result$papers
cat(sprintf("Total papers: %d\n", nrow(papers)))
cat(sprintf("Total authors: %d\n", nrow(authors)))

# 4. Check ecosystem distribution
table(papers$Ecosystem)

# 5. Open Kumu and import:
#    - network_analysis/kumu_import/nodes.csv
#    - network_analysis/kumu_import/connections.csv
```

## Output Files Location

After running the pipeline:

```
dimension_analysis/
├── extracted_data.csv          # All publications with classifications

network_analysis/kumu_import/
├── nodes.csv                   # 341 nodes (73 papers + 268 authors)
├── connections.csv             # 3,241 connections (574 authored + 2,667 collaborated)
├── papers.csv                  # Reference: full paper data
└── authors.csv                 # Reference: full author data
```

## Importing to Kumu

1. Go to https://kumu.io
2. Create or open a map
3. Click **Settings** → **Import**
4. Select **CSV** format
5. Upload both files:
   - First: `nodes.csv`
   - Second: `connections.csv`
6. Kumu will automatically create the network with proper colors, sizes, and metadata

## Reproducing Python Outputs

This R script produces equivalent outputs to the Python pipeline:

| Python File | R Equivalent |
|-------------|--------------|
| `extract_zotero_data()` | `extract_zotero_data()` |
| `classify_documents_by_semantic_similarity()` | `classify_documents_semantic()` |
| `author_deduplication.py` | `group_authors_fuzzy()` + `create_author_mapping()` |
| `generate_kumu_import.py` | `generate_kumu_csv()` |
| `verify_kumu_json.py` | CSV structure is self-verifying |

**Differences:**
- Uses Jaro-Winkler distance (R) instead of SequenceMatcher ratio (Python)
- Direct CSV export instead of JSON (simpler for Kumu)
- More integrated (single script vs. 4 separate Python scripts)

## References

- **Zotero API**: https://www.zotero.org/support/dev/web_api/v3/start
- **Sentence Transformers**: https://www.sbert.net/
- **Kumu.io**: https://kumu.io/
- **stringdist R package**: https://github.com/markvanderloo/stringdist
- **Jaro-Winkler Distance**: https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance

---

**Version:** 1.0  
**Last Updated:** February 16, 2026  
**Status:** Production Ready  

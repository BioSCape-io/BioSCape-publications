#!/usr/bin/env Rscript
"""
BioSCape Publication Network Pipeline
Integrated R script that:
1. Retrieves publication data from Zotero
2. Classifies publications using semantic similarity dimensions
3. Deduplicates authors with fuzzy matching
4. Generates Kumu-compatible CSV export files
"""

# ============================================================================
# LIBRARIES
# ============================================================================

# Suppress warnings for cleaner output
suppressPackageStartupMessages({
  library(httr)           # HTTP requests to Zotero API
  library(jsonlite)       # JSON parsing
  library(dplyr)          # Data manipulation
  library(tidyr)          # Data tidying
  library(stringr)        # String manipulation
  library(stringdist)     # Fuzzy string matching
  library(reticulate)     # Python integration
  library(readr)          # CSV reading/writing
  library(tibble)         # Modern data frames
})

# ============================================================================
# CONFIGURATION
# ============================================================================

ZOTERO_API_KEY <- Sys.getenv("ZOTERO_API_KEY", "")
LIBRARY_ID <- "2810748"
LIBRARY_TYPE <- "group"
TARGET_COLLECTION <- "U4SW8TCS"
OUTPUT_DIR <- "dimension_analysis"
KUMU_OUTPUT_DIR <- "network_analysis/kumu_import"

# Create output directories
dir.create(OUTPUT_DIR, showWarnings = FALSE)
dir.create(KUMU_OUTPUT_DIR, showWarnings = FALSE)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

#' Reformat date string to year
#' @param date_str Character string containing date
#' @return Character string with year (YYYY)
reformat_date <- function(date_str) {
  if (is.na(date_str) || date_str == "") return("")
  
  # Try to extract 4-digit year
  year_match <- stringr::str_extract(date_str, "\\d{4}")
  if (!is.na(year_match)) return(year_match)
  
  return("")
}

#' Normalize author name for comparison
#' @param author Character string with author name
#' @return Normalized author name (lowercase, trimmed)
normalize_author <- function(author) {
  author %>%
    str_trim() %>%
    str_to_lower() %>%
    str_squish()
}

#' Extract last name and initials from author string
#' @param author Character string with author name
#' @return List with initials and last_name
extract_name_parts <- function(author) {
  author <- normalize_author(author)
  parts <- str_split(author, "\\s+")[[1]]
  
  if (length(parts) == 0) {
    return(list(initials = "", last_name = ""))
  }
  
  last_name <- parts[length(parts)]
  initials <- paste0(substr(parts[-length(parts)], 1, 1), collapse = "")
  
  list(initials = initials, last_name = last_name)
}

#' Common name variations for fuzzy matching
#' @return List of name variation groups
get_name_variations <- function() {
  list(
    c("james", "jim", "jimmy", "j", "j."),
    c("robert", "rob", "bob", "r", "r."),
    c("william", "bill", "will", "w", "w."),
    c("richard", "dick", "rick", "r", "r."),
    c("david", "dave", "d", "d."),
    c("joseph", "joe", "j", "j."),
    c("thomas", "tom", "tommy", "t", "t."),
    c("charles", "charlie", "chuck", "c", "c."),
    c("christopher", "chris", "c", "c."),
    c("daniel", "dan", "d", "d."),
    c("matthew", "matt", "m", "m."),
    c("anthony", "tony", "a", "a."),
    c("margaret", "peggy", "m", "m."),
    c("elizabeth", "liz", "beth", "e", "e."),
    c("barbara", "barb", "b", "b."),
    c("catherine", "cathy", "c", "c.")
  )
}

#' Calculate fuzzy similarity between two author names
#' @param s1 First author name
#' @param s2 Second author name
#' @param threshold Minimum similarity score (0-1)
#' @return Similarity score
fuzzy_match_score <- function(s1, s2, threshold = 0.8) {
  s1 <- normalize_author(s1)
  s2 <- normalize_author(s2)
  
  if (s1 == s2) return(1.0)
  
  # Use Jaro-Winkler distance
  score <- 1 - stringdist::stringdist(s1, s2, method = "jw")
  max(0, min(1, score))
}

# ============================================================================
# ZOTERO DATA EXTRACTION
# ============================================================================

#' Extract publication data from Zotero
#' @return Data frame with publications
extract_zotero_data <- function() {
  cat("Fetching data from Zotero API...\n")
  
  if (ZOTERO_API_KEY == "") {
    warning("ZOTERO_API_KEY environment variable not set. Skipping Zotero fetch.")
    return(NULL)
  }
  
  # Build API endpoint
  # Format: /groups/{groupID}/collections/{collectionKey}/items/top
  base_url <- sprintf(
    "https://api.zotero.org/%s/%s/collections/%s/items/top",
    LIBRARY_TYPE,
    LIBRARY_ID,
    TARGET_COLLECTION
  )
  
  cat("  URL: ", base_url, "\n", sep = "")
  cat("  API Key: ", substr(ZOTERO_API_KEY, 1, 10), "...\n", sep = "")
  
  # Fetch items with top-level items only
  response <- httr::GET(
    base_url,
    query = list(
      key = ZOTERO_API_KEY,
      format = "json",
      limit = 100,
      include = "abstractNote,url"
    ),
    httr::timeout(30)
  )
  
  status_code <- httr::status_code(response)
  cat("  Status: ", status_code, "\n", sep = "")
  
  if (status_code != 200) {
    error_msg <- httr::content(response, "text")
    warning(sprintf("Zotero API error %d\n%s\n
Check configuration:
  LIBRARY_ID: %s
  LIBRARY_TYPE: %s
  TARGET_COLLECTION: %s

Run: Rscript zotero_config_helper.R", 
            status_code, error_msg, LIBRARY_ID, LIBRARY_TYPE, TARGET_COLLECTION))
    return(NULL)
  }
  
  items <- jsonlite::fromJSON(httr::content(response, "text"))
  
  if (!is.list(items) || length(items) == 0) {
    warning("No items found in collection. Check TARGET_COLLECTION ID.")
    return(NULL)
  }
  
  records <- list()
  
  for (item in items) {
    data <- item$data
    
    # Extract title
    title <- data$title %||% ""
    if (title == "") next
    
    # Extract authors
    creators <- data$creators %||% list()
    authors <- character(0)
    
    for (creator in creators) {
      if (!is.null(creator$firstName) && !is.null(creator$lastName)) {
        authors <- c(authors, paste(creator$firstName, creator$lastName))
      } else if (!is.null(creator$name)) {
        authors <- c(authors, creator$name)
      }
    }
    
    authors_str <- paste(authors, collapse = "; ")
    
    # Extract abstract
    abstract <- data$abstractNote %||% ""
    if (abstract == "") next
    
    # Extract metadata
    item_type <- data$itemType %||% ""
    year <- reformat_date(data$date %||% "")
    url <- data$url %||% ""
    
    records[[length(records) + 1]] <- list(
      title = title,
      authors = authors_str,
      abstract = abstract,
      item_type = item_type,
      year = year,
      url = url
    )
  }
  
  cat(sprintf("Extracted %d publications from Zotero\n", length(records)))
  
  # Convert to data frame
  if (length(records) == 0) {
    return(tibble::tibble(
      title = character(),
      authors = character(),
      abstract = character(),
      item_type = character(),
      year = character(),
      url = character()
    ))
  }
  
  records %>%
    do.call(rbind, .) %>%
    as.data.frame() %>%
    tibble::as_tibble() %>%
    mutate(across(everything(), as.character))
}

# ============================================================================
# SEMANTIC CLASSIFICATION
# ============================================================================

#' Classify documents using semantic similarity with Python/transformers
#' @param df Data frame with 'title' and 'abstract' columns
#' @return Data frame with dimension classifications
classify_documents_semantic <- function(df) {
  cat("\nClassifying documents using semantic similarity...\n")
  
  # Check if Python and required packages are available
  python_check <- tryCatch({
    reticulate::py_run_string("
import sys
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    print('Python packages available')
except ImportError as e:
    print(f'Missing package: {e}')
    sys.exit(1)
")
    TRUE
  }, error = function(e) {
    warning("Python/sentence_transformers not available. Using keyword-based classification.")
    FALSE
  })
  
  if (!python_check) {
    # Fallback: keyword-based classification
    return(classify_documents_keywords(df))
  }
  
  # Define dimension categories with descriptions
  dimensions <- list(
    ecosystem = list(
      Marine = "Marine ocean coastal waters seawater phytoplankton kelp coral reef pelagic benthic intertidal offshore saltwater biodiversity ocean",
      Freshwater = "Freshwater rivers streams lakes ponds wetlands riparian floodplains inland water quality",
      Terrestrial = "Terrestrial forests grasslands savannas woodland upland canopy vegetation soil land-dwelling"
    ),
    taxa = list(
      Bacteria = "Bacteria prokaryotic bacterial diversity microbial bacterioplankton nitrogen-fixing decomposer",
      Archaea = "Archaea archaeal extremophile methane",
      Protozoa = "Protozoa protozoans amoebae ciliates flagellates heterotrophic protist",
      Chromista = "Chromista algae diatom kelp brown algae phytoplankton",
      Plantae = "Plantae plants vegetation flora botanical ecology photosynthesis trees shrubs herbs flowers crops",
      Fungi = "Fungi mushrooms yeasts molds mycorrhizal decomposer fungal",
      Animalia = "Animalia animals mammals birds reptiles amphibians fish invertebrates insects zoology fauna wildlife"
    ),
    method = list(
      Measurement = "Measurement physical observation deterministic instruments sensors remote sensing spectroscopy field measurement mechanical",
      Inferential = "Inferential statistical analysis probabilistic modeling inference hypothesis machine learning data mining predictive"
    )
  )
  
  # Use Python for embeddings
  reticulate::py_run_string("
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')
")
  
  # Embed documents
  cat("  Generating document embeddings...\n")
  document_texts <- paste0(df$title, ". ", df$abstract)
  
  doc_embeddings <- reticulate::py_run_string(
    sprintf("
documents = %s
doc_embeddings = model.encode(documents, batch_size=32, show_progress_bar=False)
", jsonlite::toJSON(document_texts))
  )
  
  # Classify each dimension
  for (dim_name in names(dimensions)) {
    cat(sprintf("  Classifying %s dimension...\n", dim_name))
    
    dim_categories <- dimensions[[dim_name]]
    category_names <- names(dim_categories)
    category_descs <- unname(dim_categories)
    
    # Embed categories
    cat_embeddings <- reticulate::py_run_string(
      sprintf("
categories = %s
cat_embeddings = model.encode(categories, batch_size=32, show_progress_bar=False)
", jsonlite::toJSON(category_descs))
    )
    
    # Calculate similarities
    similarities <- reticulate::py_run_string(
      "similarities = cosine_similarity(doc_embeddings, cat_embeddings)"
    )
    
    sim_matrix <- reticulate::py$similarities
    
    # Store similarity scores
    for (i in seq_along(category_names)) {
      col_name <- sprintf("%s_%s_similarity", dim_name, category_names[i])
      df[[col_name]] <- sim_matrix[, i]
    }
    
    # Assign primary category
    max_idx <- apply(sim_matrix, 1, which.max)
    df[[dim_name]] <- category_names[max_idx]
    
    # Calculate confidence (difference between top 2)
    sorted_sims <- t(apply(sim_matrix, 1, sort, decreasing = TRUE))
    df[[sprintf("%s_confidence", dim_name)]] <- sorted_sims[, 1] - sorted_sims[, 2]
    
    # Mark as 'Mixed' if low confidence
    low_conf <- df[[sprintf("%s_confidence", dim_name)]] < 0.05
    df[[dim_name]][low_conf] <- "Mixed"
    
    # Print distribution
    cat(sprintf("    Distribution:\n"))
    dist <- table(df[[dim_name]])
    for (cat in names(dist)) {
      cat(sprintf("      %s: %d documents\n", cat, dist[cat]))
    }
  }
  
  return(df)
}

#' Keyword-based classification (fallback)
#' @param df Data frame with documents
#' @return Classified data frame
classify_documents_keywords <- function(df) {
  cat("  Using keyword-based classification (fallback)...\n")
  
  keywords <- list(
    ecosystem = list(
      Marine = c("marine", "ocean", "coastal", "seawater", "coral", "kelp"),
      Freshwater = c("freshwater", "river", "stream", "lake", "pond", "wetland"),
      Terrestrial = c("terrestrial", "forest", "grassland", "woodland", "soil", "vegetation")
    ),
    taxa = list(
      Bacteria = c("bacteria", "bacterial", "microbial"),
      Archaea = c("archaea", "archaeal"),
      Plantae = c("plant", "vegetation", "flora", "tree", "grass"),
      Fungi = c("fungi", "fungal", "mushroom"),
      Animalia = c("animal", "fauna", "wildlife", "fish", "bird")
    ),
    method = list(
      Measurement = c("measurement", "instrument", "sensor", "observation"),
      Inferential = c("statistical", "model", "inference", "learning", "machine")
    )
  )
  
  combined_text <- paste0(tolower(df$title), " ", tolower(df$abstract))
  
  for (dim_name in names(keywords)) {
    scores <- matrix(0, nrow = nrow(df), ncol = length(keywords[[dim_name]]))
    
    for (j in seq_along(keywords[[dim_name]])) {
      kw_list <- keywords[[dim_name]][[j]]
      for (kw in kw_list) {
        scores[, j] <- scores[, j] + stringr::str_count(combined_text, kw)
      }
    }
    
    # Assign category
    max_idx <- apply(scores, 1, which.max)
    df[[dim_name]] <- names(keywords[[dim_name]])[max_idx]
    
    # Confidence
    df[[sprintf("%s_confidence", dim_name)]] <- apply(scores, 1, function(x) {
      sorted <- sort(x, decreasing = TRUE)
      if (length(sorted) >= 2) sorted[1] - sorted[2] else sorted[1]
    })
  }
  
  return(df)
}

# ============================================================================
# AUTHOR DEDUPLICATION
# ============================================================================

#' Group similar authors using fuzzy matching
#' @param authors Character vector of author names
#' @param similarity_threshold Minimum similarity (0-1)
#' @return List with author groups
group_authors_fuzzy <- function(authors, similarity_threshold = 0.85) {
  cat(sprintf("Grouping %d authors using fuzzy matching...\n", length(authors)))
  
  # Normalize all authors
  authors_norm <- sapply(authors, normalize_author, USE.NAMES = FALSE)
  
  # Initialize groups
  groups <- list()
  grouped <- rep(FALSE, length(authors))
  group_counter <- 0
  
  name_variations <- get_name_variations()
  
  for (i in seq_along(authors)) {
    if (grouped[i]) next
    
    group_counter <- group_counter + 1
    group_id <- sprintf("group_%d", group_counter)
    groups[[group_id]] <- authors[i]
    grouped[i] <- TRUE
    
    # Find similar authors
    for (j in (i + 1):length(authors)) {
      if (grouped[j]) next
      
      # Strategy 1: Direct fuzzy matching
      score <- fuzzy_match_score(authors[i], authors[j])
      if (score >= similarity_threshold) {
        groups[[group_id]] <- c(groups[[group_id]], authors[j])
        grouped[j] <- TRUE
        next
      }
      
      # Strategy 2: Last name + initials matching
      parts1 <- extract_name_parts(authors[i])
      parts2 <- extract_name_parts(authors[j])
      
      if (parts1$last_name != "" && parts1$last_name == parts2$last_name) {
        if (parts1$initials != "" && parts2$initials != "") {
          if (substr(parts1$initials, 1, 1) == substr(parts2$initials, 1, 1)) {
            groups[[group_id]] <- c(groups[[group_id]], authors[j])
            grouped[j] <- TRUE
            next
          }
        }
      }
    }
  }
  
  cat(sprintf("Found %d unique authors\n", length(groups)))
  return(groups)
}

#' Select canonical name from author group
#' @param author_group Character vector of author name variations
#' @return Best canonical name
select_canonical <- function(author_group) {
  # Prefer longer, more complete names
  sorted <- author_group[order(nchar(author_group), decreasing = TRUE)]
  
  # Filter out abbreviation-heavy names
  abbrev_score <- sapply(sorted, function(x) {
    parts <- str_split(x, "\\s+")[[1]]
    sum(nchar(parts) <= 2)
  })
  
  sorted[which.min(abbrev_score)][1]
}

#' Create author mapping and lookup table
#' @param authors Character vector of author names
#' @return List with mapping and canonical authors
create_author_mapping <- function(authors) {
  groups <- group_authors_fuzzy(authors, similarity_threshold = 0.85)
  
  mapping <- list()
  canonical_df <- tibble::tibble(
    canonical_name = character(),
    num_variations = integer(),
    variations = character()
  )
  
  for (group in groups) {
    canonical <- select_canonical(group)
    canonical <- paste(
      tools::toTitleCase(tolower(canonical)),
      sep = ""
    )
    
    for (variation in group) {
      mapping[[normalize_author(variation)]] <- canonical
    }
    
    canonical_df <- rbind(canonical_df, tibble::tibble(
      canonical_name = canonical,
      num_variations = length(group),
      variations = paste(sort(group), collapse = "|")
    ))
  }
  
  # Sort and remove duplicates
  canonical_df <- canonical_df %>%
    distinct(canonical_name, .keep_all = TRUE) %>%
    arrange(canonical_name)
  
  list(mapping = mapping, canonical_authors = canonical_df)
}

# ============================================================================
# DATA FRAME GENERATION
# ============================================================================

#' Parse authors from semicolon-separated string
#' @param authors_str Semicolon-separated author string
#' @param author_mapping Named list mapping authors to canonical names
#' @return Character vector of canonical author names
parse_authors <- function(authors_str, author_mapping) {
  if (is.na(authors_str) || authors_str == "") return(character(0))
  
  authors <- str_split(authors_str, ";")[[1]] %>%
    str_trim()
  
  canonical <- sapply(authors, function(a) {
    normalized <- normalize_author(a)
    author_mapping[[normalized]] %||% a
  }, USE.NAMES = FALSE)
  
  canonical[canonical != ""]
}

#' Create papers and authors data frames
#' @param df Classified publications data frame
#' @param author_mapping Author mapping
#' @param canonical_authors Canonical authors data frame
#' @return List with papers_df and authors_df
create_papers_authors_df <- function(df, author_mapping, canonical_authors) {
  cat("\nCreating papers and authors data frames...\n")
  
  # Papers data frame
  ecosystem_colors <- c(
    Marine = "#1f77b4",
    Freshwater = "#2ca02c",
    Terrestrial = "#d62728",
    Mixed = "#ff7f0e",
    Unknown = "#7f7f7f"
  )
  
  papers_df <- df %>%
    mutate(
      paper_id = row_number(),
      Type = "Publication",
      Label = title,
      Color = ecosystem_colors[ecosystem],
      Size = 50,
      Year = year,
      Ecosystem = ecosystem,
      Taxa = taxa,
      Method = method,
      Author_Count = NA_integer_
    ) %>%
    select(
      paper_id, Label, Type, Color, Size,
      Year, Ecosystem, Taxa, Method,
      everything()
    )
  
  # Parse authors for each paper
  papers_df$Author_Count <- sapply(papers_df$authors, function(auth_str) {
    parse_authors(auth_str, author_mapping) %>% length()
  })
  
  # Authors data frame with publication count
  author_pub_count <- integer()
  for (canonical in canonical_authors$canonical_name) {
    count <- sum(sapply(papers_df$authors, function(auth_str) {
      canonical %in% parse_authors(auth_str, author_mapping)
    }))
    author_pub_count[canonical] <- count
  }
  
  authors_df <- canonical_authors %>%
    rename(Label = canonical_name) %>%
    mutate(
      author_id = row_number(),
      Type = "Author",
      Color = "#999999",
      Size = pmin(20, pmax(5, 5 + num_variations * 1.5)),
      Publications = author_pub_count[Label]
    ) %>%
    select(author_id, Label, Type, Color, Size, Publications, everything())
  
  list(papers_df = papers_df, authors_df = authors_df)
}

# ============================================================================
# KUMU CSV EXPORT
# ============================================================================

#' Generate Kumu CSV files (nodes and connections)
#' @param papers_df Papers data frame
#' @param authors_df Authors data frame
#' @param output_dir Output directory
generate_kumu_csv <- function(papers_df, authors_df, output_dir = KUMU_OUTPUT_DIR) {
  cat("\nGenerating Kumu CSV files...\n")
  
  # Papers nodes CSV
  papers_nodes <- papers_df %>%
    select(Label, Type, Color, Size, Year, Ecosystem, Taxa, Method, Author_Count) %>%
    rename(
      Name = Label,
      "Year of Publication" = Year,
      "Research Ecosystem" = Ecosystem,
      "Primary Organism Group" = Taxa,
      "Research Method" = Method,
      "Author Count" = Author_Count
    ) %>%
    mutate(
      Tags = paste(Type, `Research Ecosystem`, `Primary Organism Group`, `Research Method`, sep = ";")
    )
  
  # Authors nodes CSV
  authors_nodes <- authors_df %>%
    select(Label, Type, Color, Size, Publications) %>%
    rename(
      Name = Label,
      "Publications Authored" = Publications
    ) %>%
    mutate(Tags = Type)
  
  # Combine nodes
  all_nodes <- rbind(
    papers_nodes %>% mutate(`Publications Authored` = NA),
    authors_nodes %>% mutate(
      Year = NA,
      `Research Ecosystem` = NA,
      `Primary Organism Group` = NA,
      `Research Method` = NA,
      `Author Count` = NA
    ) %>% select(Names(colnames(papers_nodes)))
  )
  
  # Write nodes CSV
  nodes_file <- file.path(output_dir, "nodes.csv")
  readr::write_csv(all_nodes, nodes_file)
  cat(sprintf("✓ Saved nodes.csv (%d nodes)\n", nrow(all_nodes)))
  
  # Generate connections
  cat("Generating connections...\n")
  
  connections <- list()
  conn_id <- 0
  
  # Publication to Author connections
  for (i in seq_len(nrow(papers_df))) {
    paper_label <- papers_df$Label[i]
    authors_str <- papers_df$authors[i]
    authors <- parse_authors(authors_str, author_mapping)
    
    for (author in authors) {
      conn_id <- conn_id + 1
      connections[[conn_id]] <- tibble::tibble(
        From = paper_label,
        To = author,
        Type = "Authored By",
        Relationship = "Publication written by Author",
        Strength = 1
      )
    }
  }
  
  # Co-authorship connections
  coauthor_pairs <- list()
  for (i in seq_len(nrow(papers_df))) {
    authors_str <- papers_df$authors[i]
    authors <- parse_authors(authors_str, author_mapping)
    
    if (length(authors) > 1) {
      for (j1 in 1:(length(authors) - 1)) {
        for (j2 in (j1 + 1):length(authors)) {
          pair_key <- paste0(
            sort(c(authors[j1], authors[j2])),
            collapse = " <-> "
          )
          coauthor_pairs[[pair_key]] <- (coauthor_pairs[[pair_key]] %||% 0) + 1
        }
      }
    }
  }
  
  # Add coauthor connections
  for (pair_key in names(coauthor_pairs)) {
    conn_id <- conn_id + 1
    authors_pair <- str_split(pair_key, " <-> ")[[1]]
    connections[[conn_id]] <- tibble::tibble(
      From = authors_pair[1],
      To = authors_pair[2],
      Type = "Collaborated With",
      Relationship = "Authors collaborated",
      Strength = coauthor_pairs[[pair_key]]
    )
  }
  
  # Combine connections
  connections_df <- do.call(rbind, connections)
  
  # Write connections CSV
  connections_file <- file.path(output_dir, "connections.csv")
  readr::write_csv(connections_df, connections_file)
  cat(sprintf("✓ Saved connections.csv (%d connections)\n", nrow(connections_df)))
  
  # Save paper-only data for reference
  papers_file <- file.path(output_dir, "papers.csv")
  readr::write_csv(papers_df, papers_file)
  cat(sprintf("✓ Saved papers.csv (%d papers)\n", nrow(papers_df)))
  
  # Save author-only data for reference
  authors_file <- file.path(output_dir, "authors.csv")
  readr::write_csv(authors_df, authors_file)
  cat(sprintf("✓ Saved authors.csv (%d authors)\n", nrow(authors_df)))
  
  # Save classified data
  classified_file <- file.path(OUTPUT_DIR, "extracted_data.csv")
  readr::write_csv(papers_df, classified_file)
  cat(sprintf("✓ Saved extracted_data.csv\n"))
}

# ============================================================================
# MAIN PIPELINE
# ============================================================================

main <- function() {
  cat("================================================================================\n")
  cat("BIOSPACE PUBLICATION NETWORK PIPELINE\n")
  cat("================================================================================\n\n")
  
  # Step 1: Extract from Zotero (or load existing)
  zotero_df <- extract_zotero_data()
  
  if (is.null(zotero_df) || nrow(zotero_df) == 0) {
    # Try to load from existing CSV
    existing_csv <- file.path(OUTPUT_DIR, "extracted_data.csv")
    if (file.exists(existing_csv)) {
      cat(sprintf("Loading from existing CSV: %s\n", existing_csv))
      df <- readr::read_csv(existing_csv, show_col_types = FALSE)
    } else {
      stop("No publication data available. Set ZOTERO_API_KEY or provide extracted_data.csv")
    }
  } else {
    df <- zotero_df
  }
  
  cat(sprintf("Working with %d publications\n", nrow(df)))
  
  # Step 2: Classify documents by semantic dimensions
  df_classified <- classify_documents_semantic(df)
  
  # Step 3: Extract and deduplicate authors
  all_authors <- character()
  for (auth_str in df_classified$authors) {
    authors_split <- str_split(auth_str, ";")[[1]] %>%
      str_trim()
    all_authors <- c(all_authors, authors_split)
  }
  all_authors <- unique(all_authors[all_authors != ""])
  
  cat(sprintf("Found %d unique author strings\n", length(all_authors)))
  
  author_result <- create_author_mapping(all_authors)
  author_mapping <- author_result$mapping
  canonical_authors <- author_result$canonical_authors
  
  # Step 4: Create papers and authors data frames
  df_result <- create_papers_authors_df(
    df_classified,
    author_mapping,
    canonical_authors
  )
  papers_df <- df_result$papers_df
  authors_df <- df_result$authors_df
  
  # Step 5: Generate Kumu CSV files
  generate_kumu_csv(papers_df, authors_df)
  
  # Summary
  cat("\n" + "=" * 80 + "\n")
  cat("PIPELINE COMPLETE\n")
  cat("=" * 80 + "\n")
  cat(sprintf("✓ Publications: %d\n", nrow(papers_df)))
  cat(sprintf("✓ Unique Authors: %d\n", nrow(authors_df)))
  cat(sprintf("✓ Dimensions: Ecosystem (Marine/Freshwater/Terrestrial)\n"))
  cat(sprintf("            : Taxa (7 kingdoms)\n"))
  cat(sprintf("            : Method (Measurement/Inferential)\n\n")
  cat(sprintf("Output Files:\n"))
  cat(sprintf("  - %s/nodes.csv (for Kumu import)\n", KUMU_OUTPUT_DIR))
  cat(sprintf("  - %s/connections.csv (for Kumu import)\n", KUMU_OUTPUT_DIR))
  cat(sprintf("  - %s/papers.csv (full paper data)\n", KUMU_OUTPUT_DIR))
  cat(sprintf("  - %s/authors.csv (author metadata)\n", KUMU_OUTPUT_DIR))
  cat(sprintf("  - %s/extracted_data.csv (classified data)\n\n", OUTPUT_DIR))
  cat("Ready for Kumu.io import!\n")
  
  invisible(list(papers = papers_df, authors = authors_df))
}

# Run pipeline
if (!interactive()) {
  main()
}

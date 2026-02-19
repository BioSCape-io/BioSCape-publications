#!/usr/bin/env Rscript
"""
BioSCape Zotero Configuration Helper
Helps identify correct Library ID and Collection ID for the API
"""

library(httr)
library(jsonlite)
library(dplyr)

# ============================================================================
# CONFIGURATION
# ============================================================================

ZOTERO_API_KEY <- Sys.getenv("ZOTERO_API_KEY", "")

if (ZOTERO_API_KEY == "") {
  stop("ZOTERO_API_KEY environment variable not set.\n",
       "Get your key from: https://www.zotero.org/settings/keys\n",
       "Then run: export ZOTERO_API_KEY='your-key-here'")
}

cat("=" * 80, "\n")
cat("ZOTERO API CONFIGURATION HELPER\n")
cat("=" * 80, "\n\n")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

make_zotero_request <- function(endpoint, method = "GET", query = NULL) {
  """Make a request to the Zotero API"""
  
  base <- "https://api.zotero.org"
  url <- paste0(base, endpoint)
  
  cat("Request: ", method, " ", url, "\n", sep = "")
  if (!is.null(query)) {
    cat("Query: ", paste(names(query), "=", query, collapse = ", "), "\n", sep = "")
  }
  
  response <- httr::GET(
    url,
    query = c(key = ZOTERO_API_KEY, query),
    timeout(10)
  )
  
  status <- httr::status_code(response)
  cat("Status: ", status, "\n", sep = "")
  
  if (status != 200) {
    cat("Error! Response:\n")
    cat(httr::content(response, "text"), "\n")
    return(NULL)
  }
  
  content <- httr::content(response, "text")
  jsonlite::fromJSON(content)
}

# ============================================================================
# STEP 1: LIST ALL GROUPS
# ============================================================================

cat("\n▶ Step 1: Finding your Zotero groups...\n")
cat("-" * 80, "\n")

groups <- make_zotero_request("/groups")

if (is.null(groups) || length(groups) == 0) {
  cat("No groups found. You may be using a personal library instead.\n")
  cat("For personal library, use LIBRARY_TYPE = 'user' and your user ID.\n\n")
} else {
  cat(sprintf("\nFound %d group(s):\n\n", length(groups)))
  
  for (i in seq_along(groups)) {
    group <- groups[[i]]$data
    cat(sprintf("  Group #%d:\n", i))
    cat(sprintf("    ID: %s\n", group$id))
    cat(sprintf("    Name: %s\n", group$name))
    cat(sprintf("    Description: %s\n", group$description %||% "(none)"))
    cat(sprintf("    Members: %d\n\n", group$numItems %||% 0))
  }
}

# ============================================================================
# STEP 2: GET USER INFO
# ============================================================================

cat("\n▶ Step 2: Checking your user account...\n")
cat("-" * 80, "\n")

user_info <- make_zotero_request("/users/me")

if (!is.null(user_info)) {
  library_id <- user_info$data$id
  cat(sprintf("\nYour User ID: %s\n", library_id))
  cat("For your personal library, use:\n")
  cat(sprintf("  LIBRARY_ID <- '%s'\n", library_id))
  cat("  LIBRARY_TYPE <- 'user'\n")
}

# ============================================================================
# STEP 3: LIST COLLECTIONS IN TARGET LIBRARY
# ============================================================================

cat("\n▶ Step 3: Listing collections...\n")
cat("-" * 80, "\n")

# Try both user and group
library_types <- c("user", "group")
library_ids <- c(user_info$data$id %||% "", "2810748")

for (lib_type in library_types) {
  for (lib_id in library_ids) {
    if (lib_id == "") next
    
    cat(sprintf("\nChecking %s library %s:\n", lib_type, lib_id))
    
    endpoint <- sprintf("/%s/%s/collections", lib_type, lib_id)
    collections <- make_zotero_request(endpoint)
    
    if (!is.null(collections) && length(collections) > 0) {
      cat(sprintf("✓ Found %d collection(s):\n\n", length(collections)))
      
      for (i in seq_along(collections)) {
        coll <- collections[[i]]$data
        coll$key <- collections[[i]]$key
        cat(sprintf("    Collection #%d:\n", i))
        cat(sprintf("      Key: %s\n", coll$key))
        cat(sprintf("      Name: %s\n", coll$name))
        cat(sprintf("      Parent: %s\n", coll$parentCollection %||% "(root)"))
        cat("\n")
      }
      
      # Try to get items from the first collection
      first_coll_key <- collections[[1]]$key
      cat(sprintf("\n  Attempting to fetch items from first collection (%s):\n", first_coll_key))
      
      items <- make_zotero_request(
        sprintf("/%s/%s/collections/%s/items/top", lib_type, lib_id, first_coll_key),
        query = list(limit = 5, format = "json")
      )
      
      if (!is.null(items) && length(items) > 0) {
        cat(sprintf("  ✓ Successfully fetched %d item(s)\n", length(items)))
        
        cat("\n  Sample items:\n")
        for (i in 1:min(3, length(items))) {
          item <- items[[i]]$data
          cat(sprintf("    - %s (type: %s)\n", 
                      item$title %||% "(no title)", 
                      item$itemType %||% "unknown"))
        }
        
        cat(sprintf("\n✅ CORRECT CONFIG for this collection:\n"))
        cat(sprintf("  LIBRARY_ID <- '%s'\n", lib_id))
        cat(sprintf("  LIBRARY_TYPE <- '%s'\n", lib_type))
        cat(sprintf("  TARGET_COLLECTION <- '%s'\n", first_coll_key))
      }
    }
  }
}

# ============================================================================
# STEP 4: SEARCH FOR BIOSPACE COLLECTION
# ============================================================================

cat("\n\n▶ Step 4: Searching for 'BioSCape' collection...\n")
cat("-" * 80, "\n")

# Check group 2810748 specifically
group_id <- "2810748"
cat(sprintf("Checking group library %s:\n", group_id))

endpoint <- sprintf("/groups/%s/collections", group_id)
response <- httr::GET(
  paste0("https://api.zotero.org", endpoint),
  query = list(key = ZOTERO_API_KEY),
  timeout(10)
)

if (httr::status_code(response) == 200) {
  collections <- jsonlite::fromJSON(httr::content(response, "text"))
  
  if (length(collections) > 0) {
    cat(sprintf("Found %d collections in group %s:\n\n", length(collections), group_id))
    
    for (i in seq_along(collections)) {
      coll <- collections[[i]]$data
      coll_key <- collections[[i]]$key
      cat(sprintf("  %s: %s\n", coll_key, coll$name))
    }
  } else {
    cat("No collections found in this group.\n")
  }
} else {
  cat(sprintf("Could not access group %s (HTTP %d)\n", 
              group_id, httr::status_code(response)))
}

# ============================================================================
# RECOMMENDED CONFIGURATION
# ============================================================================

cat("\n\n" * 80, "\n")
cat("CONFIGURATION RECOMMENDATION\n")
cat("=" * 80, "\n\n")

cat("Copy this into your R script:\n\n")
cat("# Zotero Configuration\n")
cat("ZOTERO_API_KEY <- 'your-api-key'  # Get from https://zotero.org/settings/keys\n")
cat("LIBRARY_ID <- 'your-library-id'  # From output above\n")
cat("LIBRARY_TYPE <- 'user'  # or 'group'\n")
cat("TARGET_COLLECTION <- 'your-collection-key'  # From output above\n\n")

cat("Then test the connection with:\n")
cat("source('zotero_config_helper.R')  # This script\n")

cat("\n" * 80, "\n")

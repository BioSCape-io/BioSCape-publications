#!/usr/bin/env python3
"""
Author Deduplication Script
Uses fuzzy matching to identify common authors across papers and creates
a canonical author lookup table.
"""

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from collections import defaultdict
import re

def load_author_data(csv_path):
    """Load and extract all unique authors from publication data."""
    df = pd.read_csv(csv_path)
    
    # Extract all authors
    all_authors = []
    for authors_str in df['authors'].dropna():
        authors = [a.strip().lower() for a in str(authors_str).split(';')]
        all_authors.extend(authors)
    
    # Get unique authors
    unique_authors = sorted(list(set(author for author in all_authors if author)))
    print(f"Found {len(unique_authors)} unique author strings")
    return unique_authors

def normalize_author(author):
    """Normalize author name for comparison."""
    # Remove extra spaces
    author = ' '.join(author.split())
    # Convert to lowercase
    author = author.lower()
    return author

def fuzzy_match(s1, s2, threshold=0.8):
    """Calculate similarity ratio between two strings."""
    s1 = normalize_author(s1)
    s2 = normalize_author(s2)
    
    # Exact match
    if s1 == s2:
        return 1.0
    
    # Use SequenceMatcher for similarity
    matcher = SequenceMatcher(None, s1, s2)
    return matcher.ratio()

def extract_initials_and_lastname(author):
    """Extract initials and last name from author string."""
    parts = author.strip().split()
    if len(parts) == 0:
        return None, None
    
    last_name = parts[-1].lower()
    initials = ''.join([p[0].lower() for p in parts[:-1]])
    
    return initials, last_name

def intelligent_group_authors(authors, similarity_threshold=0.85):
    """
    Group similar authors using multiple matching strategies:
    1. Fuzzy string matching
    2. Same last name + similar initials
    3. Common variations (John vs J, Robert vs R, etc.)
    """
    groups = defaultdict(list)
    grouped = set()
    
    # Common first name variations
    name_variations = {
        'james': ['james', 'jim', 'jimmy', 'j.', 'j'],
        'robert': ['robert', 'rob', 'bob', 'r.', 'r'],
        'william': ['william', 'bill', 'will', 'w.', 'w'],
        'richard': ['richard', 'dick', 'rick', 'r.', 'r'],
        'david': ['david', 'dave', 'd.', 'd'],
        'joseph': ['joseph', 'joe', 'j.', 'j'],
        'thomas': ['thomas', 'tom', 'tommy', 't.', 't'],
        'charles': ['charles', 'charlie', 'chuck', 'c.', 'c'],
        'christopher': ['christopher', 'chris', 'c.', 'c'],
        'daniel': ['daniel', 'dan', 'd.', 'd'],
        'matthew': ['matthew', 'matt', 'm.', 'm'],
        'anthony': ['anthony', 'tony', 'a.', 'a'],
        'margaret': ['margaret', 'peggy', 'm.', 'm'],
        'elizabeth': ['elizabeth', 'liz', 'beth', 'e.', 'e'],
        'barbara': ['barbara', 'barb', 'b.', 'b'],
        'catherine': ['catherine', 'catherine', 'cathy', 'c.', 'c'],
    }
    
    for idx, author1 in enumerate(authors):
        if idx in grouped:
            continue
        
        group_id = f"group_{idx}"
        groups[group_id].append(author1)
        grouped.add(idx)
        
        # Find similar authors
        for idx2 in range(idx + 1, len(authors)):
            if idx2 in grouped:
                continue
            
            author2 = authors[idx2]
            
            # Strategy 1: Direct fuzzy matching
            similarity = fuzzy_match(author1, author2)
            if similarity >= similarity_threshold:
                groups[group_id].append(author2)
                grouped.add(idx2)
                continue
            
            # Strategy 2: Check last name + initials match
            init1, last1 = extract_initials_and_lastname(author1)
            init2, last2 = extract_initials_and_lastname(author2)
            
            if last1 and last2 and last1 == last2:
                # Same last name - check if initials are similar or one is subset of the other
                if init1 and init2:
                    # Check for abbreviation matches (e.g., "A.B." and "Anne B.")
                    if (init1[0] == init2[0] or 
                        (len(init1) > 0 and len(init2) > 0 and init1[0] == init2[0])):
                        groups[group_id].append(author2)
                        grouped.add(idx2)
                        continue
                elif not init1 or not init2:
                    # One might be firstname-only, check similarity of what we have
                    if fuzzy_match(author1, author2, threshold=0.7) >= 0.7:
                        groups[group_id].append(author2)
                        grouped.add(idx2)
                        continue
            
            # Strategy 3: Check name variations
            parts1 = author1.split()
            parts2 = author2.split()
            if len(parts1) > 0 and len(parts2) > 0:
                # Check if any first names might be variations
                for var_list in name_variations.values():
                    if parts1[0].lower() in var_list and parts2[0].lower() in var_list:
                        # Both use variations of same name
                        if len(parts1) > 1 and len(parts2) > 1:
                            if fuzzy_match(parts1[-1], parts2[-1], threshold=0.85) >= 0.85:
                                groups[group_id].append(author2)
                                grouped.add(idx2)
                                break
    
    return groups

def select_canonical_name(author_group):
    """
    Select a canonical name for a group of authors.
    Prefer longer, more complete names.
    """
    # Sort by length (longer = more complete)
    sorted_authors = sorted(author_group, key=lambda x: len(x), reverse=True)
    
    # Filter out abbreviation-heavy names
    candidates = []
    for author in sorted_authors:
        # Count how many parts are just single letters or abbreviations
        parts = author.split()
        abbrev_count = sum(1 for p in parts if len(p) <= 2 and p.endswith('.') or len(p) == 1)
        candidates.append((author, abbrev_count))
    
    # Prefer names with fewer abbreviations
    candidates.sort(key=lambda x: x[1])
    
    return candidates[0][0]

def create_author_mapping(authors, similarity_threshold=0.85):
    """
    Create a mapping from all author variations to canonical names.
    """
    print(f"\nGrouping {len(authors)} authors using fuzzy matching...")
    print(f"Similarity threshold: {similarity_threshold}")
    
    groups = intelligent_group_authors(authors, similarity_threshold)
    
    print(f"Found {len(groups)} unique author(s)")
    
    # Create mapping table
    mapping = {}
    canonical_authors = []
    
    for group_id, author_group in sorted(groups.items()):
        # Select canonical name
        canonical = select_canonical_name(author_group)
        # Titlecase for better presentation
        canonical = ' '.join(word.capitalize() for word in canonical.split())
        
        canonical_authors.append({
            'canonical_name': canonical,
            'num_variations': len(author_group),
            'variations': '|'.join(sorted(author_group))
        })
        
        # Map all variations to canonical
        for variation in author_group:
            mapping[variation] = canonical
    
    return mapping, canonical_authors

def main():
    csv_path = "dimension_analysis/extracted_data.csv"
    
    print("=" * 80)
    print("AUTHOR DEDUPLICATION")
    print("=" * 80)
    
    # Load authors
    authors = load_author_data(csv_path)
    
    # Create mapping with fuzzy matching
    mapping, canonical_authors = create_author_mapping(authors, similarity_threshold=0.85)
    
    # Create output dataframes
    author_df = pd.DataFrame(canonical_authors)
    author_df = author_df.sort_values('canonical_name').reset_index(drop=True)
    
    print("\nAuthor Summary:")
    print(f"  Original author strings: {len(authors)}")
    print(f"  Unique authors (after deduplication): {len(author_df)}")
    print(f"  Authors with multiple variations: {(author_df['num_variations'] > 1).sum()}")
    
    # Show examples of duplicates found
    print("\nExamples of authors with multiple variations:")
    multi_var = author_df[author_df['num_variations'] > 1].head(10)
    for _, row in multi_var.iterrows():
        variations = row['variations'].split('|')
        print(f"  {row['canonical_name']} ({row['num_variations']} variations)")
        print(f"    → {', '.join(variations[:3])}")
        if row['num_variations'] > 3:
            print(f"    → ... and {row['num_variations'] - 3} more")
    
    # Save author lookup table
    lookup_df = pd.DataFrame([
        {'original_author': k, 'canonical_author': v}
        for k, v in mapping.items()
    ])
    lookup_df = lookup_df.sort_values('original_author')
    
    lookup_output = "dimension_analysis/author_lookup.csv"
    lookup_df.to_csv(lookup_output, index=False)
    print(f"\n✓ Saved author lookup table to {lookup_output}")
    print(f"  {len(lookup_df)} author-to-canonical mappings")
    
    # Save canonical author list
    authors_output = "dimension_analysis/canonical_authors.csv"
    author_df.to_csv(authors_output, index=False)
    print(f"✓ Saved canonical authors to {authors_output}")
    print(f"  {len(author_df)} unique authors")
    
    return mapping, author_df

if __name__ == "__main__":
    mapping, author_df = main()

#!/usr/bin/env python3
"""
Generate optimized Kumu JSON blueprint with semantic dimensions.
Papers as large nodes with semantic information, authors as smaller nodes.
Papers link to all their authors.
"""

import json
import pandas as pd
from pathlib import Path

def create_optimized_kumu_json():
    """Create Kumu-compatible JSON with semantic dimensions and proper sizing."""
    
    print("=" * 80)
    print("KUMU JSON - SEMANTIC DIMENSIONS EDITION")
    print("=" * 80)
    
    # Load source data
    csv_path = "dimension_analysis/extracted_data.csv"
    lookup_path = "dimension_analysis/author_lookup.csv"
    
    df = pd.read_csv(csv_path)
    author_lookup = pd.read_csv(lookup_path)
    
    print("\nLoading data...")
    print(f"Loaded {len(df)} publications")
    print(f"Loaded {len(author_lookup)} author mappings")
    
    # === PARSE AUTHORS ===
    author_mapping = dict(zip(author_lookup['original_author'].str.strip().str.lower(), 
                               author_lookup['canonical_author']))
    
    all_authors = set()
    paper_authors = {}
    
    for idx, row in df.iterrows():
        title = row['title']
        authors_str = row['authors']
        
        authors = [a.strip().lower() for a in str(authors_str).split(';')]
        canonical_authors = []
        
        for author in authors:
            if author:
                canonical = author_mapping.get(author, author.title())
                all_authors.add(canonical)
                canonical_authors.append(canonical)
        
        paper_authors[title] = canonical_authors
    
    print(f"\nFound {len(all_authors)} unique authors")
    print(f"Found {len(paper_authors)} publications with author lists")
    
    # === CREATE ELEMENTS (NODES) ===
    print("\nCreating elements...")
    
    elements = []
    
    # Publication elements (LARGE NODES)
    ecosystem_colors = {
        'Marine': '#1f77b4',
        'Freshwater': '#2ca02c',
        'Terrestrial': '#d62728',
        'Mixed': '#ff7f0e'
    }
    
    taxa_keywords = {
        'Bacteria': 'Bacteria',
        'Archaea': 'Archaea',
        'Protozoa': 'Protozoa',
        'Chromista': 'Chromista',
        'Plantae': 'Plantae',
        'Fungi': 'Fungi',
        'Animalia': 'Animalia'
    }
    
    method_keywords = {
        'Measurement': 'Measurement-based',
        'Inferential': 'Inferential'
    }
    
    for idx, row in df.iterrows():
        title = row['title']
        year = int(row['year']) if pd.notna(row['year']) else None
        ecosystem = row['ecosystem'] if pd.notna(row['ecosystem']) else 'Unknown'
        taxa = row['taxa'] if pd.notna(row['taxa']) else 'Unknown'
        method = row['method'] if pd.notna(row['method']) else 'Unknown'
        color = ecosystem_colors.get(ecosystem, '#7f7f7f')
        authors_count = len(paper_authors.get(title, []))
        
        # Build semantic dimensions dict
        semantic_dimensions = {
            'Ecosystem_Marine': float(row['ecosystem_Marine_similarity']) if pd.notna(row['ecosystem_Marine_similarity']) else 0,
            'Ecosystem_Freshwater': float(row['ecosystem_Freshwater_similarity']) if pd.notna(row['ecosystem_Freshwater_similarity']) else 0,
            'Ecosystem_Terrestrial': float(row['ecosystem_Terrestrial_similarity']) if pd.notna(row['ecosystem_Terrestrial_similarity']) else 0,
            'Ecosystem_Confidence': float(row['ecosystem_confidence']) if pd.notna(row['ecosystem_confidence']) else 0,
            'Taxa_Bacteria': float(row['taxa_Bacteria_similarity']) if pd.notna(row['taxa_Bacteria_similarity']) else 0,
            'Taxa_Archaea': float(row['taxa_Archaea_similarity']) if pd.notna(row['taxa_Archaea_similarity']) else 0,
            'Taxa_Protozoa': float(row['taxa_Protozoa_similarity']) if pd.notna(row['taxa_Protozoa_similarity']) else 0,
            'Taxa_Chromista': float(row['taxa_Chromista_similarity']) if pd.notna(row['taxa_Chromista_similarity']) else 0,
            'Taxa_Plantae': float(row['taxa_Plantae_similarity']) if pd.notna(row['taxa_Plantae_similarity']) else 0,
            'Taxa_Fungi': float(row['taxa_Fungi_similarity']) if pd.notna(row['taxa_Fungi_similarity']) else 0,
            'Taxa_Animalia': float(row['taxa_Animalia_similarity']) if pd.notna(row['taxa_Animalia_similarity']) else 0,
            'Taxa_Confidence': float(row['taxa_confidence']) if pd.notna(row['taxa_confidence']) else 0,
            'Method_Measurement': float(row['method_Measurement_similarity']) if pd.notna(row['method_Measurement_similarity']) else 0,
            'Method_Inferential': float(row['method_Inferential_similarity']) if pd.notna(row['method_Inferential_similarity']) else 0,
            'Method_Confidence': float(row['method_confidence']) if pd.notna(row['method_confidence']) else 0,
        }
        
        element = {
            "id": f"pub_{idx}",
            "label": title,
            "type": "Publication",
            "tags": ["Publication", ecosystem, taxa, method],
            "year": year,
            "ecosystem": ecosystem,
            "ecosystem_classification": ecosystem,
            "taxa": taxa,
            "taxa_classification": taxa,
            "method": method,
            "method_classification": method,
            "author_count": authors_count,
            "size": 50,  # Large node size for publications
            "color": color,
            "shape": "circle",
            "metadata": semantic_dimensions
        }
        
        elements.append(element)
    
    # Author elements (SMALL NODES)
    author_pub_counts = {}
    for title, authors in paper_authors.items():
        for author in authors:
            author_pub_counts[author] = author_pub_counts.get(author, 0) + 1
    
    for author in sorted(all_authors):
        pub_count = author_pub_counts.get(author, 0)
        elements.append({
            "id": f"auth_{author}",
            "label": author,
            "type": "Author",
            "tags": ["Author"],
            "publications_authored": pub_count,
            "size": max(5, min(20, 5 + int(pub_count * 1.5))),  # Small node size, scaled by publications
            "color": "#999999",
            "shape": "circle"
        })
    
    print(f"  - Created {len(df)} publication elements (large nodes)")
    print(f"  - Created {len(author_pub_counts)} author elements (small nodes)")
    
    # === CREATE CONNECTIONS ===
    print("\nCreating connections...")
    
    connections = []
    
    # Paper to Author connections (directed: paper -> author)
    for idx, row in df.iterrows():
        title = row['title']
        authors = paper_authors.get(title, [])
        
        for author in authors:
            connections.append({
                "id": f"conn_pub_{idx}_auth_{author}",
                "from": f"pub_{idx}",
                "to": f"auth_{author}",
                "type": "Authored By",
                "tags": ["Publication-Author"],
                "direction": "directed",
                "metadata": {
                    "relationship": "Publication written by Author",
                    "strength": 1
                }
            })
    
    # Co-authorship connections (undirected/mutual: author <-> author)
    coauthor_pairs = {}
    for title, authors in paper_authors.items():
        if len(authors) > 1:
            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    author1, author2 = sorted([authors[i], authors[j]])
                    pair_key = (author1, author2)
                    
                    if pair_key not in coauthor_pairs:
                        coauthor_pairs[pair_key] = 0
                    coauthor_pairs[pair_key] += 1
    
    for (author1, author2), count in coauthor_pairs.items():
        connections.append({
            "id": f"conn_auth_{author1}_with_{author2}",
            "from": f"auth_{author1}",
            "to": f"auth_{author2}",
            "type": "Collaborated With",
            "tags": ["Co-authorship"],
            "direction": "mutual",
            "metadata": {
                "relationship": "Authors collaborated",
                "collaboration_count": count,
                "papers_together": count
            }
        })
    
    print(f"  - Created {sum(1 for c in connections if c['type'] == 'Authored By')} publication-author connections")
    print(f"  - Created {sum(1 for c in connections if c['type'] == 'Collaborated With')} co-authorship connections")
    print(f"  - Total: {len(connections)} connections")
    
    # === CREATE BLUEPRINT ===
    print("\nCreating blueprint...")
    
    blueprint = {
        "name": "BioSCape Publication Network",
        "description": "Author collaboration and publication network with semantic dimensions from the BioSCape project",
        "focus": "Publication network showing papers (large nodes) with semantic semantic classifications and their authors (small nodes)",
        "elements": elements,
        "connections": connections,
        "metadata": {
            "total_elements": len(elements),
            "total_connections": len(connections),
            "publications": len(df),
            "authors": len(all_authors),
            "publication_author_links": sum(1 for c in connections if c['type'] == 'Authored By'),
            "collaboration_links": sum(1 for c in connections if c['type'] == 'Collaborated With'),
            "semantic_dimensions": ["Ecosystem", "Taxa", "Method"],
            "data_generated": "2026-02-16"
        }
    }
    
    # === SAVE JSON ===
    print("\nSaving optimized Kumu JSON blueprint...")
    
    output_dir = Path("network_analysis/kumu_import")
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / "biospace_semantic_network.json"
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(blueprint, f, indent=2, ensure_ascii=False)
    
    file_size = json_file.stat().st_size
    print(f"✓ Saved blueprint to {json_file}")
    print(f"  File size: {file_size / (1024*1024):.2f} MB")
    
    # === CREATE DOCUMENTATION ===
    doc = """# BioSCape Semantic Network - Kumu JSON

## Overview

This is an optimized Kumu JSON blueprint for visualizing the BioSCape publication network with semantic dimensions.

### Node Structure

**Publications (Large Nodes - Size 50)**
- Each publication is a large circular node
- Color-coded by primary ecosystem classification:
  - Blue (#1f77b4): Marine
  - Green (#2ca02c): Freshwater
  - Red (#d62728): Terrestrial
  - Orange (#ff7f0e): Mixed
- Contains rich semantic metadata:
  - Ecosystem similarities (Marine, Freshwater, Terrestrial) + confidence
  - Taxa similarities (7 kingdoms: Bacteria, Archaea, Protozoa, Chromista, Plantae, Fungi, Animalia) + confidence
  - Method similarities (Measurement, Inferential) + confidence
  - Year of publication
  - Number of authors

**Authors (Small Nodes - Size 5-20)**
- Each author is a small gray circular node
- Size scaled by number of publications (5-20px)
- Shows total number of publications authored

### Connection Types

**Publication → Author (Directed)**
- Type: "Authored By"
- Direction: Directed from publication to author
- Shows authorship relationships
- One connection per author per publication

**Author ↔ Author (Undirected/Mutual)**
- Type: "Collaborated With"
- Direction: Mutual/undirected
- Shows co-authorship relationships
- Strength indicated by collaboration_count (how many papers they wrote together)

### Semantic Dimensions Included

Each publication includes detailed semantic classification scores:

**Ecosystem Dimensions:**
- ecosystem_Marine_similarity: 0.0-1.0
- ecosystem_Freshwater_similarity: 0.0-1.0
- ecosystem_Terrestrial_similarity: 0.0-1.0
- ecosystem_confidence: Confidence in classification

**Taxa Dimensions:**
- taxa_Bacteria_similarity: 0.0-1.0
- taxa_Archaea_similarity: 0.0-1.0
- taxa_Protozoa_similarity: 0.0-1.0
- taxa_Chromista_similarity: 0.0-1.0
- taxa_Plantae_similarity: 0.0-1.0
- taxa_Fungi_similarity: 0.0-1.0
- taxa_Animalia_similarity: 0.0-1.0
- taxa_confidence: Confidence in classification

**Method Dimensions:**
- method_Measurement_similarity: 0.0-1.0
- method_Inferential_similarity: 0.0-1.0
- method_confidence: Confidence in classification

## Data Summary

- **Total Publications:** 72 (large nodes)
- **Total Authors:** 269 (small nodes)
- **Publication-Author Links:** 557
- **Co-authorship Links:** 2,667
- **Total Connections:** 3,224

## How to Import into Kumu

1. Go to https://kumu.io
2. Create a new map
3. Click the "+ Add" button → "Import"
4. Select "JSON" and paste the contents of this file, or upload the file
5. Kumu will automatically create:
   - Large nodes for publications
   - Small nodes for authors
   - Directed links from publications to authors
   - Undirected links between collaborating authors

## Visualization Tips

1. **Filter by Ecosystem:** Use tags to show only Marine, Freshwater, Terrestrial, or Mixed publications
2. **Filter by Taxa:** Show publications studying specific organism groups
3. **Filter by Method:** Show measurement-based vs. inferential studies
4. **Size Analysis:** Author node size indicates productivity (number of publications)
5. **Collaboration Patterns:** Thicker co-authorship lines = more frequent collaborations
6. **Semantic Exploration:** Hover over publication nodes to see detailed similarity scores

## Advanced Kumu Features

Once imported, you can:
- Enable "Collaboration mode" to modify and extend the network
- Create custom decorations based on semantic dimensions
- Set up filters and views for different research aspects
- Use metrics to analyze publication and author networks
- Export views for presentations

## File Format Details

- Format: JSON (Kumu Blueprint)
- Elements: 341 (72 publications + 269 authors)
- Connections: 3,224
- Custom Fields: Semantic dimensions (15 per publication)
- Ready for: Direct import into Kumu.io
"""
    
    doc_file = output_dir / "SEMANTIC_NETWORK_README.md"
    with open(doc_file, 'w') as f:
        f.write(doc)
    
    print(f"✓ Saved documentation to {doc_file}")
    
    print("\n" + "=" * 80)
    print("KUMU SEMANTIC NETWORK READY")
    print("=" * 80)
    print(f"\nFile: {json_file.absolute()}")
    print(f"Size: {file_size / (1024*1024):.2f} MB")
    print("\nKey Features:")
    print("  ✓ Publications as large nodes (size 50)")
    print("  ✓ Authors as small nodes (size 5-20, scaled by publications)")
    print("  ✓ All semantic dimensions included (Ecosystem, Taxa, Method)")
    print("  ✓ Directed links: Publication → Authors")
    print("  ✓ Mutual links: Author ↔ Author collaborations")
    print("  ✓ Color-coded by ecosystem")
    print("\nReady to import into Kumu!")

if __name__ == "__main__":
    create_optimized_kumu_json()

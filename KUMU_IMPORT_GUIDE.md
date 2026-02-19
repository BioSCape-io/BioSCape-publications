# BioSCape Kumu Import Guide

## What You Have Ready

### **File:** `biospace_semantic_network.json` (1.35 MB)
**Location:** `network_analysis/kumu_import/biospace_semantic_network.json`

## Network Summary

| Metric | Value |
|--------|-------|
| Total Elements (Nodes) | 341 |
| Publications | 72 |
| Authors | 269 |
| Total Connections | 3,241 |
| Publication-Author Links | 574 |
| Co-authorship Links | 2,667 |

## Node Types & Sizing

### Publications (LARGE NODES)
- **Size:** 50px (fixed)
- **Color:** Coded by primary ecosystem
  - Marine: Blue (#1f77b4)
  - Freshwater: Green (#2ca02c)
  - Terrestrial: Red (#d62728)
  - Mixed: Orange (#ff7f0e)
- **Metadata:** 15 semantic dimensions per publication
- **Visual Prominence:** Large, easily identified in the center of collaboration clusters

### Authors (SMALL NODES)
- **Size:** 5-20px (scaled by publication count)
  - 5px = authors with 1 publication
  - 20px = authors with 8+ publications
  - Average: 7.5px
- **Color:** Gray (#999999)
- **Metadata:** Publication count and author ID

## Connection Types

### 1. "Authored By" (Directed)
- **Direction:** Publication → Author
- **Count:** 574
- **Relationship:** Shows which authors wrote which papers
- **Strength:** All equal (1:1 relationship)
- **Visual:** Directed arrows from large paper nodes to small author nodes

### 2. "Collaborated With" (Mutual/Undirected)
- **Direction:** Author ↔ Author (mutual)
- **Count:** 2,667
- **Relationship:** Shows co-authorship relationships
- **Strength:** Variable (1-20+ collaborations)
- **Visual:** Thicker lines = more frequent collaborations

## Semantic Dimensions Included

Every publication contains 15 semantic dimension scores:

### Ecosystem (3 dimensions + confidence)
- `Ecosystem_Marine`: Similarity score (0.0-1.0)
- `Ecosystem_Freshwater`: Similarity score (0.0-1.0)
- `Ecosystem_Terrestrial`: Similarity score (0.0-1.0)
- `Ecosystem_Confidence`: How confident is the classification

### Taxa (7 dimensions + confidence)
- `Taxa_Bacteria`: Similarity score
- `Taxa_Archaea`: Similarity score
- `Taxa_Protozoa`: Similarity score
- `Taxa_Chromista`: Similarity score
- `Taxa_Plantae`: Similarity score
- `Taxa_Fungi`: Similarity score
- `Taxa_Animalia`: Similarity score
- `Taxa_Confidence`: Classification confidence

### Method (2 dimensions + confidence)
- `Method_Measurement`: Similarity score
- `Method_Inferential`: Similarity score
- `Method_Confidence`: Classification confidence

## How to Import into Kumu

### Step 1: Prepare the File
The JSON is ready to use as-is. No modifications needed.

### Step 2: Create/Open a Kumu Map
1. Go to https://kumu.io
2. Sign in to your account
3. Create a new map or open an existing one

### Step 3: Import the JSON
**Method A: File Upload**
1. Click **Settings** (gear icon)
2. Click **Import**
3. Select **JSON** format
4. Choose **Upload file**
5. Select `biospace_semantic_network.json`
6. Click **Import**

**Method B: Direct Paste**
1. Click **Settings** → **Import**
2. Select **JSON** format
3. Copy the entire contents of `biospace_semantic_network.json`
4. Paste into the import field
5. Click **Import**

### Step 4: Kumu Will Automatically
✓ Create 72 large publication nodes (size 50)
✓ Create 269 small author nodes (size 5-20, scaled by productivity)
✓ Create directed links from publications to their authors (574 connections)
✓ Create mutual co-authorship links between authors (2,667 connections)
✓ Apply ecosystem-based color coding to publications
✓ Add all semantic dimension data as node attributes

## What You Can Do in Kumu

### Filtering & Views
- Filter by **Ecosystem** tag (Marine, Freshwater, Terrestrial, Mixed)
- Filter by **Taxa** (see publications studying specific organisms)
- Filter by **Method** (Measurement-based vs. Inferential)
- Filter by **Author** (network around specific researchers)
- Filter by **Year** (evolution of research over time)

### Analysis
- **Author Productivity:** Author node size shows publication count
- **Collaboration Strength:** Line thickness shows co-authorship frequency
- **Research Focus:** Publication metadata reveals semantic dimensions
- **Network Density:** Identify central authors and key collaborators

### Customization
- Create custom **connection decorations** (e.g., color by collaboration count)
- Set up **element decorations** (e.g., icons by ecosystem)
- Build **views** for specific research questions
- Add **descriptions** and **comments** to nodes and connections
- Use **metrics** to analyze centrality, clustering, etc.

### Export & Sharing
- Export views as images for presentations
- Share interactive map with collaborators
- Export network statistics as reports
- Use for publication in presentations/papers

## Example Queries You Can Explore

1. **Which authors have the most publications?**
   - Look for the largest author nodes
   - Check `publications_authored` metadata

2. **Who are the most central collaborators?**
   - Apply **centrality metrics** in Kumu
   - Look for authors with most co-authorship connections

3. **What research topics are most common?**
   - Look at cluster of large publications
   - Check `ecosystem` and `taxa` classifications

4. **How has research evolved over time?**
   - Filter by `year` ranges
   - See publication topic shifts

5. **Are there isolated research groups?**
   - Look for disconnected author clusters
   - Identify silos or unique research approaches

6. **What's the primary ecosystem focus?**
   - Filter by ecosystem color
   - Check `Ecosystem_*` similarity scores

## Technical Details

### JSON Structure
- **elements:** Array of 341 nodes (72 publication + 269 author elements)
- **connections:** Array of 3,241 directed/mutual links
- **metadata:** Arbitrary custom fields per element (semantic dimensions, sizes, colors)

### Data Standards
- All IDs are unique and human-readable
- Connection IDs follow naming convention: `conn_source_to_target`
- All float values are between 0.0 and 1.0 (for similarity scores)
- Colors use standard hex notation (#RRGGBB)

### Browser Compatibility
The JSON format is compatible with:
- All modern web browsers
- Kumu.io's import system
- JSON validators and parsers
- Data visualization tools

## Questions & Troubleshooting

### Q: The JSON is large (1.35 MB). Will it work?
A: Yes! Kumu handles files up to 100MB. This will import smoothly.

### Q: Can I modify the semantic dimensions after import?
A: Yes! In Kumu, you can:
- Edit metadata for any element
- Add new metadata fields
- Modify connection metadata
- Changes are saved automatically

### Q: How do I see the similarity scores?
A: In Kumu:
1. Click on a publication node
2. Open the **Details** panel on the right
3. Scroll to see all metadata including Ecosystem_*, Taxa_*, Method_* fields
4. The values (0.0-1.0) show similarity strength

### Q: Can I set up custom styling based on semantic dimensions?
A: Yes! Kumu allows decoration rules:
1. Click **Decorate** in the sidebar
2. Create rules based on metadata fields
3. E.g., "Color all Plantae-focused papers green"

### Q: What if I want to add more data later?
A: You can:
1. Download the map as JSON from Kumu
2. Add more elements/connections
3. Re-import to update the map
4. Or edit directly in Kumu's editor

## Next Steps

1. ✓ JSON file is ready: `biospace_semantic_network.json`
2. → Open Kumu.io and create a new map
3. → Import the JSON using Settings → Import
4. → Explore the interactive network
5. → Apply filters and metrics
6. → Share with collaborators
7. → Export views for publications

## File Checksums

For verification purposes:
- **File:** biospace_semantic_network.json
- **Size:** 1.35 MB
- **Elements:** 341 total (72 publications, 269 authors)
- **Connections:** 3,241 total (574 authorship, 2,667 collaborations)
- **Semantic Dimensions per Publication:** 15 (ecosystem ×3, taxa ×7, method ×2, plus confidence)

---

**Generated:** 2026-02-16
**Format:** Kumu JSON Blueprint v1.0
**Status:** Ready for Import ✓

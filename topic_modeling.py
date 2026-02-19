"""
Semantic Classification for BioSCape Publications
Classifies publications by ecosystem, taxa, and method dimensions using semantic similarity.
"""

import os
import re
import numpy as np
import pandas as pd
from pyzotero import zotero
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import plotly.graph_objects as go
import plotly.express as px
import dateparser

# Configuration
API_KEY = os.environ.get('ZOTERO_API_KEY', "")
LIBRARY_ID = "2810748"
LIBRARY_TYPE = "group"
TARGET_COLLECTION = "U4SW8TCS"
OUTPUT_DIR = "dimension_analysis"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def reformat_date(date_str: str) -> str:
    """
    Parse a date string and return the year.
    Uses dateparser for robust parsing, with regex fallback.
    """
    if not date_str:
        return ''

    formatted_date = None

    # First try parsing with dateparser
    datetime_obj = dateparser.parse(date_str)
    if datetime_obj is not None:
        # Format it as YYYY
        formatted_date = datetime_obj.strftime('%Y')

    # Backup: just take the first 4-digit number
    if formatted_date is None:
        match = re.findall(r"\d{4}", date_str)
        if match:
            formatted_date = match[0]
            print(f"Using backup date parsing for {date_str} -> {formatted_date}")
        else:
            formatted_date = ''

    return formatted_date

def extract_zotero_data():
    """
    Extract title, authors, and abstracts from Zotero library.
    Returns a pandas DataFrame.
    """
    print("Fetching data from Zotero...")
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)
    items = zot.collection_items_top(TARGET_COLLECTION)
    
    records = []
    for item in items:
        data = item['data']
        
        # Extract title
        title = data.get('title', '')
        
        # Extract authors
        creators = data.get('creators', [])
        authors = []
        for c in creators:
            first_name = c.get('firstName', '')
            last_name = c.get('lastName', '')
            name = c.get('name', '')
            
            if first_name and last_name:
                authors.append(f"{first_name} {last_name}")
            elif name:
                authors.append(name)
            elif last_name:
                authors.append(last_name)
        
        authors_str = '; '.join(authors)
        
        # Extract abstract
        abstract = data.get('abstractNote', '')
        
        # Extract additional metadata
        item_type = data.get('itemType', '')
        year = reformat_date(data.get('date', ''))
        url = data.get('url', '')
        
        # Only include items with abstracts (needed for topic modeling)
        if abstract and abstract.strip():
            records.append({
                'title': title,
                'authors': authors_str,
                'abstract': abstract,
                'item_type': item_type,
                'year': year,
                'url': url
            })
    
    df = pd.DataFrame(records)
    print(f"Extracted {len(df)} publications with abstracts")
    return df

def classify_documents_by_semantic_similarity(df):
    """
    Classify documents across multiple dimensions using semantic similarity
    between document embeddings and category description embeddings.
    
    Args:
        df: DataFrame with 'abstract' and 'title' columns
    
    Returns:
        df: DataFrame with new dimension columns added
    """
    print("\nClassifying documents using semantic similarity...")
    
    # Define dimension categories with rich descriptions
    dimensions = {
        'ecosystem': {
            'Marine': """
                Marine and ocean ecosystems including coastal waters, seawater environments, 
                phytoplankton communities, kelp forests, coral reefs, pelagic zones, benthic 
                habitats, intertidal areas, and offshore environments. Studies of saltwater 
                biodiversity, marine organisms, ocean processes, and coastal ecology.
            """,
            'Freshwater': """
                Freshwater ecosystems including rivers, streams, lakes, ponds, wetlands, 
                riparian zones, floodplains, and inland water bodies. Studies of freshwater 
                aquatic organisms, river ecology, lake systems, wetland habitats, and 
                inland water quality and biodiversity.
            """,
            'Terrestrial': """
                Land-based terrestrial ecosystems including forests, grasslands, savannas, 
                fynbos, shrublands, woodlands, and upland habitats. Studies of trees, 
                vegetation structure, canopy dynamics, soil systems, and land-dwelling 
                organisms and their interactions.
            """
        },
        'taxa': {
            'Bacteria': """
                Bacteria and bacterial organisms. Studies of prokaryotic bacteria, bacterial 
                diversity, microbial communities, bacterial ecology, bacterioplankton, 
                nitrogen-fixing bacteria, decomposer bacteria, and bacterial processes in 
                ecosystems.
            """,
            'Archaea': """
                Archaea and archaeal organisms. Studies of archaeal diversity, extremophile 
                archaea, methanogenic archaea, archaeal ecology, and archaeal contributions 
                to biogeochemical cycles.
            """,
            'Protozoa': """
                Protozoa and single-celled eukaryotic organisms. Studies of protozoans, 
                amoebae, ciliates, flagellates, parasitic protozoa, heterotrophic protists, 
                and protozoan ecology in aquatic and terrestrial systems.
            """,
            'Chromista': """
                Chromista including algae, diatoms, kelp, and related organisms. Studies of 
                brown algae, golden algae, diatoms, seaweeds, kelp forests, algal blooms, 
                and chromistan photosynthesis and ecology.
            """,
            'Plantae': """
                Plants including true plants, mosses, ferns, and green algae. Studies of 
                vascular plants, trees, shrubs, herbs, grasses, flowers, crops, vegetation, 
                flora, plant diversity, botanical ecology, photosynthesis, and terrestrial 
                plant communities.
            """,
            'Fungi': """
                Fungi including mushrooms, yeasts, molds, and mycorrhizae. Studies of fungal 
                diversity, fungal ecology, decomposer fungi, mycorrhizal associations, 
                fungal pathogens, and fungal contributions to nutrient cycling.
            """,
            'Animalia': """
                Animals including all multicellular animal life. Studies of mammals, birds, 
                reptiles, amphibians, fish, invertebrates, insects, arthropods, mollusks, 
                worms, wildlife, fauna, animal behavior, vertebrate and invertebrate ecology, 
                and zoology.
            """
        },
        'method': {
            'Measurement': """
                Direct measurement, physical observation, and deterministic approaches. Studies 
                using instruments, sensors, remote sensing, spectroscopy, field measurements, 
                mechanical models, physics-based methods, and direct quantification of 
                physical properties. Empirical data collection through observation and 
                instrumentation.
            """,
            'Inferential': """
                Statistical analysis, inferential methods, and probabilistic approaches. Studies 
                using statistical modeling, inference, hypothesis testing, machine learning, 
                data mining, predictive models, uncertainty quantification, and pattern 
                recognition. Approaches focused on deriving insights from data through 
                statistical and computational methods.
            """
        }
    }
    
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    # Use the same model as BERTopic for consistency
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Generating embeddings for documents...")
    # Combine title and abstract for richer context
    document_texts = (df['title'] + '. ' + df['abstract']).tolist()
    document_embeddings = embedding_model.encode(
        document_texts, 
        show_progress_bar=True,
        batch_size=32
    )
    
    # Classify each dimension
    for dimension_name, categories in dimensions.items():
        print(f"\n  Classifying {dimension_name} dimension...")
        
        # Embed category descriptions
        category_names = list(categories.keys())
        category_descriptions = [desc.strip() for desc in categories.values()]
        category_embeddings = embedding_model.encode(category_descriptions)
        
        # Compute cosine similarity between each document and each category
        similarities = cosine_similarity(document_embeddings, category_embeddings)
        
        # Store similarity scores for each category
        for i, cat_name in enumerate(category_names):
            df[f'{dimension_name}_{cat_name}_similarity'] = similarities[:, i]
        
        # Assign primary category (highest similarity)
        max_indices = similarities.argmax(axis=1)
        df[dimension_name] = [category_names[i] for i in max_indices]
        
        # Calculate confidence (difference between top 2 similarity scores)
        sorted_sims = np.sort(similarities, axis=1)
        top_scores = sorted_sims[:, -1]
        second_scores = sorted_sims[:, -2]
        df[f'{dimension_name}_confidence'] = top_scores - second_scores
        
        # Mark as 'Mixed' if confidence is low (top 2 categories are very similar)
        low_confidence_threshold = 0.05  # Can be adjusted
        is_low_confidence = df[f'{dimension_name}_confidence'] < low_confidence_threshold
        df.loc[is_low_confidence, dimension_name] = 'Mixed'
        
        # Print distribution and statistics
        print(f"    Distribution:")
        for cat, count in df[dimension_name].value_counts().items():
            print(f"      {cat}: {count} documents")
        print(f"    Average confidence: {df[f'{dimension_name}_confidence'].mean():.3f}")
        print(f"    Low confidence (Mixed): {is_low_confidence.sum()} documents")
    
    return df

def create_visualizations(df, output_dir):
    """
    Create various visualizations of the dimension classifications.
    """
    print("Creating visualizations...")
    
    # 1. Sankey diagram: Flow between dimensions
    if 'ecosystem' in df.columns and 'taxa' in df.columns and 'method' in df.columns:
        try:
            # Create flow data
            df_flow = df[['ecosystem', 'taxa', 'method']].copy()
            
            # Create source-target pairs for Sankey
            eco_taxa = df_flow.groupby(['ecosystem', 'taxa']).size().reset_index(name='count')
            taxa_method = df_flow.groupby(['taxa', 'method']).size().reset_index(name='count')
            
            # Build node list
            nodes = []
            node_dict = {}
            node_idx = 0
            
            for eco in df_flow['ecosystem'].unique():
                node_dict[('eco', eco)] = node_idx
                nodes.append(f"Eco: {eco}")
                node_idx += 1
            
            for taxa in df_flow['taxa'].unique():
                node_dict[('taxa', taxa)] = node_idx
                nodes.append(f"Taxa: {taxa}")
                node_idx += 1
            
            for method in df_flow['method'].unique():
                node_dict[('method', method)] = node_idx
                nodes.append(f"Method: {method}")
                node_idx += 1
            
            # Build links
            sources = []
            targets = []
            values = []
            
            for _, row in eco_taxa.iterrows():
                sources.append(node_dict[('eco', row['ecosystem'])])
                targets.append(node_dict[('taxa', row['taxa'])])
                values.append(row['count'])
            
            for _, row in taxa_method.iterrows():
                sources.append(node_dict[('taxa', row['taxa'])])
                targets.append(node_dict[('method', row['method'])])
                values.append(row['count'])
            
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=nodes
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values
                )
            )])
            
            fig.update_layout(
                title="Publication Flow: Ecosystem → Taxa → Method",
                font_size=12,
                height=600
            )
            fig.write_html(f"{output_dir}/dimension_flow.html")
            print(f"Saved dimension flow diagram to {output_dir}/dimension_flow.html")
        except Exception as e:
            print(f"Could not create dimension flow: {e}")
    
    # 2. Treemap of all dimensions
    if 'ecosystem' in df.columns and 'taxa' in df.columns and 'method' in df.columns:
        try:
            # Create hierarchical data for treemap
            df_tree = df[['ecosystem', 'taxa', 'method']].copy()
            df_tree['count'] = 1
            
            # Aggregate by all three dimensions
            tree_data = df_tree.groupby(['ecosystem', 'taxa', 'method']).size().reset_index(name='count')
            
            # Prepare data for treemap
            labels = ['All Publications']
            parents = ['']
            values = [len(df)]
            
            # Add ecosystems
            for eco in df['ecosystem'].unique():
                labels.append(eco)
                parents.append('All Publications')
                values.append(len(df[df['ecosystem'] == eco]))
                
                # Add taxa under each ecosystem
                for taxa in df[df['ecosystem'] == eco]['taxa'].unique():
                    label = f"{eco}/{taxa}"
                    labels.append(label)
                    parents.append(eco)
                    values.append(len(df[(df['ecosystem'] == eco) & (df['taxa'] == taxa)]))
            
            fig = go.Figure(go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                textposition='middle center',
                marker=dict(colorscale='Viridis', line=dict(width=2))
            ))
            
            fig.update_layout(
                title="Hierarchical View: Ecosystem → Taxa",
                height=600
            )
            fig.write_html(f"{output_dir}/dimension_treemap.html")
            print(f"Saved dimension treemap to {output_dir}/dimension_treemap.html")
        except Exception as e:
            print(f"Could not create dimension treemap: {e}")
    
    # 3. Sunburst chart showing hierarchical breakdown
    if 'ecosystem' in df.columns and 'taxa' in df.columns and 'method' in df.columns:
        try:
            df_sunburst = df[['ecosystem', 'taxa', 'method']].copy()
            df_sunburst['count'] = 1
            
            # Aggregate data
            sunburst_data = df_sunburst.groupby(['ecosystem', 'taxa', 'method']).size().reset_index(name='count')
            
            fig = px.sunburst(
                sunburst_data,
                path=['ecosystem', 'taxa', 'method'],
                values='count',
                title='Hierarchical Breakdown: Ecosystem → Taxa → Method',
                color='count',
                color_continuous_scale='RdYlBu_r'
            )
            
            fig.update_layout(height=700)
            fig.write_html(f"{output_dir}/dimension_sunburst.html")
            print(f"Saved dimension sunburst to {output_dir}/dimension_sunburst.html")
        except Exception as e:
            print(f"Could not create dimension sunburst: {e}")
    
    # 4. Parallel coordinates plot showing dimension relationships
    if 'ecosystem' in df.columns and 'taxa' in df.columns and 'method' in df.columns:
        try:
            df_parallel = df.copy()
            
            # Create numeric encodings for categorical dimensions
            df_parallel['ecosystem_code'] = pd.Categorical(df_parallel['ecosystem']).codes
            df_parallel['taxa_code'] = pd.Categorical(df_parallel['taxa']).codes
            df_parallel['method_code'] = pd.Categorical(df_parallel['method']).codes
            
            # Get category labels for the axes
            eco_labels = dict(enumerate(pd.Categorical(df_parallel['ecosystem']).categories))
            taxa_labels = dict(enumerate(pd.Categorical(df_parallel['taxa']).categories))
            method_labels = dict(enumerate(pd.Categorical(df_parallel['method']).categories))
            
            dimensions = [
                dict(range=[df_parallel['ecosystem_code'].min(), df_parallel['ecosystem_code'].max()],
                     label='Ecosystem',
                     values=df_parallel['ecosystem_code'],
                     tickvals=list(eco_labels.keys()),
                     ticktext=list(eco_labels.values())),
                dict(range=[df_parallel['taxa_code'].min(), df_parallel['taxa_code'].max()],
                     label='Taxa',
                     values=df_parallel['taxa_code'],
                     tickvals=list(taxa_labels.keys()),
                     ticktext=list(taxa_labels.values())),
                dict(range=[df_parallel['method_code'].min(), df_parallel['method_code'].max()],
                     label='Method',
                     values=df_parallel['method_code'],
                     tickvals=list(method_labels.keys()),
                     ticktext=list(method_labels.values()))
            ]
            
            # Add confidence scores if available
            if 'ecosystem_confidence' in df_parallel.columns:
                dimensions.append(
                    dict(range=[0, df_parallel['ecosystem_confidence'].max()],
                         label='Eco Confidence',
                         values=df_parallel['ecosystem_confidence'])
                )
            
            fig = go.Figure(data=go.Parcoords(
                line=dict(
                    color=df_parallel['ecosystem_code'],
                    colorscale='Viridis',
                    showscale=True
                ),
                dimensions=dimensions
            ))
            
            fig.update_layout(
                title='Parallel Coordinates: Dimension Relationships',
                height=500
            )
            fig.write_html(f"{output_dir}/dimension_parallel_coordinates.html")
            print(f"Saved parallel coordinates to {output_dir}/dimension_parallel_coordinates.html")
        except Exception as e:
            print(f"Could not create parallel coordinates: {e}")
    
    # 5. Cross-dimension heatmap (Ecosystem x Taxa)
    if 'ecosystem' in df.columns and 'taxa' in df.columns:
        try:
            cross_tab = pd.crosstab(df['ecosystem'], df['taxa'])
            
            fig = px.imshow(
                cross_tab,
                labels=dict(x="Taxa", y="Ecosystem", color="Count"),
                title='Publications by Ecosystem and Taxa',
                text_auto=True,
                aspect='auto',
                color_continuous_scale='Blues'
            )
            fig.write_html(f"{output_dir}/ecosystem_taxa_matrix.html")
            print(f"Saved cross-dimension analysis to {output_dir}/ecosystem_taxa_matrix.html")
        except Exception as e:
            print(f"Could not create ecosystem-taxa matrix: {e}")
    
    # 6. Confidence distributions
    if 'ecosystem_confidence' in df.columns or 'taxa_confidence' in df.columns or 'method_confidence' in df.columns:
        try:
            fig = go.Figure()
            if 'ecosystem_confidence' in df.columns:
                fig.add_trace(go.Histogram(x=df['ecosystem_confidence'], name='Ecosystem', opacity=0.6))
            if 'taxa_confidence' in df.columns:
                fig.add_trace(go.Histogram(x=df['taxa_confidence'], name='Taxa', opacity=0.6))
            if 'method_confidence' in df.columns:
                fig.add_trace(go.Histogram(x=df['method_confidence'], name='Method', opacity=0.6))
            fig.update_layout(
                title='Classification Confidence Distributions',
                xaxis_title='Confidence Score',
                yaxis_title='Number of Documents',
                barmode='overlay'
            )
            fig.write_html(f"{output_dir}/confidence_distributions.html")
            print(f"Saved confidence distributions to {output_dir}/confidence_distributions.html")
        except Exception as e:
            print(f"Could not create confidence distributions: {e}")

def generate_summary(df, output_dir):
    """Generate a human-readable summary of dimensions."""
    
    with open(f"{output_dir}/dimension_summary.txt", 'w') as f:
        f.write("BioSCape Publications - Topic Analysis Summary\n")
        f.write("=" * 60 + "\n\n")
        
        # Dimension summaries
        if 'ecosystem' in df.columns:
            f.write("ECOSYSTEM DIMENSION\n")
            f.write("-" * 60 + "\n")
            for cat, count in df['ecosystem'].value_counts().sort_index().items():
                pct = (count / len(df)) * 100
                f.write(f"{cat}: {count} documents ({pct:.1f}%)\n")
            if 'ecosystem_confidence' in df.columns:
                f.write(f"Average confidence: {df['ecosystem_confidence'].mean():.3f}\n")
            f.write("\n")
        
        if 'taxa' in df.columns:
            f.write("TAXA DIMENSION\n")
            f.write("-" * 60 + "\n")
            for cat, count in df['taxa'].value_counts().sort_index().items():
                pct = (count / len(df)) * 100
                f.write(f"{cat}: {count} documents ({pct:.1f}%)\n")
            if 'taxa_confidence' in df.columns:
                f.write(f"Average confidence: {df['taxa_confidence'].mean():.3f}\n")
            f.write("\n")
        
        if 'method' in df.columns:
            f.write("METHOD DIMENSION\n")
            f.write("-" * 60 + "\n")
            for cat, count in df['method'].value_counts().sort_index().items():
                pct = (count / len(df)) * 100
                f.write(f"{cat}: {count} documents ({pct:.1f}%)\n")
            if 'method_confidence' in df.columns:
                f.write(f"Average confidence: {df['method_confidence'].mean():.3f}\n")
            f.write("\n")
    
    print(f"Saved dimension summary to {output_dir}/dimension_summary.txt")

def generate_dashboard_html(output_dir):
    """Generate a consolidated HTML dashboard with all visualizations."""
    print(f"\nGenerating consolidated dashboard...")
    
    # Get list of available visualizations
    import glob
    viz_files = [os.path.basename(f) for f in glob.glob(f"{output_dir}/*.html") if 'dashboard' not in f]
    
    # Define visualization order and titles
    viz_info = {
        'ecosystem_over_time.html': ('Ecosystem Distribution Over Time', 'dimension'),
        'taxa_over_time.html': ('Taxa Distribution Over Time', 'dimension'),
        'method_over_time.html': ('Method Distribution Over Time', 'dimension'),
        'ecosystem_taxa_matrix.html': ('Ecosystem × Taxa Cross-Analysis', 'dimension'),
        'confidence_distributions.html': ('Classification Confidence Scores', 'dimension'),
        'topics_over_time.html': ('Research Topics Over Time', 'topic'),
        'topic_distance_map.html': ('Topic Distance Map', 'topic'),
        'topic_barchart.html': ('Top Terms per Topic', 'topic'),
        'topic_hierarchy.html': ('Topic Hierarchy', 'topic'),
        'topic_heatmap.html': ('Topic Similarity Heatmap', 'topic'),
    }
    
    # Organize by category
    dimension_viz = [(f, title) for f, (title, cat) in viz_info.items() if cat == 'dimension' and f in viz_files]
    topic_viz = [(f, title) for f, (title, cat) in viz_info.items() if cat == 'topic' and f in viz_files]
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BioSCape Publications - Analysis Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        
        .section {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .viz-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}
        
        .viz-container {{
            background: #f8f9fa;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .viz-container:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        
        .viz-title {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            font-size: 1.2em;
            font-weight: 600;
        }}
        
        .viz-frame {{
            width: 100%;
            height: 600px;
            border: none;
            background: white;
        }}
        
        .info-box {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .info-box h3 {{
            color: #1976d2;
            margin-bottom: 10px;
        }}
        
        .data-files {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 15px;
        }}
        
        .data-file {{
            background: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            color: #667eea;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }}
        
        .data-file:hover {{
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        @media (max-width: 900px) {{
            .viz-grid {{
                grid-template-columns: 1fr;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌍 BioSCape Publications Analysis Dashboard</h1>
            <p class="subtitle">Multi-dimensional Classification & Topic Modeling</p>
            <p class="timestamp">Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="section">
            <div class="info-box">
                <h3>📊 About This Dashboard</h3>
                <p>This dashboard visualizes publications from the BioSCape Zotero library across multiple dimensions:</p>
                <ul style="margin: 10px 0 10px 20px; line-height: 1.8;">
                    <li><strong>Ecosystem:</strong> Marine, Freshwater, Terrestrial</li>
                    <li><strong>Taxa:</strong> Vertebrates, Plants, Plankton</li>
                    <li><strong>Method:</strong> Measurement/Physics, Statistical/Inferential</li>
                    <li><strong>Topics:</strong> Automatically discovered research themes using BERTopic</li>
                </ul>
                <p style="margin-top: 10px;">Classifications are performed using semantic similarity with sentence embeddings.</p>
            </div>
            
            <h3 style="color: #667eea; margin-top: 20px;">📁 Data Files</h3>
            <div class="data-files">
                <a href="extracted_data.csv" class="data-file">📄 Extracted Data</a>
                <a href="documents_with_topics.csv" class="data-file">📄 Documents + Topics</a>
                <a href="topic_info.csv" class="data-file">📄 Topic Info</a>
                <a href="topic_summary.txt" class="data-file">📄 Summary (TXT)</a>
            </div>
        </div>
"""
    
    # Add dimension visualizations
    if dimension_viz:
        html_content += """
        <div class="section">
            <h2 class="section-title">📐 Dimension Analysis</h2>
            <p style="color: #666; margin-bottom: 20px;">Publications classified across ecosystem, taxa, and methodological dimensions using semantic similarity.</p>
            <div class="viz-grid">
"""
        for filename, title in dimension_viz:
            html_content += f"""
                <div class="viz-container">
                    <div class="viz-title">{title}</div>
                    <iframe src="{filename}" class="viz-frame"></iframe>
                </div>
"""
        html_content += """
            </div>
        </div>
"""
    
    # Add topic visualizations
    if topic_viz:
        html_content += """
        <div class="section">
            <h2 class="section-title">🔍 Topic Modeling Analysis</h2>
            <p style="color: #666; margin-bottom: 20px;">Research themes automatically discovered using BERTopic with HDBSCAN clustering and sentence embeddings.</p>
            <div class="viz-grid">
"""
        for filename, title in topic_viz:
            html_content += f"""
                <div class="viz-container">
                    <div class="viz-title">{title}</div>
                    <iframe src="{filename}" class="viz-frame"></iframe>
                </div>
"""
        html_content += """
            </div>
        </div>
"""
    
    html_content += """
        <footer style="text-align: center; color: white; margin-top: 30px; padding: 20px;">
            <p>Generated by BioSCape Publications Topic Modeling Analysis</p>
            <p style="font-size: 0.9em; margin-top: 5px;">Re-run dimension_analysis.py to update this dashboard</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # Write the dashboard HTML file
    dashboard_path = f"{output_dir}/dashboard.html"
    with open(dashboard_path, 'w') as f:
        f.write(html_content)
    
    print(f"✓ Saved dashboard to {dashboard_path}")
    return dashboard_path

def main():
    """Main execution function."""
    print("Starting BioSCape Dimension Classification Analysis")
    print("=" * 60)
    
    # Step 1: Extract data from Zotero
    df = extract_zotero_data()
    
    # Check if we have enough documents
    if len(df) < 1:
        print("Error: No documents found")
        return
    
    # Step 2: Classify documents by dimensions using semantic similarity
    df = classify_documents_by_semantic_similarity(df)
    
    # Save extracted and classified data
    df.to_csv(f"{OUTPUT_DIR}/extracted_data.csv", index=False)
    print(f"\nSaved extracted and classified data to {OUTPUT_DIR}/extracted_data.csv")
    
    # Step 3: Create visualizations
    create_visualizations(df, OUTPUT_DIR)
    
    # Step 4: Generate summary
    generate_summary(df, OUTPUT_DIR)
    
    # Step 5: Generate consolidated dashboard
    dashboard_path = generate_dashboard_html(OUTPUT_DIR)
    
    print("\n" + "=" * 60)
    print("Dimension classification analysis complete!")
    print(f"Results saved to {OUTPUT_DIR}/ directory")
    print(f"\n🎯 OPEN THIS: file://{os.path.abspath(dashboard_path)}")
    print("\nKey outputs:")
    print(f"  - dashboard.html: 📊 CONSOLIDATED DASHBOARD (open this!)")
    print(f"  - extracted_data.csv: All documents with dimension classifications")
    print(f"  - dimension_summary.txt: Human-readable summary")
    print(f"  - dimension_flow.html: Sankey diagram of dimension relationships")
    print(f"  - dimension_treemap.html: Hierarchical view of ecosystems and taxa")
    print(f"  - dimension_sunburst.html: Complete hierarchy visualization")
    print(f"  - dimension_parallel_coordinates.html: Multi-dimensional relationships")
    print(f"  - ecosystem_taxa_matrix.html: Cross-dimension heatmap")
    print(f"  - confidence_distributions.html: Classification confidence scores")

if __name__ == "__main__":
    main()

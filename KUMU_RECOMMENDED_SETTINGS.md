# Kumu Advanced Editor Settings - BioSCape Publication Network

## Overview

This document provides recommended Advanced Editor settings for the BioSCape publication network map. These settings will optimize visualization, performance, and interactivity for analyzing author collaborations and publication metadata.

**Reference:** https://docs.kumu.io/overview/advanced-editor-hub

---

## Quick Start: Recommended @settings Block

Copy this into your Advanced Editor to apply optimal settings for the BioSCape network:

```
@settings {
  /* Theme & Quality */
  *-theme: light;
  *-quality: high;
  *-layout: force-directed;
  
  /* Element Defaults */
  element-size: 30;
  element-color: #999999;
  element-border-color: #444444;
  element-border-width: 2;
  element-font-size: 11;
  element-font-color: #222222;
  element-shape: circle;
  
  /* Connection Defaults */
  connection-color: #cccccc;
  connection-width: 1;
  connection-opacity: 0.6;
  connection-font-size: 10;
  connection-arrow: on;
  
  /* Force-Directed Layout Optimization */
  element-repulsion: 1500;
  element-min-distance: 60;
  connection-attraction: 0.3;
  
  /* Font Settings */
  font-family: "Open Sans", sans-serif;
  font-weight: normal;
}
```

---

## Advanced Editor Learning Path

### 1. **Essential Foundations** (Start Here)
- **Selectors:** Control which elements/connections your rules apply to
- **Property Reference:** Complete list of all decorative properties
- **@settings Block:** Configure global map defaults
  - Reference: https://docs.kumu.io/overview/advanced-editor-hub/settings-reference

### 2. **Most Commonly Used Features**

#### A. Data-Driven Decorations
Style elements and connections based on their metadata:

**Example: Color publications by ecosystem**
```
/* Match publication nodes with "Marine" ecosystem tag */
publication[ecosystem="Marine"] {
  color: #1f77b4;
  size: 50;
}

publication[ecosystem="Freshwater"] {
  color: #2ca02c;
  size: 50;
}

publication[ecosystem="Terrestrial"] {
  color: #d62728;
  size: 50;
}

publication[ecosystem="Mixed"] {
  color: #ff7f0e;
  size: 50;
}
```

**Example: Size authors by publication count**
```
author {
  size: 5;
}

author[publications_authored>=5] {
  size: 10;
}

author[publications_authored>=10] {
  size: 15;
}

author[publications_authored>=15] {
  size: 20;
}
```

#### B. Flags
Highlight important nodes with visual indicators:

```
/* Flag prolific co-authors */
author[publications_authored>=10] {
  flag: "Prolific";
  flag-color: gold;
}

/* Flag recent publications */
publication[year>=2020] {
  flag: "Recent";
  flag-color: green;
}
```

#### C. Icons
Add visual symbols to nodes:

```
/* Icons for publication types */
publication[ecosystem="Marine"] {
  icon: wave;
  icon-color: #1f77b4;
}

publication[ecosystem="Terrestrial"] {
  icon: tree;
  icon-color: #d62728;
}

author {
  icon: person;
  icon-color: #999999;
}
```

#### D. Label Templates
Customize displayed labels using node data:

```
/* Show author name and publication count */
author {
  label: <span data-attr="label"> (<span data-attr="publications_authored">)</span>;
}

/* Show publication title and year */
publication {
  label: <span data-attr="label"><br/><span style="font-size: 0.8em">(<span data-attr="year">)</span>;
}
```

#### E. Popovers
Enhanced information panels on hover:

```
publication {
  popover: <div class="popover-header"><strong>{{label}}</strong></div>
           <div><strong>Year:</strong> {{year}}</div>
           <div><strong>Ecosystem:</strong> {{ecosystem}}</div>
           <div><strong>Authors:</strong> {{author_count}}</div>
           <div><strong>Method:</strong> {{method}}</div>;
}

author {
  popover: <div class="popover-header"><strong>{{label}}</strong></div>
           <div><strong>Publications:</strong> {{publications_authored}}</div>;
}
```

#### F. Filter
Show/hide elements based on metadata:

```
/* Interactive filtering documentation */
publication[ecosystem="Marine"] { display: block; }
publication[ecosystem="Marine"] { display: none; } /* Toggle visibility */
```

#### G. Showcase
Highlight specific subsets:

```
/* Highlight recent marine research */
publication[ecosystem="Marine"][year>=2020],
author[publications_authored>=5] {
  color: #1f77b4;
  size: 40;
  border-width: 3;
}
```

#### H. Focus
Emphasize and contextualize specific elements:

```
/* Interactive focus - uses controls (see Advanced Features) */
```

#### I. Cluster
Group related elements:

```
/* Group by ecosystem */
publication[ecosystem="Marine"] {
  cluster: "Marine";
  cluster-color: #1f77b4;
}

publication[ecosystem="Freshwater"] {
  cluster: "Freshwater";
  cluster-color: #2ca02c;
}
```

#### J. Controls
Add interactive controls for filtering and clustering:

```
@controls {
  top {
    control type: filter
           target: publication
           by: ecosystem
    ;
    
    control type: cluster
           target: publication
           by: ecosystem
    ;
  }
  
  top {
    control type: showcase
           label: "Prolific Authors"
           targets: author[publications_authored>=10]
    ;
  }
}
```

---

## Less Commonly Used Features

### Bridge
Connect external maps and import subsets of networks:
- Reference: https://docs.kumu.io/guides/bridge#bridge-in-the-advanced-editor

### Custom Force-Directed Layout
Fine-tune physics simulation for optimal arrangement:
- Reference: https://docs.kumu.io/guides/layouts/force-directed#change-the-forces-underlying-strengths

```
@settings {
  /* Recommended for publication network */
  element-repulsion: 1500;      /* Spread elements apart */
  element-min-distance: 60;     /* Minimum spacing */
  connection-attraction: 0.3;   /* Co-authored connections */
  element-physics: on;
  element-damping: 0.4;
}
```

### Geo Template
Map network to geographic locations (if location data available)
- Reference: https://docs.kumu.io/guides/templates/geo

### Underlays
Add background images or patterns:
- Reference: https://docs.kumu.io/guides/underlays

### Background Images
Add text and graphics behind the network:
- Reference: https://docs.kumu.io/guides/decorate/images#add-a-background-image

---

## Power User Features

### Scatter Plots
Create 2D scatter visualization by metadata dimensions:

```
@settings {
  *-layout: scatter;
  *-x-axis: author.publications_authored;    /* X-axis: productivity */
  *-y-axis: author.collaboration_count;      /* Y-axis: collaboration */
}
```

### Imported Views
Reference and embed other map views:
- Reference: https://docs.kumu.io/guides/imported-views

### Partial Views
Display filtered subsets of your network:
- Reference: https://docs.kumu.io/guides/partial-views

---

## Complete Advanced Editor Reference

### Available Property Prefixes

Use these prefixes in `@settings` to target specific item types:

- `*-property`: Apply to all items (elements, connections, loops)
- `element-property`: Apply to element nodes only
- `connection-property`: Apply to connection links only
- `loop-property`: Apply to self-referential connections only

### Essential Properties

| Property | Values | Purpose |
|----------|--------|---------|
| `theme` | `light`, `dark` | Map background theme |
| `quality` | `high`, `fast` | High quality (all decorations) vs fast rendering |
| `layout` | `off`, `force-directed` | Layout algorithm |
| `color` | hex `#RRGGBB` | Node/connection color |
| `size` | number 1-100 | Width/height of elements |
| `opacity` | number 0-1 | Transparency (0=invisible, 1=opaque) |
| `width` | number 1-20 | Connection line thickness |
| `border-color` | hex code | Element outline color |
| `border-width` | number | Element outline thickness |
| `font-size` | number 6-20 | Text size |
| `font-color` | hex code | Text color |
| `font-family` | name | Font (default: "Open Sans") |
| `shape` | `circle`, `square`, `diamond` | Element shape |
| `icon` | name | Icon type (person, building, etc.) |
| `flag` | text | Label on element |
| `arrow` | `on`, `off` | Direction arrows on connections |

**Full reference:** https://docs.kumu.io/overview/advanced-editor-hub/property-reference

---

## Recommended Configuration for BioSCape Network

### Phase 1: Basic Setup

```css
/* Set global defaults */
@settings {
  *-theme: light;
  *-quality: high;
  *-layout: force-directed;
  *-shape: circle;
  *-font-size: 11;
  *-font-family: "Open Sans", sans-serif;
}

/* Publication nodes - large, colored by ecosystem */
publication {
  size: 50;
  border-width: 2;
  border-color: #333333;
}

publication[ecosystem="Marine"] {
  color: #1f77b4;
}

publication[ecosystem="Freshwater"] {
  color: #2ca02c;
}

publication[ecosystem="Terrestrial"] {
  color: #d62728;
}

publication[ecosystem="Mixed"] {
  color: #ff7f0e;
}

/* Author nodes - small, gray, scaled by productivity */
author {
  color: #999999;
  border-color: #666666;
  size: 5;
}

author[publications_authored>=5] {
  size: 10;
}

author[publications_authored>=10] {
  size: 15;
}

author[publications_authored>=15] {
  size: 20;
}

/* Connection styling */
connection {
  color: #cccccc;
  width: 1;
  opacity: 0.6;
  font-size: 10;
}

connection["Authored By"] {
  arrow: on;
  color: #1a1a1a;
  opacity: 0.4;
}

connection["Collaborated With"] {
  arrow: off;
  color: #5c5c5c;
  width: 2;
  opacity: 0.4;
}
```

### Phase 2: Interactive Controls

```css
@controls {
  top {
    /* Filter by ecosystem */
    control type: filter
           target: publication
           by: ecosystem;
    
    /* Filter by research method */
    control type: filter
           target: publication
           by: method;
    
    /* Cluster publications by year */
    control type: cluster
           target: publication
           by: year;
  }
  
  bottom {
    /* Toggle author visibility */
    control type: filter
           target: author
           label: "Show Authors";
    
    /* Highlight prolific researchers */
    control type: showcase
           label: "Top Contributors"
           targets: author[publications_authored>=10];
  }
}
```

### Phase 3: Enhanced Visualization

```css
/* Icons */
publication[ecosystem="Marine"] {
  icon: water;
  icon-color: #1f77b4;
}

publication[ecosystem="Terrestrial"] {
  icon: tree;
  icon-color: #d62728;
}

author[publications_authored>=10] {
  icon: star;
  icon-color: gold;
  flag: "Top Author";
  flag-color: gold;
}

/* Recent publications */
publication[year>=2023] {
  flag: "Recent";
  flag-color: green;
  border-width: 3;
}

/* Label templates */
publication {
  label: {{label}}<br/><span style="font-size: 0.75em; opacity: 0.7;">{{year}}</span>;
}

author {
  label: {{label}}<br/><span style="font-size: 0.75em; opacity: 0.7;">{{publications_authored}} pubs</span>;
}

/* Popovers for detailed info */
publication {
  popover: <div style="padding: 10px; max-width: 300px;">
             <strong>{{label}}</strong><br/>
             <strong>Year:</strong> {{year}}<br/>
             <strong>Ecosystem:</strong> {{ecosystem}}<br/>
             <strong>Taxa:</strong> {{taxa}}<br/>
             <strong>Method:</strong> {{method}}<br/>
             <strong>Authors:</strong> {{author_count}}<br/>
             <strong>Marine:</strong> {{Ecosystem_Marine}}<br/>
             <strong>Freshwater:</strong> {{Ecosystem_Freshwater}}<br/>
             <strong>Terrestrial:</strong> {{Ecosystem_Terrestrial}}
           </div>;
}

author {
  popover: <div style="padding: 10px;">
             <strong>{{label}}</strong><br/>
             <strong>Publications:</strong> {{publications_authored}}<br/>
             <strong>Collaborations:</strong> <em>Hover over co-author connections</em>
           </div>;
}
```

---

## Performance Optimization Tips

### For Large Networks (1000+ elements)

```css
@settings {
  *-quality: fast;              /* Disable some decorations */
  *-font-size: 9;               /* Smaller labels */
  element-opacity: 0.8;         /* Slight transparency */
  connection-opacity: 0.3;      /* Less visible connections */
  connection-width: 0.5;        /* Thinner lines */
}
```

### For High-Performance Rendering

```css
@settings {
  element-repulsion: 2000;      /* Stronger point repulsion */
  element-min-distance: 80;     /* More spacing */
  connection-attraction: 0.2;   /* Weaker pull */
  element-damping: 0.5;         /* More damping = faster settle */
  element-physics: on;
}
```

---

## Selector Examples for BioSCape Data

### By Ecosystem
```css
publication[ecosystem="Marine"]        /* Marine research */
publication[ecosystem="Freshwater"]    /* Freshwater research */
publication[ecosystem="Terrestrial"]   /* Terrestrial research */
publication[ecosystem="Mixed"]         /* Multi-ecosystem */
```

### By Semantic Dimensions
```css
publication[taxa="Animalia"]           /* Animal research */
publication[taxa="Plantae"]            /* Plant research */
publication[method="Measurement"]      /* Measurement-based */
publication[method="Inferential"]      /* Inferential methods */
```

### By Author Productivity
```css
author[publications_authored>=1]       /* All authors */
author[publications_authored>=5]       /* Established authors */
author[publications_authored>=10]      /* Prolific authors */
author[publications_authored<5]        /* Emerging authors */
```

### By Time
```css
publication[year=2023]                 /* Specific year */
publication[year>=2020]                /* Recent papers */
publication[year<2020]                 /* Earlier papers */
```

### By Connection Type
```css
connection["Authored By"]              /* Author-publication links */
connection["Collaborated With"]        /* Co-authorship links */
```

---

## Documentation Links

- **Official Advanced Editor Hub:** https://docs.kumu.io/overview/advanced-editor-hub
- **Settings Reference:** https://docs.kumu.io/overview/advanced-editor-hub/settings-reference
- **Property Reference:** https://docs.kumu.io/overview/advanced-editor-hub/property-reference
- **Selector Reference:** https://docs.kumu.io/overview/advanced-editor-hub/selector-reference
- **Color Reference:** https://docs.kumu.io/overview/advanced-editor-hub/color-reference
- **Controls Reference:** https://docs.kumu.io/overview/advanced-editor-hub/controls-reference
- **Force-Directed Layout:** https://docs.kumu.io/guides/layouts/force-directed
- **Data-Driven Decorations:** https://docs.kumu.io/guides/decorate/data-driven-decorations
- **Intro to Advanced Editor (Video):** https://www.youtube.com/watch?v=iPgLHTsQZ_w

---

## Quick Reference Checklist

After importing your semantic network JSON:

- [ ] Open the Advanced Editor
- [ ] Apply the `@settings` block with theme and layout settings
- [ ] Add publication ecosystem color rules
- [ ] Add author size scaling by publication count
- [ ] Configure publication and author connection styles
- [ ] Add data-driven decorations (icons, flags, labels)
- [ ] Create popovers for hover information
- [ ] Set up controls for filtering and clustering
- [ ] Test force-directed layout parameters
- [ ] Optimize rendering quality for network size
- [ ] Share interactive map with collaborators

---

**Last Updated:** February 16, 2026
**For:** BioSCape Publication Network
**Status:** Ready to Use

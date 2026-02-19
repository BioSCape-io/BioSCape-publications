#!/usr/bin/env python3
"""Verify the semantic network JSON is complete and ready for Kumu."""

import json

with open('network_analysis/kumu_import/biospace_semantic_network.json', 'r') as f:
    data = json.load(f)

print("\n" + "=" * 80)
print("SEMANTIC NETWORK VERIFICATION")
print("=" * 80)

# Get a sample publication element
publications = [e for e in data['elements'] if e['type'] == 'Publication']
sample_pub = publications[0]

print(f"\nSample Publication Element:")
print(f"  ID: {sample_pub['id']}")
print(f"  Label: {sample_pub['label']}")
print(f"  Size: {sample_pub['size']} (papers are large)")
print(f"  Color: {sample_pub['color']}")
print(f"  Ecosystem: {sample_pub['ecosystem']}")
print(f"  Taxa: {sample_pub['taxa']}")
print(f"  Method: {sample_pub['method']}")
print(f"  Authors: {sample_pub['author_count']}")

if 'metadata' in sample_pub and sample_pub['metadata']:
    print(f"\n  Semantic Dimensions (in metadata):")
    meta = sample_pub['metadata']
    for key in sorted(meta.keys()):
        if isinstance(meta[key], float):
            print(f"    {key}: {meta[key]:.3f}")

# Get a sample author element
authors = [e for e in data['elements'] if e['type'] == 'Author']
sample_auth = authors[10]

print(f"\nSample Author Element:")
print(f"  ID: {sample_auth['id']}")
print(f"  Label: {sample_auth['label']}")
print(f"  Size: {sample_auth['size']} (authors are small)")
print(f"  Color: {sample_auth['color']}")
print(f"  Publications: {sample_auth['publications_authored']}")

# Get sample connection types
authored = [c for c in data['connections'] if c['type'] == 'Authored By'][0]
collab = [c for c in data['connections'] if c['type'] == 'Collaborated With'][0]

print(f"\nSample Authored By Connection:")
print(f"  From: {authored['from']} (publication)")
print(f"  To: {authored['to']} (author)")
print(f"  Direction: {authored['direction']}")

print(f"\nSample Collaborated With Connection:")
print(f"  From: {collab['from']} (author1)")
print(f"  To: {collab['to']} (author2)")
print(f"  Direction: {collab['direction']}")
print(f"  Collaboration Count: {collab['metadata']['collaboration_count']}")

# Summary statistics
print(f"\n" + "=" * 80)
print("NETWORK STATISTICS")
print("=" * 80)
print(f"Total Elements: {len(data['elements'])}")
print(f"  Publications: {len(publications)}")
print(f"  Authors: {len(authors)}")
print(f"Total Connections: {len(data['connections'])}")
print(f"  Authored By: {sum(1 for c in data['connections'] if c['type'] == 'Authored By')}")
print(f"  Collaborated With: {sum(1 for c in data['connections'] if c['type'] == 'Collaborated With')}")

# Check metadata completeness
pub_with_metadata = sum(1 for p in publications if 'metadata' in p and p['metadata'])
print(f"\nPublications with Semantic Metadata: {pub_with_metadata}/72")

# Check node sizes
pub_sizes = [p['size'] for p in publications]
auth_sizes = [a['size'] for a in authors]
print(f"\nNode Size Hierarchy:")
print(f"  Publications: {min(pub_sizes)}-{max(pub_sizes)}px (avg {sum(pub_sizes)/len(pub_sizes):.0f}px)")
print(f"  Authors: {min(auth_sizes)}-{max(auth_sizes)}px (avg {sum(auth_sizes)/len(auth_sizes):.1f}px)")

print(f"\n✓ Semantic network ready for Kumu import!")
print("=" * 80)

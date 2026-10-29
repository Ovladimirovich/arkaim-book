import json

with open(
    "core/CORE/narrative_engine/data/WORLD_MODEL.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

# Find CANON epochs with empty provenance
canon_epochs = [
    e
    for e in data["epochs"]
    if e.get("source_level") == "CANON" and not e.get("provenance")
]
print("CANON epochs with empty provenance:")
for e in canon_epochs:
    print(f"  {e['id']} (order={e['order']})")

# Find CANON locations with empty provenance
canon_locs = [
    l
    for l in data["locations"]
    if l.get("source_level") == "CANON" and not l.get("provenance")
]
print("\nCANON locations with empty provenance:")
for l in canon_locs:
    print(f"  {l['id']}")

print(f"\nTotal: {len(canon_epochs)} epochs, {len(canon_locs)} locations")

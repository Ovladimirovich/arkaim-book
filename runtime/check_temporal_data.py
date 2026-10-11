"""Check actual temporal data for forensic audit."""
import json

wm = json.load(open('../core/CORE/narrative_engine/WORLD_MODEL.json', encoding='utf-8'))
epochs = wm.get('epochs', [])
events = wm.get('canonical_events', [])
characters = wm.get('characters_alive', [])
locations = wm.get('locations', [])

print('=== WORLD_MODEL.json ===')
print(f'Epochs: {len(epochs)}')
for e in epochs:
    print(f'  {e["id"]}: {e["name_ru"]} (order={e.get("order", "?")})')

print(f'\nCanonical events: {len(events)}')
for ev in events:
    print(f'  {ev["id"]}: {ev["title_ru"][:60]} epoch={ev.get("epoch", "?")} chars={ev.get("characters_involved", [])}')

print(f'\nCharacters: {len(characters)}')
for c in characters:
    print(f'  {c.get("character_name", "?")}: epoch={c.get("epoch", "?")} status={c.get("status", "?")}')

print(f'\nLocations: {len(locations)}')
for loc in locations:
    print(f'  {loc["id"]}: {loc["name_ru"]} type={loc.get("type", "?")} epochs={loc.get("epochs_present", [])}')

# Check knowledge graph entities
print('\n=== KNOWLEDGE GRAPH ===')
try:
    kg = json.load(open('../core/CORE/knowledge_graph/KNOWLEDGE_GRAPH.json', encoding='utf-8'))
    entities = kg.get('entities', [])
    relations = kg.get('relations', [])
    facts = kg.get('facts', [])
    print(f'Entities: {len(entities)}, Relations: {len(relations)}, Facts: {len(facts)}')
    # Entity types
    types = {}
    for e in entities:
        t = e.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1
    print('Entity types:', types)
except Exception as ex:
    print(f'Error: {ex}')

# Check world model entities
print('\n=== WORLD MODEL ENTITIES ===')
try:
    wme = json.load(open('../core/CORE/narrative_engine/WORLD_MODEL/civilization_profiles.json', encoding='utf-8'))
    print(f'Civilizations: {len(wme)}')
    for c in wme:
        print(f'  {c.get("id", "?")}: {c.get("name_ru", "?")} epochs={c.get("epochs", [])}')
except Exception as ex:
    print(f'Error: {ex}')

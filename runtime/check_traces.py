"""Check actual book content for traces."""
import json

# Check genome for characters and themes
genome = json.load(open('../core/GENOME/GENOME_v1.0.0.json', encoding='utf-8'))
characters = genome.get('modules', {}).get('characters', [])
themes = genome.get('modules', {}).get('themes', [])

print(f'=== GENOME CHARACTERS ({len(characters)}) ===')
for c in characters:
    cid = c.get('id', '?')
    name = c.get('name', '?')
    aliases = c.get('aliases', [])
    ctype = c.get('type', '?')
    archetype = c.get('archetype', '?')
    desc = c.get('description', '')[:60]
    print(f'  {cid}: {name} ({", ".join(aliases)}) type={ctype} archetype={archetype}')
    if desc:
        print(f'    desc: {desc}')

print(f'\n=== KEY THEMES (transmission/legacy/carriers) ===')
for t in themes:
    tid = t.get('id', '?')
    name = t.get('name', t.get('name_ru', '?'))
    strength = t.get('strength', 0)
    desc = t.get('description', t.get('description_ru', ''))[:80]
    # Filter for relevant themes
    keywords = ['наслед', 'учени', 'учител', 'носител', 'перед', 'поколен', 'преемствен', 
                'мудрост', 'знан', 'миссия', 'эпох', 'цикл', 'зеркал', 'пробужд', 'кали']
    if any(kw in (name + desc).lower() for kw in keywords):
        print(f'  {tid}: "{name}" strength={strength}')
        print(f'    {desc}')

# Check WORLD_MODEL characters
print(f'\n=== WORLD MODEL CHARACTER PRESENCE ===')
wm = json.load(open('../core/CORE/narrative_engine/data/WORLD_MODEL.json', encoding='utf-8'))
chars = wm.get('characters_alive', [])
print(f'Count: {len(chars)}')
for c in chars:
    print(f'  {c}')

# Check knowledge graph
print(f'\n=== KNOWLEDGE GRAPH ENTITIES ===')
try:
    kg = json.load(open('../core/CORE/knowledge_graph/data/KNOWLEDGE_GRAPH.json', encoding='utf-8'))
    entities = kg.get('entities', [])
    relations = kg.get('relations', [])
    print(f'Entities: {len(entities)}, Relations: {len(relations)}')
    types = {}
    for e in entities:
        t = e.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1
    print(f'Entity types: {types}')
    # Show sample character entities
    chars_kg = [e for e in entities if e.get('type') == 'character']
    print(f'Character entities: {len(chars_kg)}')
    for c in chars_kg[:10]:
        print(f'  {c.get("id", "?")}: {c.get("name", "?")} - {c.get("description", "")[:60]}')
except Exception as ex:
    print(f'Error: {ex}')

# Check RelationGraph data
print(f'\n=== RELATION GRAPH ===')
try:
    rg = json.load(open('../core/CORE/narrative_engine/data/WORLD_MODEL/relations.json', encoding='utf-8'))
    print(f'Relations file: {len(rg)} entries')
    if isinstance(rg, list) and len(rg) > 0:
        for r in rg[:5]:
            print(f'  {r}')
except Exception as ex:
    print(f'Error: {ex}')

# Check if there are separate character files
import os
wm_dir = '../core/CORE/narrative_engine/data/WORLD_MODEL'
if os.path.exists(wm_dir):
    files = os.listdir(wm_dir)
    print(f'\n=== WORLD_MODEL directory files ({len(files)}) ===')
    for f in sorted(files):
        print(f'  {f}')

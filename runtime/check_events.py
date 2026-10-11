"""Read all 17 canonical events and check their data."""
import json

wm = json.load(open('../core/CORE/narrative_engine/data/WORLD_MODEL.json', encoding='utf-8'))
events = wm.get('canonical_events', [])
epochs = wm.get('epochs', [])
characters = wm.get('characters_alive', [])

epoch_ids = [e['id'] for e in epochs]
epoch_names = {e['id']: e['name_ru'] for e in epochs}

print(f'=== {len(events)} CANONICAL EVENTS ===')
print(f'Epochs available: {epoch_ids}')
print()

for ev in events:
    ev_id = ev.get('id', '?')
    title = ev.get('title_ru', ev.get('title', '?'))
    desc = ev.get('description', '')
    epoch = ev.get('epoch', '?')
    loc = ev.get('location_id', None)
    chars = ev.get('characters_involved', [])
    chapter = ev.get('chapter', None)
    order = ev.get('order_in_epoch', 0)
    source = ev.get('source_level', '?')
    prov = ev.get('provenance', [])
    
    print(f'{ev_id}: "{title}"')
    print(f'  epoch={epoch}, location={loc}, chapter={chapter}, order={order}')
    print(f'  characters={chars}')
    print(f'  source_level={source}, provenance={len(prov)} tags')
    if desc:
        print(f'  description: {desc[:100]}')
    print()

print('=== CHARACTERS ===')
for c in characters:
    name = c.get('character_name', '?')
    epoch = c.get('epoch', '?')
    loc = c.get('location_id', None)
    status = c.get('status', '?')
    print(f'  {name}: epoch={epoch}, location={loc}, status={status}')

print(f'\n=== EPOCHS ===')
for e in epochs:
    eid = e['id']
    name = e['name_ru']
    order = e.get('order', '?')
    start = e.get('start_event', '?')
    end = e.get('end_event', '?')
    print(f'  {eid}: "{name}" order={order} start={start} end={end}')

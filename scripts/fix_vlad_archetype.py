"""Исправить archetype Влада в Genome JSON."""
import json
from pathlib import Path

path = Path(r"C:\ПРОЕКТ Наследие Аркаима\core\GENOME\GENOME_v1.0.0.json")

with open(path, encoding="utf-8") as f:
    g = json.load(f)

chars = g["modules"]["characters"]
fixed = 0
for c in chars:
    if c.get("name") == "Влад" and c.get("archetype") == "Хранитель":
        print(f"Before: {c['name']} - archetype: {c['archetype']}")
        c["archetype"] = "Житель Гипербореи"
        print(f"After:  {c['name']} - archetype: {c['archetype']}")
        fixed += 1

with open(path, "w", encoding="utf-8") as f:
    json.dump(g, f, ensure_ascii=False, indent=2)

print(f"Исправлено: {fixed}")

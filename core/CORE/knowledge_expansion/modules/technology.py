"""
Technology Module — технологии гипербореев.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "technology",
    "description": "Технологии: звукознание, энергетика, строительство",
    "source_files": [
        Path("core/KNOWLEDGE/ARCHAEOLOGY.json"),
        Path("core/KNOWLEDGE/THEMES_DEEP.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/TECHNOLOGY.json"),
}

PROMPT = """Проанализируй технологии, описанные в книге «Наследие Аркаима».

Данные: {data}

Определи:
1. Технологии гипербореев (звузнание, энергетика)
2. Инженерные знания (строительство, астрономия)
3. Современные параллели
4. Влияние на цивилизацию

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

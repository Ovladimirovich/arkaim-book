"""
Cosmology Module — космологические знания книги.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "cosmology",
    "description": "Космологические знания: циклы, эпохи, космические законы",
    "source_files": [
        Path("core/KNOWLEDGE/THEMES_DEEP.json"),
        Path("core/KNOWLEDGE/ESOTERIC_CONNECTIONS.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/COSMOLOGY.json"),
}

PROMPT = """Проанализируй космологические знания из книги «Наследие Аркаима».

Темы для анализа: {topics}

Определи:
1. Циклическую модель времени (юги, эпохи)
2. Космические законы, описанные в книге
3. Связь человека с космосом
4. Параллели с другими космологическими системами

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

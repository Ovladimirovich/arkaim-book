"""
Psychology Module — психология персонажей.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "psychology",
    "description": "Психология: мотивации, архетипы, трансформации персонажей",
    "source_files": [
        Path("core/KNOWLEDGE/THEMES_DEEP.json"),
        Path("core/KNOWLEDGE/SYMBOLS_EXPANDED.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/PSYCHOLOGY.json"),
}

PROMPT = """Проанализируй психологические аспекты персонажей книги «Наследие Аркаима».

Темы: {topics}

Определи:
1. Психологические портреты ключевых персонажей
2. Архетипические модели поведения
3. Психологические трансформации (от неведения к знанию)
4. Мотивации и конфликты

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

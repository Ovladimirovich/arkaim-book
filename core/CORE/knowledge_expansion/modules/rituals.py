"""
Rituals Module — ритуалы и практики книги.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "rituals",
    "description": "Ритуалы и практики, описанные в книге",
    "source_files": [
        Path("core/KNOWLEDGE/ESOTERIC_CONNECTIONS.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/RITUALS.json"),
}

PROMPT = """Проанализируй ритуалы и практики из книги «Наследие Аркаима».

Данные: {data}

Определи:
1. Описанные практики и ритуалы
2. Связи с изотерическими традициями
3. Символическое значение
4. Практическое применение

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

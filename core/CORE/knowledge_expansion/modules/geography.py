"""
Geography Module — география и энергетика мест.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "geography",
    "description": "География: маршруты, ландшафты, энергетика мест",
    "source_files": [
        Path("core/KNOWLEDGE/MAP_DATA.json"),
        Path("core/KNOWLEDGE/ARCHAEOLOGY.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/GEOGRAPHY.json"),
}

PROMPT = """Проанализируй географические знания из книги «Наследие Аркаима».

Данные: {data}

Определи:
1. Ключевые локации и их значение
2. Маршруты миграций
3. Энергетические свойства мест
4. Современные подтверждения (археология)

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

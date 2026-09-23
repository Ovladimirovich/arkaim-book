"""
Language Module — язык и терминология книги.
"""
from pathlib import Path

MODULE_CONFIG = {
    "name": "language",
    "description": "Язык: термины, формулировки, стилистика",
    "source_files": [
        Path("core/KNOWLEDGE/PHILOSOPHY.json"),
        Path("core/KNOWLEDGE/CROSS_REFERENCES.json"),
    ],
    "output_file": Path("core/KNOWLEDGE/LANGUAGE.json"),
}

PROMPT = """Проанализируй язык и терминологию книги «Наследие Аркаима».

Данные: {data}

Определи:
1. Ключевые термины и их определения
2. Стилистические особенности
3. Связи терминов с другими культурами
4. Языковые паттерны

Верни JSON со списком объектов, каждый с полями:
- topic: тема
- layers: {literal, metaphorical, cosmic}
- cross_references: список связей
- patterns: список паттернов"""

def get_config():
    return MODULE_CONFIG

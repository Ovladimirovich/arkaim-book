"""
TextCleaner — пайплайн очистки текста книги от артефактов OCR/PDF-конвертации.
Исправляет:
1. Дефисные переносы на конце строк (слово- \nпродолжение -> словопродолжение)
2. Разрывы слов пробелом внутри (слово- продолжение -> словопродолжение)
3. Сдвоенную пунктуацию
4. Лишние пробелы
"""

import re
from pathlib import Path
from typing import Optional


class TextCleaner:
    def __init__(self):
        # Частицы, которые могут быть отделены дефисом в русском языке
        # Их НЕ нужно склеивать
        self._russian_particles = {
            "то", "либо", "нибудь", "таки", "ка",
            "де", "тка", "тко", "с", "ста",
        }

    def _is_particle(self, word: str) -> bool:
        return word.lower() in self._russian_particles

    def _is_compound_prefix(self, word: str) -> bool:
        """
        Составные прилагательные в русском оканчиваются на -о-, -е-:
        морально-, причинно-, культурно-, древне-.
        Если слово длиннее 4 букв и оканчивается на о/е — это compound prefix.
        """
        return len(word) >= 5 and word[-1] in ("о", "е")

    def fix_hyphenation(self, text: str) -> str:
        """
        Исправляет дефисные переносы.

        Правило:
          слово-<пробел>продолжение
          - Если первая часть — compound prefix (-о, -е) и вторая >= 4 букв:
            сохраняем дефис: «морально- нравственных» -> «морально-нравственных»
          - Если вторая часть — частица (то, либо): не трогаем
          - Иначе: убираем дефис и пробел (перенос со строки)
        """
        def _fix(m: re.Match) -> str:
            before = m.group(1)
            after = m.group(2)
            if self._is_particle(after):
                return before + "-" + after
            if self._is_compound_prefix(before) and len(after) >= 4:
                return before + "-" + after
            return before + after

        text = re.sub(
            r'([а-яё]+)\-\s+([а-яё]+)',
            _fix,
            text,
            flags=re.IGNORECASE,
        )

        # Перенос на конце строки (без пробела после дефиса)
        text = re.sub(
            r'([а-яё]+)\-\n+([а-яё]+)',
            lambda m: m.group(1) + m.group(2),
            text,
            flags=re.IGNORECASE,
        )

        return text

    def fix_punctuation(self, text: str) -> str:
        """Нормализует пунктуацию."""
        # Сдвоенные знаки (кроме троеточия)
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r',{2,}', ',', text)
        text = re.sub(r';{2,}', ';', text)
        text = re.sub(r':{2,}', ':', text)
        text = re.sub(r'!{3,}', '!!', text)
        text = re.sub(r'\?{3,}', '??', text)
        return text

    def fix_spaces(self, text: str) -> str:
        """Убирает лишние пробелы."""
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
        return text.strip()

    def clean(self, text: str) -> str:
        """Полный пайплайн очистки."""
        text = self.fix_hyphenation(text)
        text = self.fix_punctuation(text)
        text = self.fix_spaces(text)
        return text

    def clean_file(self, src_path: Path, dst_path: Optional[Path] = None) -> Path:
        """
        Очищает файл и сохраняет результат.
        Если dst_path не указан, перезаписывает исходный.
        """
        text = src_path.read_text(encoding="utf-8")
        cleaned = self.clean(text)
        dst = dst_path or src_path
        dst.write_text(cleaned, encoding="utf-8")
        return dst

    def get_stats(self, before: str, after: str) -> dict:
        """Сравнивает текст до и после очистки."""
        def count_hyphen_artifacts(t: str) -> int:
            return len(re.findall(r'(?<=[а-яё])\-\s+(?=[а-яё])', t, re.IGNORECASE))

        return {
            "chars_before": len(before),
            "chars_after": len(after),
            "hyphen_artifacts_before": count_hyphen_artifacts(before),
            "hyphen_artifacts_after": count_hyphen_artifacts(after),
            "double_spaces_removed": len(before) - len(after),
        }

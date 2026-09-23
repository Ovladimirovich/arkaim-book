"""DocumentValidator — проверка документов перед ингестом."""

from pathlib import Path
from typing import List, Tuple

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".pdf"}


class ValidationError(Exception):
    """Ошибка валидации документа."""


class DocumentValidator:
    """Проверяет файл перед добавлением в OS."""

    @staticmethod
    def validate(file_path: Path) -> Tuple[bool, List[str]]:
        """Проверить файл. Возвращает (ok, [ошибки])."""
        errors = []

        if not file_path.exists():
            errors.append(f"Файл не существует: {file_path}")
            return False, errors

        if not file_path.is_file():
            errors.append(f"Не является файлом: {file_path}")
            return False, errors

        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(
                f"Неподдерживаемое расширение: {ext}. "
                f"Допустимы: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
            return False, errors

        size = file_path.stat().st_size
        if size == 0:
            errors.append(f"Файл пуст: {file_path}")
            return False, errors

        if size > MAX_FILE_SIZE:
            errors.append(
                f"Файл слишком большой: {size} байт "
                f"(максимум {MAX_FILE_SIZE} байт)"
            )
            return False, errors

        # Binary formats (PDF) are handled by the pipeline extractor
        if ext not in {".pdf"}:
            try:
                text = file_path.read_text(encoding="utf-8")
                if not text.strip():
                    errors.append(f"Файл не содержит текста: {file_path}")
                    return False, errors
            except UnicodeDecodeError:
                errors.append(f"Файл не в UTF-8: {file_path}")
                return False, errors

        return True, errors


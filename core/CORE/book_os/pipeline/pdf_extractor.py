"""
pdf_extractor — извлечение текста из PDF для BOOK OS ingestion pipeline.

Использует pdfplumber (точное извлечение с сохранением структуры),
с fallback на PyPDF2, если pdfplumber недоступен.

Функция extract_text(pdf_path) -> str возвращает текст с разделением
по страницам и абзацам для корректного chunking'а.
"""
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.pdf_extractor")


def extract_text(pdf_path: Path, fallback: bool = True) -> str:
    """
    Извлечь текст из PDF-файла.

    Args:
        pdf_path: путь к PDF-файлу
        fallback: использовать PyPDF2, если pdfplumber недоступен

    Returns:
        str: извлечённый текст (UTF-8), разделённый по страницам
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    # Попытка 1: pdfplumber
    try:
        import pdfplumber
        return _extract_with_pdfplumber(path)
    except ImportError:
        log.warning("pdfplumber_not_installed falling_back")
    except Exception as e:
        log.warning("pdfplumber_failed error=%s", e)

    # Попытка 2: PyPDF2
    if fallback:
        try:
            import PyPDF2
            return _extract_with_pypdf2(path)
        except ImportError:
            log.error("pypdf2_not_installed")
        except Exception as e:
            log.error("pypdf2_failed error=%s", e)

    raise RuntimeError(
        "Не удалось извлечь текст из PDF. Установите pdfplumber или PyPDF2."
    )


def _extract_with_pdfplumber(path: Path) -> str:
    """Точное извлечение с сохранением структуры страниц."""
    import pdfplumber

    pages_text = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_text.append(f"[СТРАНИЦА {i}]\n{text}")

    result = "\n\n".join(pages_text)
    log.info("pdfplumber_extracted pages=%d chars=%d", len(pages_text), len(result))
    return result


def _extract_with_pypdf2(path: Path) -> str:
    """Fallback-извлечение через PyPDF2."""
    import PyPDF2

    reader = PyPDF2.PdfReader(str(path))
    pages_text = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages_text.append(f"[СТРАНИЦА {i}]\n{text}")

    result = "\n\n".join(pages_text)
    log.info("pypdf2_extracted pages=%d chars=%d", len(pages_text), len(result))
    return result


def extract_to_temp_txt(pdf_path: Path, output_dir: Optional[Path] = None) -> Path:
    """
    Извлечь текст из PDF и сохранить как .txt во временный файл.

    Returns:
        Path: путь к созданному .txt файлу
    """
    from tempfile import NamedTemporaryFile

    text = extract_text(pdf_path)
    suffix = f"_{Path(pdf_path).stem}.txt"
    with NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        return Path(f.name)


__all__ = ["extract_text", "extract_to_temp_txt"]
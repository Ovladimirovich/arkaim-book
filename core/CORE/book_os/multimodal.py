"""Multi-modal обработка: PDF, изображения, аудио.

Поддерживает:
- PDF: извлечение текста через pypdf
- Изображения: OCR через pytesseract (если установлен)
- Аудио: STT через speech_recognition (если установлен)

Все результаты возвращаются как Chunk с metadata["format"] = тип файла.
"""

from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from schemas.chunk import Chunk

# ── PDF ──────────────────────────────────────────────

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


def extract_text_from_pdf(path: Path) -> Optional[str]:
    """Извлечь текст из PDF через pypdf."""
    if not HAS_PYPDF:
        return None
    try:
        reader = pypdf.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages) if pages else None
    except Exception:
        return None


# ── Image OCR ────────────────────────────────────────

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def extract_text_from_image(path: Path) -> Optional[str]:
    """OCR изображения через pytesseract."""
    if not HAS_PIL:
        return None
    if not HAS_TESSERACT:
        return None
    try:
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        return text.strip() or None
    except Exception:
        return None


# ── Audio ────────────────────────────────────────────

try:
    import speech_recognition as sr
    HAS_SPEECH = True
except ImportError:
    HAS_SPEECH = False


def extract_text_from_audio(path: Path) -> Optional[str]:
    """STT аудио через speech_recognition."""
    if not HAS_SPEECH:
        return None
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(path)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="ru-RU")
    except Exception:
        return None


# ── Supported types ──────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".bmp": "image", ".tiff": "image",
    ".wav": "audio", ".mp3": "audio", ".flac": "audio", ".ogg": "audio",
}

EXTRACTORS = {
    "pdf": extract_text_from_pdf,
    "image": extract_text_from_image,
    "audio": extract_text_from_audio,
}

FILE_TYPE_NAMES = {
    "pdf": "PDF document",
    "image": "Image",
    "audio": "Audio",
}


def detect_file_type(path: Path) -> Optional[str]:
    """Определить тип файла по расширению."""
    ext = path.suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def process_multimodal(path: Path, doc_id: Optional[str] = None,
                       chunk_size: int = 2000) -> List[Chunk]:
    """Обработать файл: извлечь текст, вернуть список Chunk.

    Args:
        path: путь к файлу
        doc_id: ID документа (авто UUID если None)
        chunk_size: макс. длина текста в одном чанке

    Returns:
        Список Chunk с текстом и metadata["format"]
    """
    file_type = detect_file_type(path)
    if file_type is None:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    extractor = EXTRACTORS.get(file_type)
    if extractor is None:
        raise ValueError(f"No extractor for type: {file_type}")

    text = extractor(path)
    if not text:
        return []

    if doc_id is None:
        doc_id = str(uuid4())

    file_type_name = FILE_TYPE_NAMES.get(file_type, file_type)
    source_name = path.name

    # Разбиваем на чанки
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk_text = text[i:i + chunk_size]
        chunks.append(Chunk(
            id=f"{file_type}_{path.stem}_{i // chunk_size}",
            doc_id=doc_id,
            text=chunk_text,
            position=i // chunk_size,
            metadata={
                "format": file_type,
                "source_file": source_name,
                "format_name": file_type_name,
                "char_start": i,
                "char_end": i + len(chunk_text),
            },
        ))

    return chunks


def get_available_extractors() -> dict:
    """Вернуть словарь доступных экстракторов."""
    return {
        "pdf": HAS_PYPDF,
        "image_ocr": HAS_TESSERACT and HAS_PIL,
        "audio_stt": HAS_SPEECH,
    }

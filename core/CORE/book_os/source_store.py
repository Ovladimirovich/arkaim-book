"""Source Store — неизменяемое хранилище первичных документов."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from schemas.document import Document
from book_os.exceptions import DocumentNotFoundError, IngestionValidationError

OS_DATA_DIR = Path(__file__).resolve().parents[2] / "OS_DATA"


class SourceStore:
    """Хранилище документов на файловой системе.

    Каждый документ сохраняется как JSON-файл:
      OS_DATA/documents/{doc_id}.json

    Документы иммутабельны — после добавления не редактируются.
    Новая версия документа = новый Document.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or OS_DATA_DIR
        self._docs_dir = self.data_dir / "documents"
        self._docs_dir.mkdir(parents=True, exist_ok=True)

    def add(self, file_path: Path, doc_type: str,
            version: str = "1.0.0") -> Document:
        """Добавить документ в Source Store.

        Читает файл, вычисляет SHA256, создаёт Document,
        сохраняет метаданные. Документ не копируется —
        хранится только ссылка (path) + хеш.
        """
        if not file_path.exists():
            raise IngestionValidationError(f"Файл не найден: {file_path}")

        content = file_path.read_bytes()
        hash_value = hashlib.sha256(content).hexdigest()

        existing = self._find_by_hash(hash_value)
        if existing:
            return existing

        doc = Document(
            title=file_path.name,
            type=doc_type,
            version=version,
            imported_at=datetime.now(timezone.utc),
            hash=hash_value,
            path=str(file_path.resolve()),
        )
        self._save(doc)
        return doc

    def get(self, doc_id: str) -> Document:
        """Вернуть документ по ID."""
        path = self._doc_path(doc_id)
        if not path.exists():
            raise DocumentNotFoundError(f"Document not found: {doc_id}")
        return self._load(path)

    def get_by_title(self, title: str) -> Optional[Document]:
        """Вернуть документ по названию (первое совпадение)."""
        for doc in self.list():
            if doc.title == title:
                return doc
        return None

    def list(self, doc_type: Optional[str] = None) -> List[Document]:
        """Список всех документов (с фильтром по типу)."""
        docs = []
        for path in sorted(self._docs_dir.glob("*.json")):
            try:
                doc = self._load(path)
                if doc_type is None or doc.type == doc_type:
                    docs.append(doc)
            except Exception:
                continue
        return docs

    def delete(self, doc_id: str) -> None:
        """Удалить документ из хранилища."""
        path = self._doc_path(doc_id)
        if not path.exists():
            raise DocumentNotFoundError(f"Document not found: {doc_id}")
        path.unlink()

    def verify(self, doc_id: str) -> bool:
        """Проверить целостность документа по SHA256."""
        doc = self.get(doc_id)
        if not doc.path:
            return False
        src = Path(doc.path)
        if not src.exists():
            return False
        actual_hash = hashlib.sha256(src.read_bytes()).hexdigest()
        return actual_hash == doc.hash

    def get_stats(self) -> dict:
        """Статистика по хранилищу."""
        all_docs = self.list()
        return {
            "total": len(all_docs),
            "by_type": {
                doc_type: len([d for d in all_docs if d.type == doc_type])
                for doc_type in set(d.type for d in all_docs)
            },
            "data_dir": str(self._docs_dir),
        }

    def _doc_path(self, doc_id: str) -> Path:
        return self._docs_dir / f"{doc_id}.json"

    def _save(self, doc: Document) -> None:
        path = self._doc_path(doc.id)
        data = doc.model_dump(mode="json")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self, path: Path) -> Document:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Document(**data)

    def _find_by_hash(self, hash_value: str) -> Optional[Document]:
        for doc in self.list():
            if doc.hash == hash_value:
                return doc
        return None

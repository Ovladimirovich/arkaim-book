"""Q2: решения по кандидатам — атомарная запись + журнал.

Решение меняет только поля проверки в самой записи знания. Никакой отдельной
базы статусов нет: гейты 6d/6e читают статус из файла, поэтому одобренная
запись начинает проходить гейты сама, без правок потребителей.

Правила (решение владельца):
  * решают только роли ``author`` и ``admin``;
  * комментарий обязателен для любого решения;
  * ``REJECTED`` остаётся в исходном файле;
  * автоматического одобрения нет ни у LLM, ни у планировщика.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .candidates import (
    KNOWLEDGE_DIR,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    CandidateRecord,
    base_candidate_id,
    candidate_id_for,
    find_candidate,
    scan_candidates,
)

log = logging.getLogger("hermes.knowledge_expansion.review.service")

REVIEW_ROLES = frozenset({"author", "admin"})

#: Действие → целевой статус.
ACTIONS: dict[str, str] = {
    "approve": STATUS_APPROVED,
    "reject": STATUS_REJECTED,
    "reopen": STATUS_PENDING,
}

COMMENT_MIN = 3
COMMENT_MAX = 1000

STALE_LOCK_SECONDS = 60.0

_METADATA_KEYS = ("_provenance_metadata", "provenance_metadata")


class ReviewError(Exception):
    """Ошибка решения; ``status_code`` — для будущего API-слоя (Q3)."""

    status_code = 400
    code = "review_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class PermissionDenied(ReviewError):
    status_code = 403
    code = "role_forbidden"


class CandidateNotFound(ReviewError):
    status_code = 404
    code = "candidate_not_found"


class ValidationError(ReviewError):
    status_code = 400
    code = "validation_error"


class StaleCandidate(ReviewError):
    status_code = 409
    code = "stale_candidate"


class InvalidTransition(ReviewError):
    status_code = 409
    code = "invalid_transition"


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _journal_path(journal_path: Path | str | None) -> Path:
    if journal_path:
        return Path(journal_path)
    return (
        Path(__file__).resolve().parents[3]
        / "core"
        / "OS_DATA"
        / "review"
        / "decisions.jsonl"
    )


def _backup_dir(knowledge_file: Path, backup_dir: Path | str | None) -> Path:
    if backup_dir:
        return Path(backup_dir)
    # core/KNOWLEDGE/<file> → core/OS_DATA/review/backups
    return knowledge_file.resolve().parents[1] / "OS_DATA" / "review" / "backups"


@contextmanager
def _file_lock(target: Path, timeout: float = 5.0) -> Iterator[None]:
    """Эксклюзивная блокировка на файл знания (lock-файл рядом)."""
    lock_path = target.with_name(f".{target.name}.review.lock")
    deadline = time.monotonic() + timeout
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if _is_stale_lock(lock_path):
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise StaleCandidate(
                    "Файл занят другим решением, повторите позже",
                    code="lock_timeout",
                )
            time.sleep(0.05)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        lock_path.unlink(missing_ok=True)


def _is_stale_lock(lock_path: Path) -> bool:
    try:
        return time.time() - lock_path.stat().st_mtime > STALE_LOCK_SECONDS
    except FileNotFoundError:
        return False


def _read_document(path: Path) -> tuple[Any, bool, bool]:
    """Прочитать JSON: (документ, был_BOM, был_перевод_строки_в_конце)."""
    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    return json.loads(text), had_bom, text.endswith("\n")


def _write_document(
    path: Path, document: Any, *, had_bom: bool, trailing_newline: bool
) -> None:
    """Атомарная замена файла: временный файл в том же каталоге → replace."""
    text = json.dumps(document, ensure_ascii=False, indent=2)
    if trailing_newline:
        text += "\n"
    data = text.encode("utf-8")
    if had_bom:
        data = b"\xef\xbb\xbf" + data
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _backup(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{stamp}-{path.name}"
    shutil.copy2(path, target)
    return target


def _entry(
    document: Any, container: str | None, index: int
) -> Mapping[str, Any] | None:
    if container is None:
        if isinstance(document, list) and 0 <= index < len(document):
            entry = document[index]
            return entry if isinstance(entry, Mapping) else None
        return None
    if not isinstance(document, Mapping):
        return None
    entries = document.get(container)
    if not isinstance(entries, list) or not (0 <= index < len(entries)):
        return None
    entry = entries[index]
    return entry if isinstance(entry, Mapping) else None


def _metadata_blocks(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Все блоки провенанса, которые нужно обновить согласованно."""
    blocks: list[dict[str, Any]] = []
    for key in _METADATA_KEYS:
        block = entry.get(key)
        if isinstance(block, dict):
            blocks.append(block)
    nested = entry.get("metadata")
    if isinstance(nested, Mapping):
        for key in _METADATA_KEYS:
            block = nested.get(key)
            if isinstance(block, dict):
                blocks.append(block)
    if not blocks:
        fresh: dict[str, Any] = {}
        entry["_provenance_metadata"] = fresh  # type: ignore[index]
        blocks.append(fresh)
    return blocks


def _validate(actor: str, role: str, comment: str) -> tuple[str, str]:
    actor_name = " ".join(str(actor or "").split())
    role_name = str(role or "").strip().lower()
    if not actor_name or role_name not in REVIEW_ROLES:
        raise PermissionDenied(
            "Решение по кандидату может принять только автор или администратор"
        )
    text = " ".join(str(comment or "").split())
    if len(text) < COMMENT_MIN:
        raise ValidationError(
            f"Нужен комментарий с обоснованием (минимум {COMMENT_MIN} символа)",
            code="comment_required",
        )
    if len(text) > COMMENT_MAX:
        raise ValidationError(
            f"Комментарий слишком длинный (максимум {COMMENT_MAX} символов)",
            code="comment_too_long",
        )
    return actor_name, text


def _check_transition(action: str, current: str) -> None:
    """Разрешённые переходы статусов (см. проект очереди, раздел 5)."""
    target = ACTIONS[action]
    if current == target:
        return
    allowed = {
        "approve": {STATUS_PENDING},
        "reject": {STATUS_PENDING, STATUS_APPROVED},
        "reopen": {STATUS_REJECTED},
    }[action]
    if current not in allowed:
        raise InvalidTransition(
            f"Переход {current or 'БЕЗ_СТАТУСА'} → {target} для действия "
            f"'{action}' не разрешён",
            code="invalid_transition",
        )


def _apply_review(
    entry: Mapping[str, Any],
    *,
    status: str,
    actor: str,
    comment: str,
    previous: str,
    now: str,
) -> None:
    for block in _metadata_blocks(entry):
        block["status"] = status
        block["requires_author_review"] = status != STATUS_APPROVED
        block["reviewed_by"] = actor
        block["reviewed_at"] = now
        block["review_comment"] = comment
        block["previous_status"] = previous


def _append_journal(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(payload), ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def iter_decisions(
    candidate_id: str | None = None,
    *,
    journal_path: Path | str | None = None,
) -> Iterator[dict[str, Any]]:
    """Прочитать журнал решений (append-only)."""
    path = _journal_path(journal_path)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                log.warning("review_journal_broken_line path=%s", path)
                continue
            if candidate_id and entry.get("candidate_id") != candidate_id:
                continue
            yield entry


def decide(
    candidate_id: str,
    action: str,
    *,
    actor: str,
    role: str,
    comment: str,
    expected_status: str | None = None,
    knowledge_dir: Path | str | None = None,
    journal_path: Path | str | None = None,
    backup_dir: Path | str | None = None,
) -> CandidateRecord:
    """Принять решение по кандидату: ``approve``, ``reject`` или ``reopen``.

    Возвращает актуальную запись индекса. Идемпотентно: повторное решение,
    совпадающее с текущим статусом, ничего не пишет и не создаёт вторую
    строку журнала.
    """
    if action not in ACTIONS:
        raise ValidationError(
            f"Неизвестное действие '{action}'; допустимы: {sorted(ACTIONS)}",
            code="unknown_action",
        )
    actor_name, comment_text = _validate(actor, role, comment)

    records = scan_candidates(knowledge_dir)
    current = next((r for r in records if r.candidate_id == candidate_id), None)
    if current is None:
        raise CandidateNotFound("Кандидат не найден: запись изменена или удалена")

    if expected_status and current.status != str(expected_status).strip().upper():
        raise StaleCandidate(
            f"Статус уже изменился: ожидался {expected_status}, сейчас {current.status}",
            code="stale_status",
        )
    if action == "approve" and current.file_blocked:
        raise InvalidTransition(
            "Файл целиком помечен как непроверенный: одобрение отдельной записи "
            "не откроет его. Сначала нужно снять file-level пометку файла.",
            code="file_level_blocked",
        )

    target_status = ACTIONS[action]
    if current.status == target_status:
        log.info(
            "review_noop id=%s action=%s status=%s",
            candidate_id,
            action,
            current.status,
        )
        return current

    _check_transition(action, current.status)

    path = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
    knowledge_file = path / current.file
    if not knowledge_file.exists():
        raise CandidateNotFound("Файл знания не найден")

    with _file_lock(knowledge_file):
        document, had_bom, trailing_newline = _read_document(knowledge_file)
        entry = _entry(document, current.container, current.index)
        if entry is None:
            raise StaleCandidate("Запись исчезла из файла — обновите очередь")
        if base_candidate_id(candidate_id) != candidate_id_for(current.file, entry):
            raise StaleCandidate(
                "Содержимое записи изменилось — обновите очередь", code="stale_record"
            )

        now = _now()
        _apply_review(
            entry,
            status=target_status,
            actor=actor_name,
            comment=comment_text,
            previous=current.status,
            now=now,
        )
        backup = _backup(knowledge_file, _backup_dir(knowledge_file, backup_dir))
        _write_document(
            knowledge_file, document, had_bom=had_bom, trailing_newline=trailing_newline
        )

    try:
        _append_journal(
            _journal_path(journal_path),
            {
                "ts": now,
                "request_id": uuid.uuid4().hex,
                "candidate_id": candidate_id,
                "action": action,
                "actor": actor_name,
                "role": str(role).strip().lower(),
                "file": current.file,
                "locator": current.locator,
                "topic": current.topic,
                "from": current.status,
                "to": target_status,
                "comment": comment_text,
                "backup": str(backup),
            },
        )
    except Exception as exc:  # noqa: BLE001
        # Решение без записи в журнал недопустимо: откатываем файл к бэкапу,
        # чтобы состояние и аудит не расходились.
        log.critical("review_journal_failed id=%s error=%s", candidate_id, exc)
        try:
            shutil.copy2(backup, knowledge_file)
        except Exception as restore_exc:  # noqa: BLE001
            log.critical(
                "review_rollback_failed id=%s error=%s", candidate_id, restore_exc
            )
            raise ReviewError(
                "Журнал недоступен, и откат файла не удался — требуется ручная "
                "проверка файла и журнала",
                code="journal_failed_rollback_failed",
            ) from exc
        raise ReviewError(
            "Журнал решений недоступен — решение отменено",
            code="journal_failed",
        ) from exc
    log.info(
        "review_decision id=%s action=%s from=%s to=%s actor=%s",
        candidate_id,
        action,
        current.status,
        target_status,
        actor_name,
    )

    updated = find_candidate(candidate_id, knowledge_dir)
    if updated is None:
        raise StaleCandidate("Запись не найдена после решения", code="stale_record")
    return updated

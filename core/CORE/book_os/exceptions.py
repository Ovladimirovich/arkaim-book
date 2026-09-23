"""Типизированные исключения BOOK OS."""


class BookOSError(Exception):
    """Базовое исключение BOOK OS."""


class DocumentNotFoundError(BookOSError):
    """Документ не найден в Source Store."""


class EntityNotFoundError(BookOSError):
    """Сущность не найдена в Knowledge Graph."""


class IngestionValidationError(BookOSError):
    """Ошибка валидации при ингесте документа."""


class ProvenanceConflictError(BookOSError):
    """Конфликт provenance при добавлении факта."""


class OSInternalError(BookOSError):
    """Внутренняя ошибка OS."""

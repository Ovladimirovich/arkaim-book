"""Подготовленные задания на обновление кадров (managed frame update).

Это НЕ механизм генерации: задание — черновик производственного
пакета (промпт/негатив/правила/референсы/исполнитель), который при
«Mock Generate» уходит в СУЩЕСТВУЮЩИЙ контур image-jobs (arkaim-web
вызывает POST /studio/image-jobs, затем PATCH-ом этого роута обновляет
статус). Хранится отдельным слоем в studio.db — новый механизм
генерации не создаётся.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_PREPARED_CONFIG = ConfigDict(extra="forbid")

PREPARED_STATUS_PREPARED = "prepared"  # черновик готов, генерация не запускалась
PREPARED_STATUS_GENERATING = "generating"  # запущена генерация (image-jobs)
PREPARED_STATUS_DONE = "done"  # новый вариант получен (completed)
PREPARED_STATUS_APPROVED = "approved"  # новый кадр утверждён шотом
PREPARED_STATUS_CANCELLED = "cancelled"  # задание отменено режиссёром

PREPARED_STATUSES = (
    PREPARED_STATUS_PREPARED,
    PREPARED_STATUS_GENERATING,
    PREPARED_STATUS_DONE,
    PREPARED_STATUS_APPROVED,
    PREPARED_STATUS_CANCELLED,
)

#: Справочник исполнителей изображений для UI выбора (п.3 OWNER-GO).
#: Это НЕ новые бэкенды — соответствие существующим preferred_backend
#: в POST /studio/image-jobs (agnes/mock/auto через arkaim-media).
IMAGE_EXECUTORS: dict[str, dict] = {
    "mock": {
        "label": "mock — тестовый ответ",
        "execution": "local",
        "execution_label": "локальный (тестовые ответы)",
        "available": True,
        "why": "без трат, проверка цикла подготовки и сравнения",
        "requirements": "нет",
        "workflow": "mock",
    },
    "agnes": {
        "label": "agnes — ComfyUI-Agnes (бесплатный)",
        "execution": "cloud",
        "execution_label": "облачный (arkaim-media → Agnes)",
        "available": True,
        "why": "реальная генерация без платных кредитов",
        "requirements": "доступность Agnes на стороне arkaim-media; при недоступности задание упадёт видимо (failed, error)",
        "workflow": "agnes-image",
    },
    "auto": {
        "label": "auto — автоматический выбор исполнителя",
        "execution": "mixed",
        "execution_label": "смешанный (выбор arkaim-media)",
        "available": True,
        "why": "делегирует выбор исполнителя существующему MediaClient",
        "requirements": "задача упадёт видимо, если ни один исполнитель недоступен",
        "workflow": "auto",
    },
}


class PreparedUpdate(BaseModel):
    """Подготовленное обновление кадра одного плана (шота)."""

    prepared_id: str = Field(..., max_length=64)
    session_id: str = Field(..., max_length=64)
    shot_id: str = Field(..., max_length=128)
    # Старый кадр (ассет), который обновляем. Может отсутствовать — тогда
    # обновление готовится «с нуля» по шоту (например, кадр ещё не создавался).
    source_asset_id: str | None = None
    # Новый итоговый промпт/негатив, вычисленные resolve_shot() на момент
    # подготовки (включают общие правила + локальные переопределения шота).
    new_prompt: str = ""
    negative_prompt: list[str] = Field(default_factory=list)
    # Промпт движения — только если задание относится к видео (задел на будущее;
    # для image-обновлений остаётся пустым).
    motion_prompt: str = ""
    # Снимок применённых общих правил на момент подготовки (для UI и provenance).
    applied_rules: dict = Field(default_factory=dict)
    # Референсы (адресные ассеты): общие reference_asset_ids + утверждённые
    # образы персонажей/локаций, попавших в resolve этого шота.
    reference_asset_ids: list[str] = Field(default_factory=list)
    # Исполнитель (mock / agnes / auto) и рабочий процесс, выбранные режиссёром.
    backend: str = Field("mock", max_length=64)
    workflow: str = Field("mock", max_length=128)
    expected_result_type: str = Field("image", max_length=32)
    status: str = Field(PREPARED_STATUS_PREPARED, max_length=32)
    # Новый вариант (ассет), созданный генерацией из этого задания.
    new_asset_id: str | None = None
    created_at: str = ""
    updated_at: str = ""


class PreparedUpdateCreateRequest(BaseModel):
    """Тело POST /studio/{session_id}/prepared-updates (подготовка без генерации)."""

    model_config = _PREPARED_CONFIG

    shot_id: str = Field(..., min_length=1, max_length=128)
    source_asset_id: str | None = Field(None, max_length=64)
    # Исполнитель выбирается режиссёром из IMAGE_EXECUTORS (по умолчанию mock —
    # без трат); запуск идёт существующим POST /studio/image-jobs.
    backend: str = Field("mock", min_length=1, max_length=64)


class PreparedUpdatePatchRequest(BaseModel):
    """Тело PATCH /studio/{session_id}/prepared-updates/{prepared_id}.

    Статусное продвижение задания фронтом после запуска существующего
    image-jobs: generating → done/failed-контекст → approved.
    """

    model_config = _PREPARED_CONFIG

    status: str | None = Field(None, max_length=32)
    new_asset_id: str | None = Field(None, max_length=64)
    backend: str | None = Field(None, min_length=1, max_length=64)
    workflow: str | None = Field(None, max_length=128)

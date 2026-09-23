"""
bootstrap — DEPRECATED.

prepare_core_path() удалена. sys.path для core/CORE добавляется
в main.py при старте приложения.

Этот модуль сохранён для обратной совместимости с legacy-импортами.
"""

import warnings


def prepare_core_path(*args, **kwargs):
    warnings.warn(
        "prepare_core_path() удалена. sys.path добавляется в main.py.",
        DeprecationWarning,
        stacklevel=2,
    )

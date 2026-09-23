"""
Анонимная аналитика использования без персональных данных.
Собирает метрики использования для улучшения сервиса.
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from threading import Lock



class AnonymousAnalytics:
    """
    Анонимная аналитика использования.

    НЕ собирает персональные данные:
    - Без IP адресов
    - Без user_id
    - Без содержимого вопросов
    - Без идентификаторов сессий

    Собирает только агрегированные метрики:
    - Количество запросов по типам
    - Среднее время ответа
    - Количество ошибок
    - Популярные категории запросов (по длине, языку и т.д.)
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            # Используем абсолютный путь относительно этого файла
            storage_path = Path(__file__).resolve().parent.parent / "analytics_data.json"
        self.storage_path = storage_path
        self._lock = Lock()
        self._metrics = {
            "total_requests": 0,
            "requests_by_type": defaultdict(int),
            "requests_by_hour": defaultdict(int),
            "response_times": [],
            "error_count": 0,
            "question_lengths": [],
            "start_time": datetime.now().isoformat()
        }
        self._load()

    def _load(self):
        """Загружает метрики из файла."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Восстанавливаем defaultdict
                    self._metrics["requests_by_type"] = defaultdict(int, data.get("requests_by_type", {}))
                    self._metrics["requests_by_hour"] = defaultdict(int, data.get("requests_by_hour", {}))
                    self._metrics["total_requests"] = data.get("total_requests", 0)
                    self._metrics["response_times"] = data.get("response_times", [])
                    self._metrics["error_count"] = data.get("error_count", 0)
                    self._metrics["question_lengths"] = data.get("question_lengths", [])
                    self._metrics["start_time"] = data.get("start_time", datetime.now().isoformat())
            except Exception as e:
                print(f"[Analytics] Failed to load: {e}")

    def _save(self):
        """Сохраняет метрики в файл."""
        try:
            # Преобразуем defaultdict в dict для JSON
            data = {
                "total_requests": self._metrics["total_requests"],
                "requests_by_type": dict(self._metrics["requests_by_type"]),
                "requests_by_hour": dict(self._metrics["requests_by_hour"]),
                "response_times": self._metrics["response_times"][-1000:],  # Храним только последние 1000
                "error_count": self._metrics["error_count"],
                "question_lengths": self._metrics["question_lengths"][-1000:],  # Храним только последние 1000
                "start_time": self._metrics["start_time"],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Analytics] Failed to save: {e}")

    def track_request(self, request_type: str, response_time: float, success: bool, question_length: int = 0):
        """
        Отслеживает запрос.

        Args:
            request_type: Тип запроса (ask, generate, health и т.д.)
            response_time: Время ответа в секундах
            success: Успешен ли запрос
            question_length: Длина вопроса (только длина, без содержимого)
        """
        with self._lock:
            self._metrics["total_requests"] += 1
            self._metrics["requests_by_type"][request_type] += 1

            # Текущий час для временного анализа
            current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
            self._metrics["requests_by_hour"][current_hour] += 1

            # Время ответа
            self._metrics["response_times"].append(response_time)

            # Ошибки
            if not success:
                self._metrics["error_count"] += 1

            # Длина вопроса (анонимно)
            if question_length > 0:
                self._metrics["question_lengths"].append(question_length)

            # Периодически сохраняем
            if self._metrics["total_requests"] % 10 == 0:
                self._save()

    def get_metrics(self) -> dict:
        """
        Возвращает агрегированные метрики.

        Возвращает только анонимные агрегированные данные.
        """
        with self._lock:
            response_times = self._metrics["response_times"]
            question_lengths = self._metrics["question_lengths"]

            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            avg_question_length = sum(question_lengths) / len(question_lengths) if question_lengths else 0

            return {
                "total_requests": self._metrics["total_requests"],
                "requests_by_type": dict(self._metrics["requests_by_type"]),
                "requests_by_hour": dict(self._metrics["requests_by_hour"]),
                "avg_response_time_ms": round(avg_response_time * 1000, 2),
                "error_rate": round(self._metrics["error_count"] / max(self._metrics["total_requests"], 1) * 100, 2),
                "avg_question_length": round(avg_question_length, 2),
                "start_time": self._metrics["start_time"],
                "uptime_hours": round((datetime.now() - datetime.fromisoformat(self._metrics["start_time"])).total_seconds() / 3600, 2)
            }

    def reset_metrics(self):
        """Сбрасывает метрики."""
        with self._lock:
            self._metrics = {
                "total_requests": 0,
                "requests_by_type": defaultdict(int),
                "requests_by_hour": defaultdict(int),
                "response_times": [],
                "error_count": 0,
                "question_lengths": [],
                "start_time": datetime.now().isoformat()
            }
            self._save()


# Глобальный экземпляр
analytics = AnonymousAnalytics()

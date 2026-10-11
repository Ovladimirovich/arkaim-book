"""
Load Test для Arkaim Digital Consciousness.
Тестирует реальные эндпоинты: /book/ask (Book Intelligence) и /v1/chat (Core Runtime).
"""
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import requests

# ── Конфигурация ───────────────────────────────────────────────────
BOOK_API_URL = "http://127.0.0.1:9090/book/ask"
CORE_API_URL = "http://127.0.0.1:8642/v1/chat"
CONCURRENCY = 10  # Количество одновременных запросов
TOTAL_REQUESTS = 50  # Всего запросов
TIMEOUT = 30.0  # Таймаут запроса в секундах

TEST_QUESTION = {
    "question": "Какие основные темы поднимаются в книге 'Наследие Аркаима'?"
}

TEST_CHAT = {
    "messages": [
        {"role": "system", "content": "Ты — Хранитель книги 'Наследие Аркаима'. Отвечай кратко."},
        {"role": "user", "content": "Расскажи о главном герое."}
    ],
    "model": "GigaChat-Pro",
    "temperature": 0.7,
    "max_tokens": 500,
}


def send_book_request(index: int) -> Tuple[int, float, bool]:
    """Отправляет запрос к Book Intelligence API."""
    start = time.time()
    try:
        resp = requests.post(BOOK_API_URL, json=TEST_QUESTION, timeout=TIMEOUT)
        elapsed = time.time() - start
        success = resp.status_code == 200
        return (resp.status_code, elapsed, success)
    except Exception as e:
        elapsed = time.time() - start
        return (0, elapsed, False)


def send_chat_request(index: int) -> Tuple[int, float, bool]:
    """Отправляет запрос к Core Chat API."""
    start = time.time()
    try:
        resp = requests.post(CORE_API_URL, json=TEST_CHAT, timeout=TIMEOUT)
        elapsed = time.time() - start
        success = resp.status_code == 200
        return (resp.status_code, elapsed, success)
    except Exception as e:
        elapsed = time.time() - start
        return (0, elapsed, False)


def run_load_test(
    name: str,
    target_url: str,
    request_fn,
    concurrency: int = CONCURRENCY,
    total: int = TOTAL_REQUESTS,
):
    """Запускает нагрузочный тест и выводит статистику."""
    print(f"\n{'=' * 60}")
    print(f"📊 LOAD TEST: {name}")
    print(f"   URL: {target_url}")
    print(f"   Concurrency: {concurrency}")
    print(f"   Total requests: {total}")
    print(f"{'=' * 60}")

    latencies: List[float] = []
    statuses: List[int] = []
    success_count = 0
    fail_count = 0

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(request_fn, i): i for i in range(total)
        }
        for future in as_completed(futures):
            status_code, latency, success = future.result()
            latencies.append(latency)
            statuses.append(status_code)
            if success:
                success_count += 1
            else:
                fail_count += 1

    total_time = time.time() - start_time

    # Статистика
    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg = statistics.mean(latencies)
    rps = total / total_time

    print(f"\n📈 RESULTS:")
    print(f"   Total time:     {total_time:.2f}s")
    print(f"   Requests/sec:   {rps:.1f} RPS")
    print(f"   Success:        {success_count}/{total}")
    print(f"   Failures:       {fail_count}/{total}")
    print(f"   Avg latency:    {avg*1000:.0f} ms")
    print(f"   P50 latency:    {p50*1000:.0f} ms")
    print(f"   P95 latency:    {p95*1000:.0f} ms")
    print(f"   P99 latency:    {p99*1000:.0f} ms")

    status_counts = {}
    for s in statuses:
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"   Status codes:   {status_counts}")

    # Пороги качества
    if p95 < 3000:
        print("   ✅ QUALITY: P95 < 3s — отлично")
    elif p95 < 5000:
        print("   ⚠️  QUALITY: P95 < 5s — приемлемо")
    else:
        print("   ❌ QUALITY: P95 > 5s — требуется оптимизация")

    if fail_count > total * 0.05:
        print(f"   ❌ QUALITY: Error rate {fail_count/total*100:.1f}% > 5% — требуется анализ")

    print(f"{'=' * 60}")
    return {
        "name": name,
        "total_time": total_time,
        "rps": rps,
        "success": success_count,
        "failures": fail_count,
        "avg_ms": avg * 1000,
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
        "p99_ms": p99 * 1000,
    }


def main():
    print("🚀 ARKAIM DIGITAL CONSCIOUSNESS — LOAD TEST SUITE")
    print(f"   Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Concurrency: {CONCURRENCY}, Total per test: {TOTAL_REQUESTS}")

    results = []

    # Тест 1: Book Intelligence
    results.append(run_load_test(
        "Book Intelligence API",
        BOOK_API_URL,
        send_book_request,
    ))

    # Тест 2: Core Chat
    results.append(run_load_test(
        "Core Chat API",
        CORE_API_URL,
        send_chat_request,
    ))

    # Сводка
    print(f"\n{'=' * 60}")
    print("📋 SUMMARY")
    print(f"{'=' * 60}")
    for r in results:
        status_icon = "✅" if r["p95_ms"] < 3000 else "⚠️"
        print(f"   {status_icon} {r['name']}: {r['rps']:.1f} RPS, "
              f"P50={r['p50_ms']:.0f}ms, P95={r['p95_ms']:.0f}ms, "
              f"Success={r['success']}/{r['success']+r['failures']}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
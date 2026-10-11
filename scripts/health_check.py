"""
health_check — проверка всех сервисов проекта.
"""
import asyncio
import httpx
import sys
from datetime import datetime

SERVICES = [
    ("Core", "http://127.0.0.1:8642/health"),
    ("Frontend", "http://127.0.0.1:3000"),
]


async def check(client: httpx.AsyncClient, name: str, url: str) -> dict:
    try:
        t0 = asyncio.get_event_loop().time()
        r = await client.get(url, timeout=5.0)
        elapsed = (asyncio.get_event_loop().time() - t0) * 1000
        return {
            "name": name,
            "status": "OK" if r.status_code == 200 else f"HTTP {r.status_code}",
            "latency_ms": round(elapsed, 1),
            "body": r.text[:200] if r.status_code == 200 else r.text[:100],
        }
    except Exception as e:
        return {"name": name, "status": "DOWN", "latency_ms": None, "body": str(e)}


async def main():
    print("=" * 60)
    print(f"  Health Check  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[check(client, n, u) for n, u in SERVICES])

    all_ok = True
    for r in results:
        icon = "✓" if r["status"] == "OK" else "✗"
        latency = f"{r['latency_ms']}ms" if r["latency_ms"] is not None else "---"
        print(f"  {icon} {r['name']:10s} {r['status']:12s} {latency:>8s}")
        if r["status"] != "OK":
            all_ok = False
            print(f"     {r['body']}")

    print("=" * 60)
    if all_ok:
        print("  Все сервисы работают.")
        return 0
    else:
        print("  Некоторые сервисы недоступны.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Small repeatable concurrency gate; run against the fully migrated CI service."""
import asyncio
import os
import statistics
import time

import httpx

BASE_URL = os.getenv("LOAD_BASE_URL", "http://127.0.0.1:8000")
REQUESTS = int(os.getenv("LOAD_REQUESTS", "500"))
CONCURRENCY = int(os.getenv("LOAD_CONCURRENCY", "50"))


async def main() -> None:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    durations: list[float] = []
    failures: list[str] = []
    paths = ["/health", "/v1/catalog/products?page_size=24"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        async def one(index: int) -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(paths[index % len(paths)])
                    if response.status_code != 200:
                        failures.append(f"{response.status_code}:{paths[index % len(paths)]}")
                except Exception as exc:
                    failures.append(type(exc).__name__)
                durations.append((time.perf_counter() - started) * 1000)

        await asyncio.gather(*(one(index) for index in range(REQUESTS)))

    ordered = sorted(durations)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    print({
        "requests": REQUESTS, "concurrency": CONCURRENCY, "failures": len(failures),
        "p50_ms": round(statistics.median(ordered), 1), "p95_ms": round(p95, 1),
    })
    if failures or p95 > 500:
        raise SystemExit(f"Load gate failed: failures={failures[:5]} p95_ms={p95:.1f}")


if __name__ == "__main__":
    asyncio.run(main())

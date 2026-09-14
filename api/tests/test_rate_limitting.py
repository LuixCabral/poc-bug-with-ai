import httpx
import asyncio

TOTAL_REQUESTS = 11
URL = "http://localhost:8000/api/chat"
PAYLOAD = {"message": "teste rate limit"}


async def send(client: httpx.AsyncClient, i: int) -> None:
    print(f"--- Request {i} (enviando) ---")
    async with client.stream("POST", URL, json=PAYLOAD) as r:
        print(f"  Request {i} → Status: {r.status_code}")
        async for line in r.aiter_lines():
            if line:
                print(f"  [{i}] {line}")


async def main() -> None:
    # Timeout alto pois o LLM pode demorar; todas as requisições são disparadas ao mesmo tempo
    async with httpx.AsyncClient(timeout=120) as client:
        tasks = [send(client, i) for i in range(1, TOTAL_REQUESTS + 1)]
        await asyncio.gather(*tasks)


asyncio.run(main())

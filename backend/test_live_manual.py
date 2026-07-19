import asyncio
import httpx


BASE_URL = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        start = await client.post(f"{BASE_URL}/api/v1/live/start")
        start.raise_for_status()
        session_id = start.json()["session_id"]

        msg = await client.post(f"{BASE_URL}/api/v1/live/message", json={
            "session_id": session_id,
            "text": "Cai nay bao nhieu tien?",
            "source_lang": "vi",
            "target_lang": "en",
            "speaker": "vendor",
            "region": "hanoi",
        })
        msg.raise_for_status()
        print("LIVE MESSAGE:", msg.json())

        await asyncio.sleep(2)
        insights = await client.get(f"{BASE_URL}/api/v1/live/insights/{session_id}")
        insights.raise_for_status()
        print("INSIGHTS:", insights.json())


if __name__ == "__main__":
    asyncio.run(main())

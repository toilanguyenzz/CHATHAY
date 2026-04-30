"""Quick test for DeepSeek API key."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def test():
    key = os.getenv("DEEPSEEK_API_KEY", "")
    print(f"Key: {key[:8]}...{key[-4:]}")

    # Test 1: Simple text (tieng Viet)
    print("\n--- Test 1: Text response (tieng Viet) ---")
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ban la tro ly AI. Tra loi bang tieng Viet CO DAU. KHONG dung tieng Trung."},
            {"role": "user", "content": "Xin chao! Ban la model gi? Tra loi ngan gon 2 cau thoi."},
        ],
        "max_tokens": 200,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            model = data.get("model", "?")
            usage = data.get("usage", {})
            inp = usage.get("prompt_tokens", 0)
            out = usage.get("completion_tokens", 0)
            print(f"Model: {model}")
            print(f"Response: {content}")
            print(f"Tokens: input={inp}, output={out}")
        else:
            print(f"Error: {r.text}")

    # Test 2: JSON response
    print("\n--- Test 2: JSON response ---")
    body2 = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Tra loi bang tieng Viet CO DAU. KHONG dung tieng Trung Quoc."},
            {"role": "user", "content": 'Tom tat ngan gon: Python la ngon ngu lap trinh pho bien nhat the gioi. Tra ve JSON: {"title": "...", "summary": "..."}'},
        ],
        "max_tokens": 300,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r2 = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body2,
        )
        print(f"Status: {r2.status_code}")
        if r2.status_code == 200:
            data2 = r2.json()
            content2 = data2["choices"][0]["message"]["content"]
            usage2 = data2.get("usage", {})
            inp2 = usage2.get("prompt_tokens", 0)
            out2 = usage2.get("completion_tokens", 0)
            print(f"JSON Response: {content2}")
            print(f"Tokens: input={inp2}, output={out2}")
        else:
            print(f"Error: {r2.text}")

    # Test 3: Check balance
    print("\n--- Test 3: Account balance ---")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r3 = await client.get(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {key}"},
        )
        if r3.status_code == 200:
            balance = r3.json()
            print(f"Balance: {balance}")
        else:
            print(f"Balance check: {r3.status_code} - {r3.text}")

    print("\n=== ALL TESTS DONE ===")


asyncio.run(test())

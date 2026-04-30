"""Test DeepSeek V4 Flash performance — latency, throughput, JSON quality."""

import os
import time
import json
import asyncio
import httpx
from typing import Dict, Any

# Import config to load .env automatically
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import config

# ═══════════════════════════════════════════════════════════════
# CONFIG (from loaded config)
# ═══════════════════════════════════════════════════════════════

DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL = config.DEEPSEEK_BASE_URL
DEEPSEEK_MODEL = config.DEEPSEEK_MODEL

# Test prompts
SHORT_PROMPT = "Hãy tóm tắt: 'Học sinh cần chăm chỉ ôn tập để đạt điểm cao trong kỳ thi.'"
LONG_PROMPT = """
Hãy phân tích sâu về chủ đề: Trí tuệ nhân tạo (AI) đang thay đổi cách chúng ta làm việc.

Chi tiết cần covering:
1. Lịch sử phát triển AI từ 1950 đến nay
2. Các loại AI khác nhau: Machine Learning, Deep Learning, Generative AI
3. Ứng dụng thực tế trong y tế, giáo dục, kinh doanh
4. Tác động đến thị trường lao động
5. Đạo đức và rủi ro của AI
6. Xu hướng tương lai 2025-2030

Hãy trả về JSON với các trường: overview, key_points (list), conclusion.
"""

EXPECTED_JSON_SCHEMA = {
    "overview": "string",
    "key_points": ["string"],
    "conclusion": "string"
}


# ═══════════════════════════════════════════════════════════════
# DEEPSEEK CLIENT
# ═══════════════════════════════════════════════════════════════

async def call_deepseek(
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    response_json: bool = True,
) -> Dict[str, Any]:
    """Gọi DeepSeek V4 Flash API."""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if response_json:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        start = time.time()
        response = await client.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=body,
        )
        elapsed = time.time() - start

        response.raise_for_status()
        data = response.json()

        return {
            "content": data["choices"][0]["message"]["content"],
            "latency": elapsed,
            "usage": data.get("usage", {}),
            "model": data.get("model", ""),
            "id": data.get("id", ""),
        }


# ═══════════════════════════════════════════════════════════════
# TEST SUITES
# ═══════════════════════════════════════════════════════════════

async def test_connection():
    """Test 1: Kết nối cơ bản — DeepSeek có respond không?"""
    print("\n" + "=" * 70)
    print("TEST 1: CONNECTION TEST")
    print("=" * 70)

    try:
        result = await call_deepseek(
            prompt=SHORT_PROMPT,
            max_tokens=512,
            response_json=False,  # Text mode
        )
        print(f"[PASS] DeepSeek responded in {result['latency']:.2f}s")
        print(f"  Response length: {len(result['content'])} chars")
        print(f"  Model: {result.get('model', 'N/A')}")
        print(f"  Usage: {result.get('usage', {})}")
        return True
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False


async def test_json_mode():
    """Test 2: JSON mode — DeepSeek trả về JSON hợp lệ?"""
    print("\n" + "=" * 70)
    print("TEST 2: JSON MODE TEST")
    print("=" * 70)

    json_prompt = """
    Hãy trả về JSON với thông tin sau:
    {
      "summary": "Tóm tắt về AI",
      "points": ["Machine Learning", "Deep Learning", "Generative AI"],
      "year": 2025
    }
    Chỉ trả JSON, không thêm gì khác.
    """

    try:
        result = await call_deepseek(
            prompt=json_prompt,
            max_tokens=1024,
            response_json=True,
        )
        content = result["content"]
        print(f"[INFO] Raw response: {content[:200]}...")

        # Parse JSON
        try:
            parsed = json.loads(content)
            print(f"[PASS] JSON valid: {list(parsed.keys())}")
            print(f"  Latency: {result['latency']:.2f}s")
            return True
        except json.JSONDecodeError as e:
            print(f"[FAIL] Invalid JSON: {e}")
            print(f"  Full response: {content}")
            return False

    except Exception as e:
        print(f"[FAIL] JSON mode test failed: {e}")
        return False


async def test_long_prompt():
    """Test 3: Prompt dài — DeepSeek handle được không? Latency bao lâu?"""
    print("\n" + "=" * 70)
    print("TEST 3: LONG PROMPT TEST (~500 words)")
    print("=" * 70)

    try:
        result = await call_deepseek(
            prompt=LONG_PROMPT,
            max_tokens=4096,
            response_json=True,
        )
        content = result["content"]
        latency = result["latency"]

        print(f"[INFO] Response length: {len(content)} chars")
        print(f"[INFO] Latency: {latency:.2f}s")
        print(f"[INFO] Usage: {result.get('usage', {})}")

        # Try parse JSON
        try:
            parsed = json.loads(content)
            print(f"[PASS] JSON valid with keys: {list(parsed.keys())}")
            print(f"  Overview: {parsed.get('overview', '')[:100]}...")
            print(f"  Key points count: {len(parsed.get('key_points', []))}")
            return True
        except json.JSONDecodeError:
            print(f"[WARN] JSON invalid, but response received")
            print(f"  First 300 chars: {content[:300]}")
            return False

    except Exception as e:
        print(f"[FAIL] Long prompt test failed: {e}")
        return False


async def test_concurrent_requests(num_requests: int = 3):
    """Test 4: Concurrent requests — throughput và rate limit."""
    print("\n" + "=" * 70)
    print(f"TEST 4: CONCURRENT REQUESTS ({num_requests} parallel)")
    print("=" * 70)

    tasks = []
    for i in range(num_requests):
        task = call_deepseek(
            prompt=f"Test request {i+1}: Hãy tóm tắt 3 ý về giáo dục.",
            max_tokens=512,
            response_json=False,
        )
        tasks.append(task)

    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start

    success_count = 0
    total_latency = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  Request {i+1}: FAILED — {result}")
        else:
            success_count += 1
            total_latency += result["latency"]
            print(f"  Request {i+1}: OK — latency {result['latency']:.2f}s")

    avg_latency = total_latency / success_count if success_count > 0 else 0
    print(f"\n[SUMMARY]")
    print(f"  Success: {success_count}/{num_requests}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Avg latency: {avg_latency:.2f}s")
    print(f"  Throughput: {num_requests / total_time:.2f} req/s")

    return success_count == num_requests


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 70)
    print("DEEPSEEK V4 FLASH PERFORMANCE TEST")
    print("=" * 70)

    if not DEEPSEEK_API_KEY:
        print("\n[ERROR] DEEPSEEK_API_KEY not set in environment!")
        print("  Please run: set DEEPSEEK_API_KEY=sk-...")
        print("  Or add to .env file.")
        return

    print(f"\n[INFO] Model: {DEEPSEEK_MODEL}")
    print(f"[INFO] Base URL: {DEEPSEEK_BASE_URL}")

    results = []

    # Test 1: Connection
    results.append(await test_connection())

    # Test 2: JSON mode
    results.append(await test_json_mode())

    # Test 3: Long prompt
    results.append(await test_long_prompt())

    # Test 4: Concurrent (optional — comment nếu muốn tránh rate limit)
    # results.append(await test_concurrent_requests(3))

    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED — DeepSeek V4 Flash is working!")
        print("\nNEXT STEPS:")
        print("  1. Monitor latency in production logs")
        print("  2. Check cost savings vs Gemini")
        print("  3. If latency >5s for text, consider Gemini fallback strategy")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed — check errors above")
        print("\nPOSSIBLE CAUSES:")
        print("  - Invalid API key")
        print("  - Network timeout")
        print("  - Rate limit exceeded")
        print("  - Model name wrong (should be 'deepseek-chat'?)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

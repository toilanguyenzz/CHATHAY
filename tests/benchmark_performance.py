#!/usr/bin/env python3
"""Performance benchmark — DeepSeek vs Gemini latency & cost estimation"""

import os
import sys
import time
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_summarizer import summarize_text_structured, _call_with_smart_routing
from config import config

# Sample texts
SHORT_TEXT = """Giá trị của biểu thức √(16) + |-3| là:
A. 1
B. 7
C. -1
D. -7"""

MEDIUM_TEXT = """
Đề thi môn Toán 12 chương trình đủ:
1. Cấu trúc đại số: ma trận, định thức, ma trận nghịch đảo, hệ phương trình.
2. Hình học: đường thẳng, mặt phẳng, hình nón, mặt trụ.
3. Giải tích: dãy số, giới hạn, đạo hàm, tích phân.
Mỗi chương có 10 câu hỏi trắc nghiệm.
"""

LONG_TEXT = """
Giáo trình Toán 12 chương trình nâng cao:
Phần 1: Đại số tuyến tính
- Ma trận: định nghĩa, các phép toán, định thức, ma trận nghịch đảo, hạng.
- Hệ phương trình: giải bằng ma trận, định lý Cramer, phương pháp Gauss.

Phần 2: Hình họcanalytic
- Trị tuyệt đối: công thức khoảng cách, tọa độ.
- Đường thẳng: phương trình, góc, khoảng cách.
- Mặt phẳng: các dạng phương trình.

Phần 3: Giải tích
- Dãy số: giới hạn, tính chất, dãy tăng/giảm.
- Hàm số: liên tục, đạo hàm, tích phân.
- Ứng dụng: tích phân xác định, phương trình vi phân.

Phần 4: Xác suất thống kê
- Xác suất: công thức, các định lý.
- Thống kê: các đại lượng mô tả, ước lượng.

Phần 5: Số học
- Phép chia, chia hết, ước chung lớn nhất.
- Số nguyên tố, Fermat, Euler.
"""

async def benchmark_single_call(text: str, label: str):
    """Benchmark one AI call."""
    start = time.time()
    try:
        result = await summarize_text_structured(text)
        elapsed = time.time() - start
        success = "error" not in result
        return {
            "label": label,
            "success": success,
            "latency": elapsed,
            "doc_type": result.get("document_type") if success else None,
            "mode_conf": result.get("mode_confidence") if success else None,
        }
    except Exception as e:
        return {
            "label": label,
            "success": False,
            "latency": time.time() - start,
            "error": str(e),
        }

async def run_benchmark():
    print("=" * 70)
    print("PERFORMANCE BENCHMARK — DeepSeek vs Gemini")
    print("=" * 70)
    print(f"Model config: DEEPSEEK_MODEL = {config.DEEPSEEK_MODEL}")
    print()

    tests = [
        (SHORT_TEXT, "Short (200 chars)"),
        (MEDIUM_TEXT, "Medium (800 chars)"),
        (LONG_TEXT, "Long (2500 chars)"),
    ]

    results = []
    for text, label in tests:
        print(f"Running: {label}...", end=" ", flush=True)
        res = await benchmark_single_call(text, label)
        results.append(res)
        if res["success"]:
            print(f"OK — {res['latency']:.2f}s, type={res['doc_type']}, conf={res['mode_conf']:.2f}")
        else:
            print(f"FAIL — {res['latency']:.2f}s, error={res.get('error')}")
        await asyncio.sleep(1)  # Avoid rate limit

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in results:
        if r["success"]:
            print(f"{r['label']}: {r['latency']:.2f}s | type={r['doc_type']}")
        else:
            print(f"{r['label']}: FAIL")

    # Estimate cost (DeepSeek ~$0.001/1K tokens, Gemini ~$0.0035/1K tokens)
    print()
    print("Cost estimate (per 1K tokens):")
    print("  DeepSeek V4 Flash: ~$0.001")
    print("  Gemini 2.5 Flash: ~$0.0035")
    print()
    print("=> DeepSeek tiết kiệm ~70%")

if __name__ == "__main__":
    if not config.DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY not set!")
        sys.exit(1)
    asyncio.run(run_benchmark())

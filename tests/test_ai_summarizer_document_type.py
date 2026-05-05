#!/usr/bin/env python3
"""Test: summarize_text_structured() returns document_type for Study Mode"""

import sys
import os
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from services.ai_summarizer import summarize_text_structured

# Sample exam text (Vietnamese math)
EXAM_TEXT = """
ĐỀ THI THPT QUỐC GIA 2025
Môn: Toán
Thời gian: 90 phút

Câu 1: Giá trị của biểu thức √(16) + |-3| là:
A. 1
B. 7
C. -1
D. -7

Câu 2: Phương trình x² - 5x + 6 = 0 có nghiệm là:
A. x₁=1, x₂=6
B. x₁=2, x₂=3
C. x₁=-2, x₂=-3
D. x₁=3, x₂=2
"""

@pytest.mark.asyncio
async def test_document_type_detection():
    print("=" * 70)
    print("TEST: summarize_text_structured() -> document_type")
    print("=" * 70)
    print()

    result = await summarize_text_structured(EXAM_TEXT)

    print(f"Result keys: {list(result.keys())}")
    print(f"document_type: {result.get('document_type', 'MISSING')}")
    print(f"mode_confidence: {result.get('mode_confidence', 'MISSING')}")

    assert "document_type" in result, "Missing 'document_type' in result"
    assert result["document_type"] == "education", f"Expected 'education', got '{result['document_type']}'"
    assert "mode_confidence" in result, "Missing 'mode_confidence'"
    assert result["mode_confidence"] > 0.8, f"Low confidence: {result['mode_confidence']}"

    print()
    print("✅ PASS: document_type correctly detected as 'education'")
    print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_document_type_detection())

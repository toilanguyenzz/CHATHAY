"""Quick test to verify hybrid routing logic works correctly."""

import asyncio
import json
import os
from unittest.mock import patch

# Set dummy keys for testing
os.environ["DEEPSEEK_API_KEY"] = "sk-test-dummy"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"

from config import config
from services.ai_summarizer import _call_with_smart_routing


def valid_summary_json() -> str:
    return json.dumps({
        "document_title": "Tài liệu kiểm thử",
        "overview": "Đây là phần tổng quan đủ rõ để vượt qua Quality Gate.",
        "points": [
            {
                "title": "Ý chính 1",
                "brief": "Tóm tắt ý chính đầu tiên.",
                "detail": "Chi tiết ý chính đầu tiên đủ dài, có nội dung rõ ràng và không chung chung."
            },
            {
                "title": "Ý chính 2",
                "brief": "Tóm tắt ý chính thứ hai.",
                "detail": "Chi tiết ý chính thứ hai đủ dài, có dữ kiện minh họa và văn phong tiếng Việt."
            },
            {
                "title": "Ý chính 3",
                "brief": "Tóm tắt ý chính thứ ba.",
                "detail": "Chi tiết ý chính thứ ba đủ dài để chứng minh output đã đạt chuẩn chất lượng."
            },
        ],
    }, ensure_ascii=False)


async def test_routing_logic():
    """Test that routing chooses correct model based on content type."""

    print("=" * 60)
    print("TEST: Hybrid AI Routing Logic")
    print("=" * 60)

    # Test 1: DeepSeek direct fast path when Quality Gate passes
    print("\n[Test 1] Text content with DeepSeek key present + clean JSON")
    print("Expected: DeepSeek direct return, Gemini not called")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        mock_deepseek.return_value = valid_summary_json()
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            try:
                await _call_with_smart_routing(
                    content="Test text content",
                    force_gemini=False
                )
                assert mock_deepseek.called, "DeepSeek should be called"
                assert not mock_gemini.called, "Gemini should NOT be called when Quality Gate passes"
                print("[PASS] DeepSeek called, Quality Gate passed, Gemini not called")
            except Exception as e:
                print(f"[FAIL] {e}")

    # Test 2: Gemini fallback when DeepSeek fails
    print("\n[Test 2] Text content but DeepSeek raises exception")
    print("Expected: Should fallback to Gemini")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        mock_deepseek.side_effect = Exception("DeepSeek API error")
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            mock_gemini.return_value = valid_summary_json()
            try:
                await _call_with_smart_routing(
                    content="Test text",
                    force_gemini=False
                )
                assert mock_deepseek.called, "DeepSeek should be tried first"
                assert mock_gemini.called, "Gemini should be called as fallback"
                print("[PASS] DeepSeek tried then fell back to Gemini")
            except Exception as e:
                print(f"[FAIL] {e}")

    # Test 3: Force Gemini for vision (image)
    print("\n[Test 3] Vision content with force_gemini=True")
    print("Expected: Should skip DeepSeek and call Gemini directly")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            mock_gemini.return_value = valid_summary_json()
            try:
                # Simulate image content (list, not string)
                await _call_with_smart_routing(
                    content=["image", "data"],
                    force_gemini=True
                )
                assert not mock_deepseek.called, "DeepSeek should NOT be called for vision"
                assert mock_gemini.called, "Gemini should be called"
                print("[PASS] Gemini called directly (skipped DeepSeek)")
            except Exception as e:
                print(f"[FAIL] {e}")

    # Test 4: No DeepSeek key → Gemini only
    print("\n[Test 4] Text content but DEEPSEEK_API_KEY is empty")
    print("Expected: Should call Gemini directly")
    original_key = config.DEEPSEEK_API_KEY
    try:
        config.DEEPSEEK_API_KEY = ""  # Simulate no key
        with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
            with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
                mock_gemini.return_value = valid_summary_json()
                try:
                    await _call_with_smart_routing(
                        content="Test text",
                        force_gemini=False
                    )
                    assert not mock_deepseek.called, "DeepSeek should NOT be called when no key"
                    assert mock_gemini.called, "Gemini should be called"
                    print("[PASS] Gemini called (DeepSeek skipped)")
                except Exception as e:
                    print(f"[FAIL] {e}")
    finally:
        config.DEEPSEEK_API_KEY = original_key

    # Test 5: DeepSeek succeeds but Quality Gate fails -> Gemini rescue
    print("\n[Test 5] DeepSeek output has Chinese/malformed JSON")
    print("Expected: Should call Gemini rescue after DeepSeek")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        mock_deepseek.return_value = '这是中文 output bị lỗi, không phải JSON'
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            mock_gemini.return_value = valid_summary_json()
            try:
                await _call_with_smart_routing(
                    content="Test text content",
                    force_gemini=False
                )
                assert mock_deepseek.called, "DeepSeek should be called first"
                assert mock_gemini.called, "Gemini should rescue failed Quality Gate output"
                print("[PASS] DeepSeek tried, Quality Gate failed, Gemini rescued")
            except Exception as e:
                print(f"[FAIL] {e}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_routing_logic())

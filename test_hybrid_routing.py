"""Quick test to verify hybrid routing logic works correctly."""

import asyncio
import os
from unittest.mock import patch

# Set dummy keys for testing
os.environ["DEEPSEEK_API_KEY"] = "sk-test-dummy"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"

from config import config
from services.ai_summarizer import _call_with_smart_routing


async def test_routing_logic():
    """Test that routing chooses correct model based on content type."""

    print("=" * 60)
    print("TEST: Hybrid AI Routing Logic")
    print("=" * 60)

    # Test 1: DeepSeek should be chosen for text when key exists
    print("\n[Test 1] Text content with DeepSeek key present")
    print("Expected: Should try DeepSeek first")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        mock_deepseek.return_value = '{"result": "deepseek response"}'
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            try:
                await _call_with_smart_routing(
                    content="Test text content",
                    force_gemini=False
                )
                assert mock_deepseek.called, "DeepSeek should be called"
                assert not mock_gemini.called, "Gemini should NOT be called when DeepSeek succeeds"
                print("[PASS] DeepSeek called, Gemini not called")
            except Exception as e:
                print(f"[FAIL] {e}")

    # Test 2: Gemini fallback when DeepSeek fails
    print("\n[Test 2] Text content but DeepSeek raises exception")
    print("Expected: Should fallback to Gemini")
    with patch('services.ai_summarizer._call_deepseek') as mock_deepseek:
        mock_deepseek.side_effect = Exception("DeepSeek API error")
        with patch('services.ai_summarizer._call_gemini_with_fallback') as mock_gemini:
            mock_gemini.return_value = '{"result": "gemini response"}'
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
            mock_gemini.return_value = '{"result": "gemini vision response"}'
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
                mock_gemini.return_value = '{"result": "gemini response"}'
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

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_routing_logic())

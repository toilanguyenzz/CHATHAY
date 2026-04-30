"""Mode Detection — phân loại tài liệu thành STUDY vs BUSINESS"""

import json
import logging
from typing import Any, Dict

import google.generativeai as genai

from config import config

logger = logging.getLogger(__name__)

DETECT_MODE_PROMPT = """
Phân loại tài liệu sau thành MỘT trong các loại:

1. STUDY_MATERIAL — nếu có MỘT trong các đặc điểm sau:
   - Đề thi (câu hỏi trắc nghiệm, true/false, tự luận)
   - Bài giảng, slide (có chương, mục, khái niệm)
   - Sách giáo trình (có bài, chương, ví dụ)
   - Tài liệu ôn thi (lý thuyết + bài tập)
   - Các từ khóa: "đề thi", "bài kiểm tra", "bài tập", "chương", "bài", "lý thuyết", "công thức", "định luật"

2. BUSINESS_DOC — nếu có MỘT trong các đặc điểm sau:
   - Hợp đồng, thỏa thuận (điều khoản, bên A/B, nghĩa vụ)
   - Hóa đơn, chứng từ (số tiền, ngày tháng, thuế, kỳ hạn)
   - Công văn, thông báo hành chính (số/ký hiệu, cơ quan, ngày ban hành)
   - Giấy tờ pháp lý (giấy phép, sổ đỏ, giấy khai sinh)
   - Các từ khóa: "hợp đồng", "thỏa thuận", "điều khoản", "hóa đơn", "thuế", "công ty", "cá nhân", "thời hạn", "nghĩa vụ"

3. GENERAL — nếu không rõ ràng

Chỉ trả về JSON (không markdown, không text khác):
{{
  "mode": "STUDY_MATERIAL|BUSINESS_DOC|GENERAL",
  "confidence": 0.0-1.0,
  "reason": "1-2 câu ngắn"
}}

Tài liệu:
---
{document_text}
---
"""


class ModeDetector:
    """Detect document mode using Gemini"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._configure_gemini()

    def _configure_gemini(self):
        """Configure Gemini with multi-key rotation"""
        _api_keys = [k for k in [
            config.GEMINI_API_KEY,
            getattr(config, "GEMINI_API_KEY_2", ""),
            getattr(config, "GEMINI_API_KEY_3", ""),
        ] if k]

        if _api_keys:
            genai.configure(api_key=_api_keys[0])
        else:
            genai.configure(api_key=config.GEMINI_API_KEY)

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API"""
        try:
            # Use gemini-2.5-flash (same as existing project)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await model.generate_content_async(prompt)
            return response.text.strip() if hasattr(response, 'text') else ""
        except Exception as e:
            self.logger.error(f"Gemini error: {e}")
            raise

    async def detect(self, text: str) -> Dict[str, Any]:
        """Detect mode from text"""
        if not text or len(text.strip()) < 10:
            return {"mode": "GENERAL", "confidence": 0.0, "reason": "Too short"}

        text_sample = text[:8000]
        prompt = DETECT_MODE_PROMPT.format(document_text=text_sample)

        try:
            response_text = await self._call_gemini(prompt)
            if not response_text:
                return {"mode": "GENERAL", "confidence": 0.0, "reason": "Empty response"}

            # Extract JSON from response
            json_str = response_text
            if "```" in response_text:
                lines = response_text.splitlines()
                in_code = False
                code_lines = []
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code = not in_code
                        continue
                    if in_code:
                        code_lines.append(line)
                if code_lines:
                    json_str = "\n".join(code_lines)

            start = json_str.find("{")
            end = json_str.rfind("}")
            if start >= 0 and end > start:
                json_str = json_str[start:end+1]

            result = json.loads(json_str)

            mode = result.get("mode", "GENERAL")
            confidence = float(result.get("confidence", 0.5))
            reason = result.get("reason", "Auto-detected")

            if mode not in ["STUDY_MATERIAL", "BUSINESS_DOC", "GENERAL"]:
                mode = "GENERAL"

            return {"mode": mode, "confidence": confidence, "reason": reason}

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON error: {e}, response: {response_text[:200]}")
            return {"mode": "GENERAL", "confidence": 0.0, "reason": f"JSON error: {e}"}
        except Exception as e:
            self.logger.error(f"Detection error: {e}", exc_info=True)
            return {"mode": "GENERAL", "confidence": 0.0, "reason": f"Error: {e}"}


async def detect_mode(text: str) -> Dict[str, Any]:
    """Convenience function"""
    detector = ModeDetector()
    return await detector.detect(text)

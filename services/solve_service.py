"""Solve problem from image: OCR + Step-by-step solution.

Pipeline:
1. Gemini Vision OCR: Extract text from image
2. DeepSeek V4 Flash: Generate step-by-step solution in Vietnamese
"""

import json
import logging
import os
import tempfile
import time
from typing import Dict, Any

from services.ai_summarizer import extract_ocr_text, _call_deepseek
from services.db_service import save_solved_problem
from prompts.study_prompts import SOLVE_PROBLEM_PROMPT

logger = logging.getLogger(__name__)


async def solve_problem_image(file_path: str, user_id: str) -> Dict[str, Any]:
    """
    Solve a problem from image using hybrid approach:
    - Gemini Vision 2.5 Flash for OCR
    - DeepSeek V4 Flash for step-by-step reasoning

    Args:
        file_path: Path to the image file
        user_id: User identifier for logging/analytics

    Returns:
        Dict with keys: question, steps (list), answer
    """
    # Stage 1: OCR with Gemini Vision 2.5 Flash
    logger.info("Stage 1: OCR with Gemini Vision for user %s", user_id)
    ocr_start = time.time()
    ocr_text = await extract_ocr_text(file_path)
    ocr_duration = time.time() - ocr_start

    if not ocr_text or ocr_text.startswith("("):
        logger.warning("OCR failed for user %s: %s", user_id, ocr_text)
        raise ValueError("Không đọc được đề bài từ ảnh. Hãy chụp rõ hơn.")

    logger.info("OCR extracted %d characters (%.2fs) for user %s", len(ocr_text), ocr_duration, user_id)

    # Stage 2: Generate solution with DeepSeek V4 Flash
    logger.info("Stage 2: DeepSeek V4 Flash generating solution for user %s", user_id)
    prompt = SOLVE_PROBLEM_PROMPT.format(question=ocr_text)

    try:
        gen_start = time.time()
        solution_text = await _call_deepseek(
            prompt=prompt,
            system_prompt="Bạn là giáo viên giỏi môn Toán/Lý/Hóa/Tiếng Anh. Giải bài tập từng bước rõ ràng.",
            max_tokens=2000,
            response_json=True,
        )
        gen_duration = time.time() - gen_start

        # Parse JSON response
        try:
            solution = json.loads(solution_text)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from DeepSeek: %s", solution_text[:200])
            raise ValueError("AI không trả về định dạng hợp lệ")

        # Validate required keys
        required_keys = ["question", "steps", "answer"]
        if not all(k in solution for k in required_keys):
            logger.error("Missing keys in solution: %s", solution.keys())
            raise ValueError("Thiếu thông tin trong lời giải")

        # Validate steps is a list
        if not isinstance(solution["steps"], list):
            raise ValueError("Steps phải là danh sách")

        # Limit steps to reasonable number (5-20)
        if len(solution["steps"]) > 20:
            solution["steps"] = solution["steps"][:20]
            logger.info("Trimmed steps to 20 for user %s", user_id)

        logger.info(
            "Solution generated successfully: question=%d chars, steps=%d",
            len(solution["question"]),
            len(solution["steps"])
        )

        # Save to database
        save_solved_problem(
            user_id=user_id,
            question=solution["question"],
            steps=solution["steps"],
            answer=solution["answer"],
            subject=None,  # TODO: detect subject from OCR
            difficulty=None,
            image_url=None  # TODO: upload image to S3 and get URL
        )

        total_duration = time.time() - ocr_start
        logger.info(
            "✅ Solve completed: OCR=%.2fs, Gen=%.2fs, Total=%.2fs, steps=%d, user=%s",
            ocr_duration, gen_duration, total_duration, len(solution["steps"]), user_id
        )

        return solution

    except Exception as e:
        logger.error("Solution generation failed for user %s: %s", user_id, e)
        raise

"""AI Summarizer using Google Gemini 2.5 Flash (free tier: 1500 req/day)."""

import logging
import google.generativeai as genai
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential
from config import config
from prompts import SYSTEM_PROMPT, PROMPTS, DETECT_TYPE_PROMPT

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=config.GEMINI_API_KEY)


def _get_model():
    """Get the Gemini model instance."""
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.3,  # Low creativity for accurate summaries
            max_output_tokens=16384,  # Tăng lên rất cao vì Gemini 2.5 Flash dùng thinking tokens
        )
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def detect_document_type(text: str) -> str:
    """Auto-detect document type from content preview."""
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                max_output_tokens=100,  # Chỉ cần 1 từ
            )
        )
        preview = text[:1000]  # First 1000 chars for classification
        prompt = DETECT_TYPE_PROMPT.format(content_preview=preview)

        response = model.generate_content(prompt)
        doc_type = response.text.strip().lower()

        valid_types = ["contract", "medical", "administrative", "education", "general"]
        if doc_type in valid_types:
            logger.info(f"Document type detected: {doc_type}")
            return doc_type
        else:
            logger.warning(f"Unknown doc type '{doc_type}', defaulting to 'general'")
            return "general"

    except Exception as e:
        logger.error(f"Document type detection failed: {e}")
        return "general"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def summarize_text(text: str, doc_type: str = None) -> str:
    """
    Summarize text content using Gemini.
    
    Args:
        text: Extracted text from document
        doc_type: Optional document type (auto-detected if None)
    
    Returns:
        Vietnamese summary in 5 key points
    """
    try:
        # Auto-detect document type if not provided
        if doc_type is None:
            doc_type = await detect_document_type(text)

        # Get the appropriate prompt template
        prompt_template = PROMPTS.get(doc_type, PROMPTS["general"])

        # Truncate text if too long (Gemini context limit)
        max_chars = 30000  # ~7500 tokens, well within limits
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... Tài liệu đã được cắt ngắn vì quá dài ...]"

        # Build the prompt
        prompt = prompt_template.format(content=text)

        # Generate summary
        model = _get_model()
        response = model.generate_content(prompt)

        summary = response.text.strip()
        logger.info(f"Summary generated: {len(summary)} chars, type={doc_type}")
        
        # Safety check: Nếu summary quá ngắn, thử lại 1 lần
        if len(summary) < 500:
            logger.warning(f"Summary too short ({len(summary)} chars), retrying...")
            response2 = model.generate_content(
                f"BẮT BUỘC viết thật dài, ÍT NHẤT 800 chữ. Viết đầy đủ 5 ý, mỗi ý 5-7 câu giải thích cặn kẽ.\n\n{prompt}"
            )
            summary2 = response2.text.strip()
            if len(summary2) > len(summary):
                summary = summary2
                logger.info(f"Retry summary: {len(summary)} chars")
        
        return summary

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return "❌ Xin lỗi, tôi không thể tóm tắt tài liệu này. Vui lòng thử lại sau."


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def summarize_image(image_path: str) -> str:
    """
    Summarize content from an image using Gemini's multimodal vision.
    Gemini reads the image directly — no separate OCR needed.
    """
    try:
        model = _get_model()

        # Load image
        image = Image.open(image_path)

        prompt = """Hãy đọc nội dung trong ảnh này và tóm tắt thành ĐÚNG 5 ý chính.
Mỗi ý viết 3-5 câu, giải thích đầy đủ chi tiết.

Nếu đây là đơn thuốc: giải thích từng loại thuốc, cách uống, và cảnh báo.
Nếu đây là hợp đồng: nêu điều khoản quan trọng nhất, số tiền, thời hạn.
Nếu đây là văn bản khác: tóm tắt nội dung chính.

Trích dẫn CỤ THỂ các con số, ngày tháng, tên riêng trong ảnh.
Viết bằng tiếng Việt đơn giản, dễ hiểu cho người lớn tuổi.
Tổng độ dài bắt buộc phải đạt ít nhất 800 chữ. Hãy mô tả cực kỳ chi tiết."""

        response = model.generate_content([prompt, image])

        summary = response.text.strip()
        logger.info(f"Image summary generated: {len(summary)} chars")
        return summary

    except Exception as e:
        logger.error(f"Image summarization failed: {e}")
        return "❌ Xin lỗi, tôi không thể đọc được nội dung trong ảnh. Vui lòng chụp ảnh rõ hơn và thử lại."

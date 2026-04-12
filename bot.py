"""
Telegram Bot — Trợ lý AI Tài liệu
Gửi file → nhận tóm tắt 5 ý chính + nghe giọng nói tiếng Việt

Flow: User gửi file → Parse document → AI summarize → TTS → Send back
v2.0: Document session management — nhớ file, hỏi lại, chọn file cũ
"""

import os
import logging
import time
import json

import uuid
from telegram.error import BadRequest
from services.db_service import (
    save_document, get_active_doc, get_active_doc_id,
    get_user_docs, check_rate_limit, increment_usage, set_active_doc
)

async def safe_send(func, text, **kwargs):
    try:
        return await func(text, **kwargs)
    except BadRequest as e:
        if "parse" in str(e).lower() or "entities" in str(e).lower():
            import logging
            logging.getLogger(__name__).warning(f"Markdown fallback: {e}")
            kwargs.pop("parse_mode", None)
            return await func(text, **kwargs)
        raise e

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from config import config
from services.document_parser import extract_text, get_file_type
from services.ai_summarizer import summarize_text, summarize_image
from services.tts_service import text_to_speech, cleanup_audio
from services.asr_service import speech_to_text

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Track daily usage per user (simple in-memory, replace with Supabase later)
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = """👋 **Xin chào! Tôi là Trợ lý AI Tài liệu.**

📄 Gửi cho tôi bất kỳ file nào:
• **PDF** — hợp đồng, văn bản, báo cáo
• **Word** (.docx) — tài liệu văn phòng  
• **Ảnh chụp** — đơn thuốc, hóa đơn, giấy tờ
• **Ghi âm** 🎤 — hỏi bằng giọng nói

🔮 Tôi sẽ:
1️⃣ Đọc và phân tích nội dung
2️⃣ Tóm tắt thành **5 ý chính** dễ hiểu
3️⃣ Đọc to bằng **giọng nói tiếng Việt** 🔊
4️⃣ **Nhớ tài liệu** của bạn để hỏi lại bất cứ lúc nào

⏱ Chỉ mất **30 giây** — nhanh hơn tự đọc!

📌 Gói miễn phí: **{limit} tài liệu/ngày**

**Lệnh hữu ích:**
/files — 📋 Xem danh sách file đã gửi
/remaining — 📊 Xem số lượt còn lại

Gửi file ngay để thử! 👇""".format(limit=config.FREE_DAILY_LIMIT)

    await safe_send(update.message.reply_text, welcome, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """📖 **Hướng dẫn sử dụng:**

**Cách 1 — Gửi file:**
Gửi file PDF hoặc Word trực tiếp vào chat

**Cách 2 — Gửi ảnh:**
Chụp ảnh tài liệu (đơn thuốc, hóa đơn...) rồi gửi

**Cách 3 — Ghi âm hỏi:**
Bấm giữ 🎤 để hỏi bất kỳ câu nào bằng giọng nói

**Sau khi nhận tóm tắt, bạn có thể:**
🔊 Bấm **Nghe giọng nói** — nghe bot đọc to
❓ Bấm **Hỏi thêm** — hỏi chi tiết về file
⚖️ Bấm **Phân tích chi tiết** — xem phân tích sâu
📋 Bấm **Danh sách file** — chọn file cũ để xem lại

**Hỏi thêm về file:**
Sau khi gửi file, gõ bất kỳ câu hỏi nào:
_"Điều khoản phạt trong hợp đồng này là gì?"_
_"Tóm lại tôi phải làm gì?"_
→ Bot sẽ trả lời dựa trên nội dung file bạn vừa gửi!

**Lệnh:**
/start — Bắt đầu
/help — Hướng dẫn
/files — Xem file đã gửi
/remaining — Xem số lượt còn lại hôm nay""".format(
        size=config.MAX_FILE_SIZE_MB,
        pages=config.MAX_PAGES,
        limit=config.FREE_DAILY_LIMIT,
    )

    await safe_send(update.message.reply_text, help_text, parse_mode="Markdown")


async def cmd_remaining(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check remaining daily usage."""
    user_id = update.effective_user.id
    today = time.strftime("%Y-%m-%d")

    used = 0
    if user_id in user_daily_usage and user_daily_usage[user_id]["date"] == today:
        used = user_daily_usage[user_id]["count"]

    remaining = config.FREE_DAILY_LIMIT - used
    await safe_send(update.message.reply_text, 
        f"📊 Hôm nay bạn đã dùng **{used}/{config.FREE_DAILY_LIMIT}** lượt.\n"
        f"Còn lại: **{remaining}** lượt miễn phí.",
        parse_mode="Markdown",
    )


async def cmd_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all documents in user's session."""
    user_id = update.effective_user.id
    docs = get_user_docs(user_id)

    if not docs:
        await safe_send(update.message.reply_text, 
            "📋 Bạn chưa gửi file nào.\n"
            "Gửi file PDF, Word, hoặc ảnh để bắt đầu!"
        )
        return

    active_id = get_active_doc_id(user_id) or ""
    text = f"📋 **Tài liệu của bạn** ({len(docs)} file):\n\n"

    for i, doc in enumerate(docs):
        icon = "📌" if doc["id"] == active_id else f"{i+1}."
        label = " ← đang chọn" if doc["id"] == active_id else ""
        text += f"{icon} **{doc['name']}**{label}\n"

    text += "\n👇 Bấm vào file để chọn và tương tác:"

    await safe_send(update.message.reply_text, 
        text,
        parse_mode="Markdown",
        reply_markup=make_docs_list_keyboard(user_id),
    )


# ===== CALLBACK QUERY HANDLER (Inline Buttons) =====

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # --- LIST DOCS ---
    if data == "list_docs":
        docs = get_user_docs(user_id)
        if not docs:
            await safe_send(query.edit_message_text, "📋 Chưa có file nào.")
            return

        active_id = get_active_doc_id(user_id) or ""
        text = f"📋 **Tài liệu của bạn** ({len(docs)} file):\n\n"
        for i, doc in enumerate(docs):
            icon = "📌" if doc["id"] == active_id else f"{i+1}."
            label = " ← đang chọn" if doc["id"] == active_id else ""
            text += f"{icon} **{doc['name']}**{label}\n"
        text += "\n👇 Bấm vào file để chọn:"

        await safe_send(query.edit_message_text, 
            text,
            parse_mode="Markdown",
            reply_markup=make_docs_list_keyboard(user_id),
        )
        return

    # Parse action|doc_id
    parts = data.split("|", 1)
    if len(parts) != 2:
        return

    action, doc_id = parts

    # --- SELECT DOC ---
    if action == "select":
        docs = get_user_docs(user_id)
        doc = next((d for d in docs if d["id"] == doc_id), None)
        if not doc:
            await safe_send(query.edit_message_text, "❌ File này đã hết hạn. Gửi lại nhé!")
            return

        set_active_doc(user_id, doc_id)

        await safe_send(query.edit_message_text, 
            f"📌 **Đã chọn:** _{doc['name']}_\n\n"
            f"{doc['summary']}\n\n"
            "👇 Bạn muốn làm gì với file này?",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(doc_id),
        )
        return

    # Get the document
    docs = get_user_docs(user_id)
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        await safe_send(query.edit_message_text, "❌ File này đã hết hạn. Gửi lại nhé!")
        return

    set_active_doc(user_id, doc_id)  # Auto-select khi tương tác

    # --- TTS ---
    if action == "tts":
        await safe_send(query.edit_message_text, 
            f"🔊 Đang tạo giọng nói cho **{doc['name']}**...",
            parse_mode="Markdown",
        )

        if config.FPT_AI_API_KEY:
            clean = doc["summary"].replace("**", "").replace("*", "")
            clean = clean.replace("⚠️", "Luu y: ").replace("📌", "")
            clean = clean.replace("❌", "").replace("✅", "")

            audio_path = await text_to_speech(clean)
            if audio_path:
                await context.bot.send_voice(
                    chat_id=query.message.chat_id,
                    voice=open(audio_path, "rb"),
                    caption=f"🔊 Nghe tóm tắt: {doc['name']}",
                )
                await cleanup_audio(audio_path)

                # Restore original message with buttons
                await safe_send(query.edit_message_text, 
                    f"📋 **{doc['name']}**\n\n{doc['summary']}",
                    parse_mode="Markdown",
                    reply_markup=make_doc_keyboard(doc_id),
                )
            else:
                await safe_send(query.edit_message_text, 
                    "❌ Lỗi tạo giọng nói. Thử lại sau!",
                    reply_markup=make_doc_keyboard(doc_id),
                )
        else:
            await safe_send(query.edit_message_text, 
                "❌ Chưa cài đặt giọng nói. Liên hệ admin!",
                reply_markup=make_doc_keyboard(doc_id),
            )
        return

    # --- ASK (Hỏi thêm) ---
    if action == "ask":
        await safe_send(query.edit_message_text, 
            f"❓ **Đang chọn:** _{doc['name']}_\n\n"
            "Gõ câu hỏi bất kỳ về tài liệu này:\n"
            "_Ví dụ: \"Điều khoản phạt là gì?\", \"Tóm lại tôi phải làm gì?\"_\n\n"
            "Hoặc bấm 🎤 ghi âm câu hỏi bằng giọng nói!",
            parse_mode="Markdown",
        )
        return

    # --- DETAIL (Phân tích chi tiết) ---
    if action == "detail":
        await safe_send(query.edit_message_text, 
            f"⚖️ Đang phân tích chi tiết **{doc['name']}**...\n"
            "Vui lòng đợi 15-30 giây.",
            parse_mode="Markdown",
        )

        detail_prompt = (
            f"Hãy phân tích CHI TIẾT tài liệu sau. Đừng tóm tắt, hãy đi sâu vào:\n"
            f"1. Các điều khoản/thông tin QUAN TRỌNG NHẤT\n"
            f"2. Các điểm CẦN LƯU Ý hoặc RỦI RO\n"
            f"3. Các con số, ngày tháng, mốc thời gian quan trọng\n"
            f"4. Những gì người đọc CẦN LÀM sau khi đọc\n"
            f"5. Đánh giá tổng thể: tài liệu này có lợi hay bất lợi cho người nhận?\n\n"
            f"Tài liệu:\n{doc['text']}"
        )

        detail = await summarize_text(detail_prompt)

        await safe_send(query.edit_message_text, 
            f"⚖️ **Phân tích chi tiết:** _{doc['name']}_\n\n{detail}",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(doc_id),
        )
        return


# ===== FILE HANDLER =====

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document files (PDF, Word)."""
    user_id = update.effective_user.id

    # Rate limit check
    if not check_rate_limit(user_id):
        await safe_send(update.message.reply_text, 
            f"⚠️ Bạn đã dùng hết **{config.FREE_DAILY_LIMIT} lượt** miễn phí hôm nay.\n"
            "Quay lại ngày mai nhé! 🙏",
            parse_mode="Markdown",
        )
        return

    document = update.message.document

    # Check file size
    if document.file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await safe_send(update.message.reply_text, 
            f"❌ File quá lớn! Tối đa {config.MAX_FILE_SIZE_MB}MB."
        )
        return

    # Check file type
    file_name = document.file_name or "document"
    file_type = get_file_type(file_name)

    if file_type == "unknown":
        await safe_send(update.message.reply_text, 
            "❌ Tôi chỉ hỗ trợ file **PDF**, **Word (.docx)**, hoặc **ảnh**.\n"
            "Vui lòng gửi đúng định dạng!",
            parse_mode="Markdown",
        )
        return

    # Send processing message
    processing_msg = await safe_send(update.message.reply_text, 
        "⏳ Đang xử lý tài liệu của bạn... Vui lòng đợi khoảng 15-30 giây."
    )

    start_time = time.time()
    file_path = os.path.join(config.TEMP_DIR, f"{uuid.uuid4().hex}_{file_name}")

    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        await file.download_to_drive(file_path)

        logger.info(f"File downloaded: {file_name} ({document.file_size} bytes)")

        # Extract text
        text, ftype = await extract_text(file_path, config.MAX_PAGES)

        if not text:
            await safe_send(processing_msg.edit_text, 
                "❌ Không thể đọc được nội dung file này.\n"
                "File có thể bị mã hóa hoặc không chứa text.\n"
                "Thử chụp ảnh tài liệu và gửi ảnh cho tôi!"
            )
            return

        # AI Summarize
        summary = await summarize_text(text)

        elapsed = time.time() - start_time
        logger.info(f"Summary ready in {elapsed:.1f}s")

        # Lưu tài liệu vào session
        doc_id = f"doc_{int(time.time())}_{user_id}"
        save_document(user_id, doc_id, file_name, text, summary, "file")

        # Send summary VỚI NÚT BẤM
        await safe_send(processing_msg.edit_text, 
            f"📋 **Tóm tắt tài liệu:** _{file_name}_\n"
            f"⏱ Xử lý trong {elapsed:.0f} giây\n\n"
            f"{summary}\n\n"
            "👇 Bạn muốn làm gì tiếp?",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(doc_id),
        )

        # Increment usage
        increment_usage(user_id)

    except Exception as e:
        logger.error(f"Document processing error: {e}", exc_info=True)
        await safe_send(processing_msg.edit_text, 
            "❌ Đã xảy ra lỗi khi xử lý tài liệu. Vui lòng thử lại!"
        )

    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)


# ===== PHOTO HANDLER =====

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos (OCR + summarize using Gemini vision)."""
    user_id = update.effective_user.id

    if not check_rate_limit(user_id):
        await safe_send(update.message.reply_text, 
            f"⚠️ Bạn đã dùng hết **{config.FREE_DAILY_LIMIT} lượt** miễn phí hôm nay.\n"
            "Quay lại ngày mai nhé! 🙏",
            parse_mode="Markdown",
        )
        return

    processing_msg = await safe_send(update.message.reply_text, 
        "⏳ Đang đọc nội dung ảnh... Vui lòng đợi khoảng 15-30 giây."
    )

    start_time = time.time()
    image_path = None

    try:
        # Get highest resolution photo
        photo = update.message.photo[-1]  # Last = highest res
        file = await context.bot.get_file(photo.file_id)

        image_path = os.path.join(config.TEMP_DIR, f"{photo.file_id}.jpg")
        await file.download_to_drive(image_path)

        logger.info(f"Photo downloaded: {image_path}")

        # Summarize image directly with Gemini vision (no separate OCR needed!)
        summary = await summarize_image(image_path)

        elapsed = time.time() - start_time
        logger.info(f"Image summary ready in {elapsed:.1f}s")

        # Lưu vào session (ảnh thì text = summary vì không extract riêng được)
        doc_id = f"img_{int(time.time())}_{user_id}"
        photo_name = f"Ảnh chụp {time.strftime('%H:%M')}"
        save_document(user_id, doc_id, photo_name, summary, summary, "photo")

        # Send summary VỚI NÚT BẤM
        await safe_send(processing_msg.edit_text, 
            f"📷 **Tóm tắt từ ảnh chụp:**\n"
            f"⏱ Xử lý trong {elapsed:.0f} giây\n\n"
            f"{summary}\n\n"
            "👇 Bạn muốn làm gì tiếp?",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(doc_id),
        )

        increment_usage(user_id)

    except Exception as e:
        logger.error(f"Photo processing error: {e}", exc_info=True)
        await safe_send(processing_msg.edit_text, 
            "❌ Không đọc được ảnh. Vui lòng chụp ảnh rõ hơn và thử lại!"
        )

    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)


# ===== TEXT MESSAGE HANDLER (Context-aware) =====

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages — context-aware with active document."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if len(text) < 5:
        await safe_send(update.message.reply_text, 
            "👋 Gửi cho tôi file **PDF**, **Word**, hoặc **ảnh chụp** tài liệu.\n"
            "Tôi sẽ tóm tắt thành 5 ý chính và đọc to cho bạn nghe! 🔊\n\n"
            "Gõ /help để xem hướng dẫn.",
            parse_mode="Markdown",
        )
        return

    # Kiểm tra xem user có tài liệu đang active không
    active_doc = get_active_doc(user_id)

    if active_doc:
        # User đang hỏi VỀ tài liệu đã gửi trước đó
        processing_msg = await safe_send(update.message.reply_text, 
            f"⏳ Đang tìm câu trả lời trong **{active_doc['name']}**...",
            parse_mode="Markdown",
        )

        qa_prompt = (
            f"Người dùng đã gửi tài liệu có tên '{active_doc['name']}'.\n\n"
            f"NỘI DUNG TÀI LIỆU:\n{active_doc['text']}\n\n"
            f"TÓM TẮT TRƯỚC ĐÓ:\n{active_doc['summary']}\n\n"
            f"CÂU HỎI CỦA NGƯỜI DÙNG: {text}\n\n"
            f"Hãy trả lời dựa trên nội dung tài liệu. "
            f"Nếu câu hỏi không liên quan đến tài liệu, hãy nói rõ. "
            f"Trả lời ngắn gọn, dễ hiểu, phù hợp người lớn tuổi."
        )

        answer = await summarize_text(qa_prompt)

        await safe_send(processing_msg.edit_text, 
            f"📌 **Trả lời về:** _{active_doc['name']}_\n\n"
            f"**Câu hỏi:** {text}\n\n"
            f"{answer}",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(active_doc["id"]),
        )

        # TTS cho câu trả lời
        if config.FPT_AI_API_KEY:
            clean = answer.replace("**", "").replace("*", "")
            audio_path = await text_to_speech(clean)
            if audio_path:
                await update.message.reply_voice(
                    voice=open(audio_path, "rb"),
                    caption="🔊 Nghe câu trả lời",
                )
                await cleanup_audio(audio_path)

    elif len(text) > 100:
        # Không có file active, text dài → tóm tắt như cũ
        if not check_rate_limit(user_id):
            await safe_send(update.message.reply_text, 
                f"⚠️ Hết lượt miễn phí hôm nay. Quay lại ngày mai nhé!"
            )
            return

        processing_msg = await safe_send(update.message.reply_text, "⏳ Đang tóm tắt...")

        summary = await summarize_text(text)

        # Lưu vào session
        doc_id = f"txt_{int(time.time())}_{user_id}"
        save_document(user_id, doc_id, "Văn bản dán vào", text, summary, "text")

        await safe_send(processing_msg.edit_text, 
            f"📝 **Tóm tắt văn bản:**\n\n{summary}",
            parse_mode="Markdown",
            reply_markup=make_doc_keyboard(doc_id),
        )

        increment_usage(user_id)

        # TTS
        if config.FPT_AI_API_KEY:
            clean_text = summary.replace("**", "").replace("*", "")
            audio_path = await text_to_speech(clean_text)
            if audio_path:
                await update.message.reply_voice(
                    voice=open(audio_path, "rb"),
                    caption="🔊 Nghe tóm tắt",
                )
                await cleanup_audio(audio_path)
    else:
        await safe_send(update.message.reply_text, 
            "📄 Gửi file hoặc ảnh tài liệu cho tôi để được tóm tắt!\n"
            "Hoặc gõ /files để xem lại file đã gửi trước đó.",
        )


# ===== VOICE HANDLER =====

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages (speech-to-text) — context-aware."""
    user_id = update.effective_user.id

    if not check_rate_limit(user_id):
        await safe_send(update.message.reply_text, 
            f"⚠️ Bạn đã dùng hết **{config.FREE_DAILY_LIMIT} lượt** miễn phí hôm nay.\n"
            "Quay lại ngày mai nhé! 🙏",
            parse_mode="Markdown",
        )
        return

    processing_msg = await safe_send(update.message.reply_text, "⏳ Đang nghe và phiên dịch...")

    voice_file = await context.bot.get_file(update.message.voice.file_id)
    audio_path = os.path.join(config.TEMP_DIR, f"{update.message.voice.file_id}.ogg")

    try:
        await voice_file.download_to_drive(audio_path)
        logger.info(f"Voice downloaded: {audio_path}")

        # Gọi ASR (Từ FPT.AI)
        transcription = await speech_to_text(audio_path)

        if not transcription:
            await safe_send(processing_msg.edit_text, "❌ Xin lỗi, tôi nghe không rõ. Bạn thu âm lại giúp nhé!")
            return

        # Kiểm tra có tài liệu active không
        active_doc = get_active_doc(user_id)

        if active_doc:
            # Hỏi VỀ tài liệu đang chọn
            await safe_send(processing_msg.edit_text, 
                f"🎤 **Bạn hỏi:** _{transcription}_\n"
                f"📌 **Về file:** _{active_doc['name']}_\n\n"
                "⏳ Đang tìm câu trả lời...",
                parse_mode="Markdown",
            )

            qa_prompt = (
                f"Người dùng đã gửi tài liệu '{active_doc['name']}'.\n\n"
                f"NỘI DUNG: {active_doc['text']}\n\n"
                f"Họ vừa hỏi bằng giọng nói: '{transcription}'\n\n"
                f"Trả lời ngắn gọn, dễ hiểu, dựa trên tài liệu."
            )
            answer = await summarize_text(qa_prompt)

            await safe_send(processing_msg.edit_text, 
                f"🎤 **Bạn hỏi:** _{transcription}_\n"
                f"📌 **Về:** _{active_doc['name']}_\n\n"
                f"🤖 **Trả lời:**\n{answer}",
                parse_mode="Markdown",
                reply_markup=make_doc_keyboard(active_doc["id"]),
            )
        else:
            # Không có file → trả lời chung
            await safe_send(processing_msg.edit_text, 
                f"🎤 **Bạn nói:** _{transcription}_\n\n⏳ Đang suy nghĩ...",
                parse_mode="Markdown",
            )

            prompt = f"Người dùng hỏi: '{transcription}'. Trả lời ngắn gọn, dễ hiểu."
            answer = await summarize_text(prompt)

            await safe_send(processing_msg.edit_text, 
                f"🎤 **Bạn hỏi:** _{transcription}_\n\n🤖 **Trả lời:**\n{answer}",
                parse_mode="Markdown",
            )

        increment_usage(user_id)

        # TTS
        if config.FPT_AI_API_KEY:
            clean = answer.replace("**", "").replace("*", "")
            tts_path = await text_to_speech(clean)
            if tts_path:
                await update.message.reply_voice(
                    voice=open(tts_path, "rb"),
                    caption="🔊 Nghe câu trả lời",
                )
                await cleanup_audio(tts_path)

    except Exception as e:
        logger.error(f"Voice error: {e}", exc_info=True)
        await safe_send(processing_msg.edit_text, "❌ Lỗi xử lý âm thanh. Bạn thu âm lại nhé!")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


# ===== MAIN =====

def main():
    """Start the Telegram bot."""
    if not config.TELEGRAM_BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN is not set!")
        print("1. Go to Telegram, search @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the token to .env file")
        return

    if not config.GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY is not set!")
        print("1. Go to https://aistudio.google.com/apikey")
        print("2. Create a new API key")
        print("3. Copy the key to .env file")
        return

    print("=" * 50)
    print("[BOT] Tro ly AI Tai lieu - Telegram Bot v2.0")
    print("=" * 50)
    print(f"[*] Free limit: {config.FREE_DAILY_LIMIT} docs/day")
    print(f"[*] Max file: {config.MAX_FILE_SIZE_MB}MB")
    print(f"[*] Max pages: {config.MAX_PAGES}")
    print(f"[*] TTS voice: {config.FPT_AI_VOICE}")
    print(f"[*] TTS enabled: {'YES' if config.FPT_AI_API_KEY else 'NO (no FPT key)'}")
    print(f"[*] Doc memory: {MAX_DOCS_PER_USER} files/user")
    print("=" * 50)
    print("Bot is running! Press Ctrl+C to stop.")
    print()

    # Build the application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("remaining", cmd_remaining))
    app.add_handler(CommandHandler("files", cmd_files))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

# 🔀 Implementation Plan: Hybrid AI Model (DeepSeek V4 Flash + Gemini 2.5 Flash)

## 📊 Phân tích đột phá

**Mục tiêu**: Giảm **60-80% chi phí AI** mà không giảm chất lượng, nhờ routing thông minh:
- **DeepSeek V4 Flash** (text-only): Output $0.28/1M vs Gemini $2.50/1M → **rẻ hơn 9x**
- **Gemini 2.5 Flash** (vision-only): Duy nhất có OCR/vision capability

**Tại sao đây là giải pháp đột phá**:
- **Zero UX change**: User không thấy gì khác — hoàn toàn internal routing
- **Instant cost savings**: Bill giảm 60-80% ngay từ tháng đầu
- **Graceful fallback**: DeepSeek fail → tự động chuyển Gemini → zero downtime
- **Zero new dependency**: Dùng `httpx` có sẵn, không cần SDK mới
- **Cache hit siêu rẻ**: DeepSeek cache hit chỉ $0.0028/1M → nếu nhiều user đọc cùng PDF, gần như miễn phí

**Rủi ro cần quản lý**:
- DeepSeek V4 Flash là model mới (Mar 2025) → cần monitor throughput & rate limit
- Output JSON quality có thể khác nhau giữa 2 model → cần test parsing robustness
- Latency: DeepSeek có thể chậm hơn Gemini (cần đo thực tế)
- Nếu DeepSeek API down toàn bộ, fallback per-request tăng latency → cần circuit breaker pattern (optional)

---

## 🏗️ Kiến trúc (Data Flow)

```
┌─────────────────────────────────────────────────────┐
│          User Request (PDF/Word/Image/Text)        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │  AiSummarizer service   │
        └─────────┬───────────────┘
                  │
                  ▼
        ┌─────────────────────────────────┐
        │  _call_with_smart_routing()    │
        │  - Nếu ảnh/PDF scan: force_gemini=True │
        │  - Nếu text: thử DeepSeek     │
        │  - Fallback nếu lỗi           │
        └─────────┬─────────────────────┘
                  │
       ┌──────────┴──────────┐
       ▼                      ▼
┌──────────────┐    ┌──────────────────┐
│ DeepSeek API │    │ Gemini API       │
│ (text-only)  │    │ (vision/text)    │
└──────┬───────┘    └────────┬─────────┘
       │                     │
       └──────────┬──────────┘
                  ▼
        ┌─────────────────────┐
        │   Parse JSON result │
        │   Return to user    │
        └─────────────────────┘
```

---

## 📝 Chi tiết thay đổi (File-by-File)

### 1. [MODIFY] `config.py`

**Vị trí**: Thêm sau line Gemini config (khoảng line 12-15)

**Thay đổi**:
```python
# DeepSeek AI (hybrid — dùng cho text tasks, rẻ hơn 9x)
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
DEEPSEEK_MODEL: str = "deepseek-v4-flash"
```

**Không thay đổi logic exist**.

---

### 2. [MODIFY] `.env.example`

**Vị trí**: Thêm section mới

**Thay đổi**:
```diff
+# DeepSeek AI (hybrid — dùng cho text tasks, rẻ hơn 9x)
+DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 3. [NEW FUNCTION] `services/ai_summarizer.py` — Thêm `_call_deepseek()`

**Vị trí**: Thêm sau `_call_gemini_with_fallback()` (khoảng line 250-260)

**Nội dung**:
```python
async def _call_deepseek(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    max_tokens: int = 8192,
    response_json: bool = True,
) -> str:
    """Gọi DeepSeek V4 Flash API (OpenAI-compatible format)."""
    
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    body = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    
    if response_json:
        body["response_format"] = {"type": "json_object"}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{config.DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
```

**Lưu ý**:
- DeepSeek dùng OpenAI-compatible format → không cần SDK mới
- Timeout 60s (Gemini là 30s) vì DeepSeek có thể slower
- Max tokens 8192 (có thể tùy chỉnh theo nhu cầu)

---

### 4. [NEW FUNCTION] `services/ai_summarizer.py` — Thêm `_call_with_smart_routing()`

**Vị trí**: Thêm sau `_call_deepseek()` (khoảng line 270-290)

**Nội dung**:
```python
async def _call_with_smart_routing(
    content: Union[str, List[Any]],
    text_length: int = 0,
    max_tokens: int = 8192,
    response_json: bool = True,
    force_gemini: bool = False,
) -> str:
    """
    Smart routing:
    - Nếu CÓ DeepSeek key VÀ KHÔNG force_gemini → thử DeepSeek trước
    - Nếu DeepSeek lỗi → fallback Gemini
    - Nếu KHÔNG có DeepSeek key → dùng Gemini luôn
    """
    
    # ── Route 1: DeepSeek (text-only) ──
    if config.DEEPSEEK_API_KEY and not force_gemini:
        # Chỉ dùng DeepSeek nếu content là string (text-only)
        if isinstance(content, str):
            try:
                result = await _call_deepseek(
                    prompt=content,
                    max_tokens=max_tokens,
                    response_json=response_json,
                )
                logger.info(
                    "✅ DeepSeek V4 Flash success: %s chars, cost ~$0.00014/1K tokens",
                    len(result)
                )
                return result
            except Exception as exc:
                logger.warning(
                    "⚠️ DeepSeek failed (fallback to Gemini): %s",
                    exc
                )
    
    # ── Route 2: Gemini (fallback OR vision) ──
    logger.info("Using Gemini (fallback or vision required)")
    return await _call_gemini_with_fallback(
        content, text_length, max_tokens, response_json
    )
```

---

### 5. [MODIFY] `services/ai_summarizer.py` — Cập nhật các hàm public

**Danh sách hàm cần sửa**:

| Hàm | Loại | force_gemini | Hành động |
|-----|------|--------------|-----------|
| `summarize_text_structured()` | Text | `False` | Đổi `_call_gemini_with_fallback` → `_call_with_smart_routing` |
| `answer_question_about_document()` | Text Q&A | `False` | Tương tự |
| `summarize_image_structured()` | Ảnh | `True` | Giữ nguyên (cần Vision) |
| `summarize_pdf_images_structured()` | Ảnh PDF scan | `True` | Giữ nguyên |
| `extract_ocr_text()` | OCR | `True` | Giữ nguyên |

**Ví dụ sửa `summarize_text_structured()`**:

```python
async def summarize_text_structured(
    text: str,
    max_tokens: int = 8192,
    response_json: bool = True,
) -> str:
    """Tóm tắt văn bản từ text."""
    
    # ... existing code (prompt generation) ...
    
    # Gọi AI với smart routing
    response_text = await _call_with_smart_routing(
        prompt,
        text_length=len(text),
        max_tokens=max_tokens,
        response_json=response_json,
        force_gemini=False,  # optional, default = False
    )
    
    # ... existing code (parse JSON) ...
```

**Các hàm xử lý ảnh giữ nguyên `_call_gemini_with_fallback()`** vì `force_gemini=True` bắt buộc dùng Gemini (có Vision).

---

### 6. [OPTIONAL] Thêm metrics logging

**Nếu có monitoring system** (Prometheus, Datadog), có thể thêm counters:

```python
# Global variables hoặc class attributes
deepseek_requests = 0
gemini_fallbacks = 0

# Trong _call_with_smart_routing():
if config.DEEPSEEK_API_KEY and not force_gemini:
    if isinstance(content, str):
        result = await _call_deepseek(...)
        deepseek_requests += 1
        return result
...
gemini_fallbacks += 1
```

**Optional** — có thể bỏ qua nếu chưa cần.

---

## 🧪 Test plan

### Test 1: DeepSeek routing (text-only)
```python
result = await summarizer.summarize_text_structured("Hello world test")
# Expect: DeepSeek được gọi (kiểm tra log)
```

### Test 2: Gemini fallback (no DeepSeek key)
```bash
unset DEEPSEEK_API_KEY
result = await summarizer.summarize_text_structured("Test")
# Expect: Gemini được gọi, không lỗi
```

### Test 3: Vision routing (Ảnh)
```python
result = await summarizer.summarize_image_structured(image_bytes)
# Expect: Gemini được gọi (force_gemini=True)
```

### Test 4: DeepSeek failure fallback
```python
# Set invalid DeepSeek key hoặc mock exception
# Expect: Tự động chuyển Gemini, không throw error
```

### Test 5: JSON parsing
```python
# Test cả DeepSeek và Gemini output đều parse được JSON đúng format
```

---

## ⏱️ Ước tính effort

| Task | Thời gian |
|------|-----------|
| Đọc codebase hiện tại | 15 phút |
| Implement `_call_deepseek()` | 20 phút |
| Implement `_call_with_smart_routing()` | 20 phút |
| Cập nhật 4 hàm public | 20 phút |
| Test local (5 scenarios) | 25 phút |
| Code review + fix edge cases | 20 phút |
| **Tổng** | **~2 giờ** |

---

## ❓ Câu hỏi mở

1. **Bạn có muốn thêm metrics counter (deepseek_requests, gemini_fallbacks) không?**
   - Nếu có → tôi thêm vào code
   - Nếu không → logging đủ để debug

2. **Timeout cho DeepSeek**: Tôi set 60s. Bạn có muốn điều chỉnh không? (Gemini hiện tại 30s)

3. **DeepSeek cache monitoring**: Bạn có muốn log thêm `x-ds-cache-hit` header không?
   - DeepSeek trả về header `x-ds-cache-hit: true/false`
   - Log để track cost optimization

4. **Circuit breaker**: Nếu DeepSeek down nhiều, có muốn thêm cache flag "deepseek_enabled=False" trong memory để tránh retry mỗi request không?
   - Optional: giảm latency khi DeepSeek outage

---

## ⚠️ Pre-flight checklist

- [ ] Bạn đã có DeepSeek API key (https://platform.deepseek.com)?
- [ ] Bạn đã backup code (git commit)?
- [ ] Bạn đã review và approve plan này?
- [ ] Bạn chấp nhận rủi ro model mới (có thể unstable, rate limit)?

---

## 🚀 Next steps (Sau khi approve)

1. **Tạo/update files** theo section 3
2. **Code** với tracking `task.md`
3. **Test** local với mock API keys
4. **Commit** changes
5. **Bạn cung cấp DeepSeek API key** → config `.env`
6. **Deploy** và monitor logs (deepseek_success vs fallback ratio)

---

**Kế hoạch đã sẵn sàng. Bạn Approve để tôi vào Pha 2: Implementation?**

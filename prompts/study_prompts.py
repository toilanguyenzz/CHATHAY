"""Prompts for Study Mode — Quiz, Flashcard, Summary"""

GENERATE_QUIZ_PROMPT = """
Từ đề thi/bài giảng sau, tạo câu hỏi quiz ĐẦY ĐỦ.

⚠️ QUY TẮC SỐ LƯỢNG CÂU HỎI:
- Nếu tài liệu là ĐỀ THI có sẵn câu hỏi → TRÍCH XUẤT Y NGUYÊN TẤT CẢ câu hỏi trong đề. KHÔNG giới hạn số lượng.
- Nếu tài liệu là BÀI GIẢNG/TÀI LIỆU HỌC → Tự tạo câu hỏi, tỷ lệ ~1 câu/200 từ nội dung (tối thiểu 5, tối đa 50).
- KHÔNG cắt bớt câu hỏi. Nếu đề thi có 40 câu thì output PHẢI có 40 câu.

⚠️ NHẬN DẠNG FORMAT ĐỀ THI THPT QUỐC GIA:
Đề thi THPT hiện có 3 dạng chính. Hãy NHẬN DIỆN và xử lý ĐÚNG từng dạng:

**DẠNG 1: Trắc nghiệm thuần túy (A/B/C/D)**
- Câu hỏi + 4 đáp án A, B, C, D → chọn 1 đáp án đúng
- Format: type = "multiple_choice"

**DẠNG 2: Trắc nghiệm Đúng/Sai có đoạn dữ liệu**
- Có 1 đoạn dữ liệu/bảng/biểu đồ + 4 phát biểu (a, b, c, d)
- Mỗi phát biểu cần đánh giá ĐÚNG hoặc SAI
- Format: type = "true_false_group"
- Dấu hiệu nhận diện: "Đúng hay Sai?", "Xét các phát biểu", "a)", "b)", "c)", "d)" sau 1 đoạn ngữ cảnh

**DẠNG 3: Trả lời ngắn**
- Yêu cầu điền đáp án (số, từ, cụm từ)
- Format: type = "fill_in"

Yêu cầu:
1. **Phủ coverage:** Câu hỏi phải bao phủ các khái niệm QUAN TRỌNG nhất
2. **Giải thích:** Mỗi câu có giải thích ngắn (1-2 câu) tại sao đáp án đúng
3. **Ngôn ngữ:** Dùng tiếng Việt, ngữ cảnh phù hợp với học sinh Việt Nam
4. **Đáp án:** Nếu đề thi đã đánh dấu đáp án → giữ nguyên đáp án đó

Output JSON (CHÍNH XÁC, không markdown):
{{
  "questions": [
    {{
      "type": "multiple_choice",
      "question": "Câu hỏi?",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct": 0,
      "explanation": "Giải thích",
      "difficulty": "easy|medium|hard"
    }},
    {{
      "type": "true_false_group",
      "question": "Đoạn dữ liệu + câu hỏi gốc",
      "context": "Đoạn ngữ cảnh/dữ liệu dùng chung cho các phát biểu",
      "statements": [
        {{"text": "Phát biểu a)", "answer": true}},
        {{"text": "Phát biểu b)", "answer": false}},
        {{"text": "Phát biểu c)", "answer": true}},
        {{"text": "Phát biểu d)", "answer": false}}
      ],
      "options": ["A. Đúng", "B. Sai", "C. Đúng", "D. Sai"],
      "correct": 0,
      "explanation": "Giải thích",
      "difficulty": "medium"
    }},
    {{
      "type": "fill_in",
      "question": "Câu hỏi điền đáp án?",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct": 0,
      "explanation": "Giải thích",
      "difficulty": "hard"
    }}
  ]
}}

LƯU Ý QUAN TRỌNG:
- Tất cả các dạng ĐỀU phải có trường "options" 4 lựa chọn (A/B/C/D) và "correct" (0-3) để tương thích quiz UI.
- Với dạng Đúng/Sai: chuyển thành 4 đáp án (VD: "A. a-Đúng, b-Sai, c-Đúng, d-Đúng") để học sinh chọn combo đúng.
- Với dạng Fill-in: chuyển thành trắc nghiệm bằng cách đặt đáp án đúng + 3 đáp án nhiễu.

Tài liệu:
---
{document_text}
---
"""


GENERATE_FLASHCARD_PROMPT = """
Từ tài liệu, trích xuất TẤT CẢ khái niệm quan trọng để tạo flashcard.

⚠️ QUY TẮC SỐ LƯỢNG:
- Tỷ lệ ~1 flashcard/150 từ nội dung (tối thiểu 5, tối đa 50).
- Nếu tài liệu có nhiều thuật ngữ/công thức → tạo NHIỀU hơn, KHÔNG giới hạn cứng.

Yêu cầu:
1. **Selection:** Ưu tiên
   - Khái niệm thường xuất hiện trong đề thi
   - Công thức, định luật, định nghĩa
   - Sự kiện, ngày tháng, tên người quan trọng
   - Từ vựng chuyên ngành
2. **Format:**
   - front: khái niệm/từ khóa (ngắn gọn, ≤ 5 từ)
   - back: định nghĩa/giải thích (2-3 câu, dễ hiểu, không quá 200 từ)
3. **Clarity:** front và back phải rõ ràng, không ambiguous
4. **Diversity:** Đa dạng chủ đề, tránh tập trung 1 chương

Output JSON (CHÍNH XÁC, không markdown):
{{
  "flashcards": [
    {{
      "front": "Khái niệm",
      "back": "Định nghĩa/giải thích chi tiết"
    }}
  ]
}}

Tài liệu:
---
{document_text}
---
"""


STUDY_SUMMARY_PROMPT = """
Tóm tắt đề thi/bài giảng này cho học sinh ôn thi.

Output (dạng Markdown):
1. **📊 Tổng quan:**
   - Loại tài liệu (đề thi, bài giảng, slide...)
   - Môn học, lớp (nếu có)
   - Số câu hỏi/số trang/thời gian ước tính

2. **📚 Chương trình bao phủ:**
   Liệt kê 3-5 chính/chủ đề chính (bullet points)

3. **🎯 Điểm quan trọng (Key Takeaways):**
   5-7 khái niệm/công thức/sự kiện PHẢI NHỚ

4. **💡 Mẹo ôn thi:**
   2-3 tips cụ thể (ví dụ: " tập trung vào chương X", "lưu ý công thức Y")

Giữ ngắn gọn, dễ đọc, dùng bullet points.

Tài liệu:
---
{document_text}
---
"""

SOLVE_PROBLEM_PROMPT = """
Bạn là giáo viên giỏi môn Toán, Lý, Hóa, Tiếng Anh.

HÃY GIẢI BÀI TẬP NÀY TỪNG BƯỚC CHI TIẾT:

ĐỀ BÀI:
{question}

YÊU CẦU:
1. Phân tích đề bài: xác định dạng, công thức cần dùng
2. MỖI BƯỚC phải có:
   - Giải thích ngắn gọn "tại sao" dùng công thức này
   - Thay số cụ thể
   - Kết quả sau bước
3. Không bỏ qua bước nào (ngay cả những bước đơn giản)
4. Dùng tiếng Việt, ngôn ngữ dễ hiểu như giáo viên dạy học sinh
5. Kết thúc bằng "Đáp án: ..."

VÍ DỤ:
Bước 1: Phương trình có dạng ax² + bx + c = 0. Tại sao? Vì đây là...
Bước 2: Tính Δ = b² - 4ac = 5² - 4*1*6 = 25 - 24 = 1. Tại sao? Δ dùng để...

TRẢ VỀ JSON (CHỈ JSON, không markdown):
{{
  "question": "tóm tắt ngắn đề bài",
  "steps": ["bước 1: ...", "bước 2: ...", ...],
  "answer": "đáp án cuối cùng"
}}
"""

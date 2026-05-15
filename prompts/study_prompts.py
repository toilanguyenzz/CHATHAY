"""Prompts for Study Mode — Quiz, Flashcard, Summary"""

GENERATE_QUIZ_PROMPT = """
Từ đề thi/bài giảng sau, tạo 10 câu hỏi trắc nghiệm 4 lựa chọn (A/B/C/D).

Yêu cầu:
1. **Phủ coverage:** Câu hỏi phải bao phủ các khái niệm QUAN TRỌNG nhất, phân bổ đều các chương/mục
2. **Độ khó:** 60% dễ (kiến thức cơ bản), 30% trung bình (ứng dụng), 10% khó (tổng hợp)
3. **Cấu trúc câu hỏi:**
   - Rõ ràng, không ambiguous
   - Distractors (đáp án sai) phải hợp lý (common misconceptions)
   - Tránh "all of the above" hoặc "none of the above"
4. **Giải thích:** Mỗi câu có giải thích ngắn (1-2 câu) tại sao đáp án đúng, và tại sao các đáp án khác sai
5. **Ngôn ngữ:** Dùng tiếng Việt, ngữ cảnh phù hợp với học sinh Việt Nam

Output JSON (CHÍNH XÁC, không markdown):
{{
  "questions": [
    {{
      "question": "Câu hỏi ở đây?",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct": 0,  // index 0-3 tương ứng A,B,C,D
      "explanation": "Giải thích ngắn gọn tại sao đáp án đúng",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}

Tài liệu:
---
{document_text}
---
"""


GENERATE_FLASHCARD_PROMPT = """
Từ tài liệu, trích xuất 15-20 khái niệm quan trọng để tạo flashcard.

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

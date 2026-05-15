# Hướng Dẫn Chạy Database Migrations

## Tạo bảng `solved_problems` trong Supabase

### Cách 1: Dùng Supabase Studio (Khuyến nghị - Dễ nhất)

1. Vào [Supabase Dashboard](https://supabase.com/dashboard)
2. Chọn project của bạn
3. Vào **SQL Editor** (bên trái)
4. Click **New Query**
5. Copy toàn bộ nội dung từ file `migrations/005_add_solved_problems.sql`
6. Paste vào editor
7. Click **Run** (hoặc Ctrl+Enter)

Nếu thành công, bạn sẽ thấy: `Query returned successfully: X rows affected`

### Cách 2: Dùng script Python (Nếu có DATABASE_URL)

```bash
# Set DATABASE_URL env var với connection string từ Supabase:
# Vào Project Settings -> Database -> Connection string
# Copy "URI" format, ví dụ:
# postgresql://postgres:[YOUR_PASSWORD]@zylckskdbbhiohbacxkd.supabase.co:5432/postgres

# Trên Windows PowerShell:
$env:DATABASE_URL="postgresql://postgres:[PASSWORD]@zylckskdbbhiohbacxkd.supabase.co:5432/postgres"

# Chạy script:
python apply_migrations.py
```

**Lưu ý:** Script này chỉ cần chạy 1 lần sau khi deploy mới.

---

## Kiểm tra lại

Sau khi chạy migration, kiểm tra bảng đã tạo chưa:

```bash
python -c "from services.db_service import supabase; r = supabase.table('solved_problems').select('*').limit(1).execute(); print('OK:', r.data)"
```

Nếu thấy `OK: []` (empty list) nghĩa là bảng đã tồn tại và sẵn sàng dùng.

---

## Các bảng khác đã có

Các migration 002, 003, 004 đã được chạy trước đó:
- 002: study_sessions, study_usage
- 003: documents.flashcards, documents.quiz_questions, user_coin_balance, coin_transactions
- 004: documents.content (RAG)

Chỉ cần chạy **005** cho tính năng solve-problem.

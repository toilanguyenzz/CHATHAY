# 🧪 TEST GUIDE - ChatHay Mini-App APIs

## Prerequisites
- Python 3.12+ installed
- All dependencies from `requirements.txt` installed
- `.env` file configured with:
  - `SUPABASE_URL` + `SUPABASE_KEY`
  - `DEEPSEEK_API_KEY`
  - `GEMINI_API_KEY`

---

## Step 1: Run Database Migration

**Migration 003** adds:
- `user_coin_balance` table
- `coin_transactions` table
- `flashcards` + `quiz_questions` columns on `documents`

Run in Supabase SQL Editor:
```sql
-- Copy content from migrations/003_add_flashcards_quiz_tables.sql
-- Paste into Supabase SQL Editor and execute
```

---

## Step 2: Start Backend Server

```powershell
cd zalo-doc-bot
python -m uvicorn zalo_webhook:zalo_webhook --host 0.0.0.0 --port 8000 --reload
```

Server will start at: `http://localhost:8000`

---

## Step 3: Quick Test with cURL

### Test 1: Health Check
```bash
curl http://localhost:8000/
```

Expected: `{"status":"ok"}` or similar

### Test 2: Get/Init Coin Balance
```bash
curl "http://localhost:8000/api/miniapp/coin/balance?user_id=test123"
```

Expected:
```json
{"balance":0,"today_usage":0,"study_sessions_today":0}
```

### Test 3: Earn Coins
```bash
curl -X POST "http://localhost:8000/api/miniapp/coin/earn" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test123","amount":50,"reason":"test"}'
```

Expected:
```json
{"success":true,"new_balance":50}
```

### Test 4: Spend Coins
```bash
curl -X POST "http://localhost:8000/api/miniapp/coin/spend" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test123","amount":10,"reason":"test"}'
```

Expected:
```json
{"success":true,"new_balance":40}
```

### Test 5: Get Transaction History
```bash
curl "http://localhost:8000/api/miniapp/coin/history?user_id=test123&limit=5"
```

Expected: Array of transactions

### Test 6: Share Reward
```bash
curl -X POST "http://localhost:8000/api/miniapp/share" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test123","type":"quiz_result"}'
```

Expected:
```json
{"success":true,"coins_earned":20}
```

---

## Step 4: Test Document Upload (Requires PDF)

### Create a test PDF first (or use any PDF):
```bash
# On Windows, you can create a simple PDF by:
# 1. Open any document in Word
# 2. Save as PDF
# Or download a sample PDF from: https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf
```

### Upload test:
```bash
curl -X POST "http://localhost:8000/api/miniapp/documents?user_id=test123" \
  -H "accept: application/json" \
  -F "file=@C:\path\to\your\test.pdf"
```

Expected:
```json
{
  "id": "uuid-here",
  "name": "test.pdf",
  "doc_type": "pdf",
  "timestamp": 1714760000.123,
  "summary": "...",
  "flashcard_count": 10,
  "quiz_count": 10
}
```

---

## Step 5: Automated Test Script

Run the provided PowerShell script:
```powershell
.\test_api.ps1
```

This will:
1. Start the server
2. Run through all API tests
3. Show results
4. Stop server

---

## Expected Test Results

| Test | Expected | Status |
|------|----------|--------|
| Server Health | 200 OK | ✅ |
| Coin Balance | 0 or existing | ✅ |
| Earn Coins | +50 | ✅ |
| Spend Coins | -10, returns 200 | ✅ |
| Insufficient Funds | 400 error | ✅ |
| Share Reward | +20 | ✅ |
| Transaction History | Array | ✅ |
| Upload PDF | 201 Created + AI processing | ⏳ |

---

## Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Supabase connection error"
Check `.env` file:
- `SUPABASE_URL` is correct
- `SUPABASE_KEY` is valid anon key

### "DeepSeek API error"
Check `DEEPSEEK_API_KEY` in `.env`
Test DeepSeek API directly:
```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"Hello"}]}'
```

### Upload fails with "File too large"
Check `MAX_FILE_SIZE_MB` in `config.py` (default: 10MB)

### PDF processing fails
Make sure `PyMuPDF` and `pdfplumber` installed correctly:
```bash
pip install PyMuPDF pdfplumber
```

---

## Debug Mode

Server logs show:
- ✅ for successful operations
- ⚠️ for warnings
- ❌ for errors

Check terminal where server is running for detailed logs.

---

## Next After Tests Pass

1. ✅ All APIs working
2. ✅ Database migrations applied
3. ✅ Coin system functional
4. ⬜ **Integrate ZaloPay in Mini-App UI** (ai-learning.tsx)
5. ⬜ **Test with real Mini-App** (upload from React frontend)
6. ⬜ **Deploy to Railway** for production

---

**Issues?** Check `zalo-doc-bot/walkthrough.md` for architecture details.

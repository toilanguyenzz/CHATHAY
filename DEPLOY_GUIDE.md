# Staging Deployment Guide — AI Learning (Study Mode)

**Date:** 2025-04-30  
**Target:** Railway.app (free tier)  
**Purpose:** Test production-like environment before soft launch

---

## 📦 Prerequisites

1. **GitHub account** — Railway auto-deploys from Git
2. **Supabase project** — Already created from Week 4 migrations
3. **API keys** — DeepSeek, Gemini, Zalo OA tokens
4. **Railway account** — Sign up at [railway.app](https://railway.app)

---

## 🔧 Step 1: Prepare Repository

### Commit all changes

```bash
git add .
git commit -m "Week 5: Persistent study sessions with Supabase + TTL"
git push origin main  # or your working branch
```

**Check:** All files committed:
- `services/db_service.py` (updated)
- `zalo_webhook.py` (updated)
- `migrations/002_add_study_tables.sql`
- `tests/` (optional, can exclude from production build)

---

## 🗄️ Step 2: Run Database Migration

**In Supabase SQL Editor** (https://app.supabase.com/project/_/sql):

```sql
-- Run migrations/002_add_study_tables.sql
-- Ensure study_sessions table exists with:
-- - user_id, doc_id, mode, state, created_at, expires_at, updated_at
-- - Indexes on user_id, expires_at
-- - RPC function cleanup_expired_study_sessions()
```

**Verify:**
```sql
SELECT * FROM study_sessions LIMIT 1;
-- Should return 0 rows (empty) but no error
SELECT * FROM cleanup_expired_study_sessions();
-- Should return integer (even 0)
```

---

## 🔐 Step 3: Configure Environment Variables

In Railway dashboard:

1. Go to your project → **Variables** tab
2. Add these variables:

| Key | Value | Notes |
|-----|-------|-------|
| `DEEPSEEK_API_KEY` | `sk-...` | From DeepSeek platform |
| `GEMINI_API_KEY` | `AIza...` | From Google AI Studio |
| `SUPABASE_URL` | `https://xxx.supabase.co` | From Supabase project settings |
| `SUPABASE_KEY` | `ey...` | Anon/public key from Supabase |
| `ZALO_ACCESS_TOKEN` | `...` | From Zalo OA → Developer → Access Token |
| `ZALO_REFRESH_TOKEN` | `...` | From Zalo OA (if using refresh) |
| `FREE_STUDY_SESSIONS_PER_DAY` | `3` | Free tier limit |
| `FREE_DAILY_LIMIT` | `5` | Q&A limit (not used for study) |
| `PORT` | `8000` | Railway sets this automatically |
| `DEBUG` | `false` | Production mode |

**⚠️ Critical:** Do NOT commit `.env` to Git. Railway variables are secure.

---

## 🛠️ Step 4: Deploy to Railway

### Option A: Deploy from GitHub (easiest)

1. In Railway dashboard → **New Project**
2. Select **Deploy from GitHub repo**
3. Choose your repository
4. Railway auto-detects `requirements.txt` and `Procfile`

**If no Procfile exists**, create `Procfile`:

```procfile
web: uvicorn zalo_webhook:app --host 0.0.0.0 --port $PORT
```

### Option B: Deploy via Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set variables (or do in dashboard)
railway variables:set DEEPSEEK_API_KEY=sk-...
railway variables:set GEMINI_API_KEY=AIza...
# ... set all variables

# Deploy
railway up
```

---

## 🏥 Step 5: Health Check

After deploy, Railway gives you a URL: `https://your-app.railway.app`

**Check health:**

```bash
curl https://your-app.railway.app/health
# Expected: {"status":"ok"}
```

**If 404 or error:**
- Check Railway logs (Dashboard → Logs)
- Verify `zalo_webhook:app` is the correct import path
- Ensure `uvicorn` installed in `requirements.txt`

---

## 🧪 Step 6: Smoke Test (Real Document)

### Test 1: Mode Detection

```bash
# Upload a DOCX/PDF with exam questions
curl -X POST "https://your-app.railway.app/api/summarize" \
  -F "file=@/path/to/test_exam.docx"
```

**Expected response:**
```json
{
  "document_type": "education",
  "mode_confidence": 1.0,
  "overview": "...",
  "buttons": [
    {"title": "🧠 Làm Quiz", "payload": "STUDY_START_QUIZ"},
    {"title": "🗂️ Lật Flashcard", "payload": "STUDY_START_FLASHCARD"},
    {"title": "❓ Hỏi đáp", "payload": "QA_START"}
  ]
}
```

### Test 2: Full Quiz Flow

1. **Send document via Zalo OA** (use Zalo app on phone)
2. **Tap "Làm Quiz"** button
3. **Answer 2-3 questions** (A/B/C/D)
4. **Restart server** (in Railway: "Restart" button)
5. **Continue quiz** → should load from Supabase

**Verify in Supabase:**
```sql
SELECT user_id, doc_id, mode, expires_at 
FROM study_sessions 
WHERE user_id = 'your_zalo_user_id';
```
Should show record with `expires_at` ~24h from now.

### Test 3: Premium Gating

1. **Check usage count:**
   ```sql
   SELECT * FROM user_usage 
   WHERE user_id = 'your_user_id' 
     AND date = CURRENT_DATE;
   ```
2. **Manually set count = 3** (or use API to increment 3 times)
3. **Send exam again** → should see premium upgrade message

---

## 📊 Step 7: Monitor Logs

Railway Dashboard → **Logs** tab. Filter for:

```
DeepSeek OK
Routing to Gemini
Study analytics
Supabase save_study_session
Cleaned up expired study sessions
```

**Alert signs:**
- `Supabase save_study_session error` → check table schema, RLS
- `DeepSeek quota exceeded` → switch to Gemini or add quota
- `Zalo token expired` → refresh tokens needed

---

## 🔄 Step 8: Rollback Plan

If deployment breaks:

1. **Railway Rollback:**
   - Dashboard → Deployments → Select previous → "Rollback"
   - Or: `railway rollback <previous_deployment_id>`

2. **Database rollback:**
   ```sql
   -- If schema changes broke things, restore from backup
   -- (Supabase has point-in-time recovery in Pro plan)
   ```

3. **Quick disable study mode:**
   - Set `FREE_STUDY_SESSIONS_PER_DAY=0` in Railway variables
   - Users will see premium gating message (safe state)

---

## ✅ Post-Deployment Validation

Run this checklist:

- [ ] Health endpoint returns 200 OK
- [ ] Document upload → `document_type="education"` detected
- [ ] Quiz starts, sends first question
- [ ] Answering questions works
- [ ] Session survives server restart
- [ ] Supabase `study_sessions` table populated
- [ ] Premium gating triggers after 3 sessions
- [ ] No errors in logs (only INFO/DEBUG)
- [ ] Latency: summary <5s, quiz generation <10s

---

## 🐛 Known Issues & Fixes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `Supabase module not found` | Missing dependency | Add `supabase` to `requirements.txt` |
| `RLS policy violation` | RLS enabled but no policy | Disable RLS or create policy for `user_id` |
| `Zalo token invalid` | Token expired | Use `cap_nhat_token_len_server.py` to refresh |
| `DeepSeek timeout` | Network/firewall | Check Railway outbound rules, switch to Gemini |
| `Session not persisting` | `doc_id` missing in save | Verify `session.doc_id` passed correctly |

---

## 📞 Support

If stuck:
1. Check Railway logs (most errors show stack trace)
2. Test locally with same `.env` vars: `uvicorn zalo_webhook:app`
3. Supabase dashboard → Table editor → verify data
4. Zalo OA dashboard → Webhook config → verify endpoint URL

---

## 🎯 Next After Staging

Once staging validated (24-48h):

1. **Scale up:** Railway auto-scales, but monitor credits
2. **Add monitoring:** Set up alerts for error rate >5%
3. **Prepare soft launch:** Recruit 100 students (friends, university groups)
4. **Collect feedback:** Track quiz completion rate, retention
5. **Week 6 (Payment):** Integrate MoMo/ZaloPay

---

**Good luck!** 🚀

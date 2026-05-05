# ═══════════════════════════════════════════════════════════════
# KOYEB DEPLOYMENT — CHAT HAY BACKEND
# ═══════════════════════════════════════════════════════════════
#
# HƯỚNG DẪN DEPLOY LÊN KOYEB (MIỄN PHÍ):
#
# Cách 1: Deploy từ GitHub (Đề xuất ✅)
#   1. Đăng ký tại https://app.koyeb.com (dùng GitHub login)
#   2. Create App → GitHub → Chọn repo "zalo-doc-bot"
#   3. Builder: Dockerfile
#   4. Instance type: eco-small (FREE)
#   5. Region: Singapore (gần Việt Nam nhất)
#   6. Port: 8000
#   7. Add tất cả Environment Variables từ file .env
#   8. Deploy!
#
# Cách 2: Deploy bằng Koyeb CLI
#   npm install -g koyeb-cli
#   koyeb login
#   koyeb app create chat-hay \
#     --docker "ghcr.io/<your-github>/zalo-doc-bot:latest" \
#     --instance-type eco-small \
#     --region sin \
#     --port 8000:http \
#     --env GEMINI_API_KEY=xxx \
#     --env DEEPSEEK_API_KEY=xxx \
#     --env SUPABASE_URL=xxx \
#     --env SUPABASE_KEY=xxx \
#     --env FPT_AI_API_KEY=xxx
#
# SAU KHI DEPLOY:
#   - URL mới sẽ là: https://chat-hay-<random>.koyeb.app
#   - Vào Zalo Developers → Đổi Webhook URL sang URL mới
#   - Test: gửi tin nhắn Zalo xem bot có reply không
#
# ═══════════════════════════════════════════════════════════════

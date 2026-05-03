import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { coinService } from "../services/coinService";
import { documentService } from "../services/documentService";
import { studyService } from "../services/studyService";
import { useAuth } from "../hooks/useAuth";

/* Animated Counter */
function useAnimatedNumber(target: number, duration = 800) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setCurrent(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return current;
}

/* Greeting */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return { text: "Chào buổi sáng", emoji: "☀️" };
  if (h < 18) return { text: "Chào buổi chiều", emoji: "🌤️" };
  return { text: "Chào buổi tối", emoji: "🌙" };
}

function HomePage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const greeting = getGreeting();

  const [coinInfo, setCoinInfo] = useState<{ balance: number; today_usage: number; study_sessions_today: number } | null>(null);
  const [stats, setStats] = useState({ docs: 0, cards: 0, quizzes: 0 });
  const [streakDays] = useState(7); // TODO: load from backend
  const [recentDocs, setRecentDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user_id) return;
    setLoading(true);

    Promise.all([
      coinService.getBalance().catch(() => ({ balance: 0, today_usage: 0, study_sessions_today: 0 })),
      documentService.getDocuments().catch(() => []),
    ]).then(([coin, docs]) => {
      setCoinInfo(coin);
      setStats({
        docs: docs.length,
        cards: 0, // TODO: load from backend
        quizzes: 0, // TODO: load from backend
      });
      setRecentDocs(docs.slice(0, 3));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [user_id]);

  const animatedCoin = useAnimatedNumber(coinInfo?.balance || 0);
  const animatedDocs = useAnimatedNumber(stats.docs, 600);
  const animatedCards = useAnimatedNumber(stats.cards, 700);
  const animatedQuiz = useAnimatedNumber(stats.quizzes, 500);

  return (
    <Page className="ch-page">
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* HEADER */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Box style={{
              width: 46, height: 46, borderRadius: 16,
              background: "var(--gradient-primary)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "white", fontWeight: 900, fontSize: 20,
              boxShadow: "0 6px 20px rgba(91, 76, 219, 0.30)",
            }}>C</Box>
            <Box>
              <Text style={{
                fontSize: "var(--font-size-xl)", fontWeight: 900,
                color: "var(--color-text-primary)", letterSpacing: "-0.02em",
              }}>CHAT HAY</Text>
              <Text style={{
                fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)",
                fontWeight: 500, marginTop: 1,
              }}>{greeting.emoji} {greeting.text}</Text>
            </Box>
          </Box>
          <Box style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "var(--color-warning-light)", borderRadius: "var(--radius-full)",
            padding: "6px 14px",
          }}>
            <span style={{ fontSize: 16 }}>🔥</span>
            <Text style={{ fontSize: 13, fontWeight: 800, color: "#B45309" }}>{streakDays} ngày</Text>
          </Box>
        </Box>

        {/* WALLET HERO CARD */}
        <Box className="ch-gradient-card" style={{ padding: "26px 24px" }}>
          <Box style={{ position: "relative", zIndex: 2 }}>
            <Text style={{
              fontSize: "var(--font-size-xs)", color: "rgba(255,255,255,0.65)",
              fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase",
            }}>Ví Coin của bạn</Text>
            <Box style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 6 }}>
              <Text style={{
                fontSize: 42, fontWeight: 900, color: "white",
                letterSpacing: "-0.03em", lineHeight: 1,
              }}>{animatedCoin.toLocaleString()}</Text>
              <Text style={{ fontSize: "var(--font-size-sm)", color: "rgba(255,255,255,0.50)", fontWeight: 600 }}>Coin</Text>
            </Box>
            <Box style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              marginTop: 16, padding: "10px 20px",
              background: "rgba(255,255,255,0.18)", backdropFilter: "blur(8px)",
              borderRadius: "var(--radius-md)", border: "1px solid rgba(255,255,255,0.25)",
              cursor: "pointer",
            }}
              onClick={() => navigate("/coin")}
            >
              <Text style={{ color: "white", fontWeight: 700, fontSize: 14 }}>Nạp Xu</Text>
              <Icon icon="zi-chevron-right" style={{ color: "rgba(255,255,255,0.7)", fontSize: 14 }} />
            </Box>
          </Box>
        </Box>

        {/* THỐNG KÊ NHANH */}
        <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          {[
            { label: "Tài liệu", value: animatedDocs, icon: "📄", accent: "#3B82F6", cls: "ch-stat-pill--blue" },
            { label: "Flashcard", value: animatedCards, icon: "🃏", accent: "#22C55E", cls: "ch-stat-pill--green" },
            { label: "Quiz", value: animatedQuiz, icon: "📝", accent: "#8B5CF6", cls: "ch-stat-pill--purple" },
          ].map((s, idx) => (
            <Box key={idx} className={`ch-stat-pill ${s.cls}`}>
              <Text style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</Text>
              <Text style={{
                fontSize: 26, fontWeight: 900, color: s.accent,
                letterSpacing: "-0.02em", lineHeight: 1,
              }}>{s.value}</Text>
              <Text style={{
                fontSize: 12, fontWeight: 600, color: "var(--color-text-tertiary)", marginTop: 4,
              }}>{s.label}</Text>
            </Box>
          ))}
        </Box>

        {/* HỌC TẬP */}
        <Box>
          <Text className="ch-section-title">📚 Học tập</Text>
          <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>

            {/* Flashcard */}
            <Box className="ch-card ch-card-interactive" style={{ padding: 20, textAlign: "center", cursor: "pointer" }}
              onClick={() => navigate("/flashcard")}
            >
              <Box style={{
                width: 56, height: 56, borderRadius: "var(--radius-lg)",
                background: "linear-gradient(135deg, #F59E0B, #EF4444)",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 14px", boxShadow: "0 6px 20px rgba(245, 158, 11, 0.25)",
              }}>
                <Text style={{ fontSize: 26, lineHeight: 1 }}>🃏</Text>
              </Box>
              <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 4 }}>Flashcard</Text>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", lineHeight: 1.4 }}>Ôn tập với thẻ ghi nhớ 3D</Text>
              <Box style={{ marginTop: 12, padding: "6px 14px", borderRadius: "var(--radius-full)", background: "var(--color-warning-light)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Text style={{ fontSize: 11, fontWeight: 700, color: "#D97706" }}>{stats.cards} thẻ</Text>
              </Box>
            </Box>

            {/* Quiz */}
            <Box className="ch-card ch-card-interactive" style={{ padding: 20, textAlign: "center", cursor: "pointer" }}
              onClick={() => navigate("/quiz")}
            >
              <Box style={{
                width: 56, height: 56, borderRadius: "var(--radius-lg)",
                background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
                display: "flex", alignItems: "center", justifyContent: "center",
                margin: "0 auto 14px", boxShadow: "0 6px 20px rgba(139, 92, 246, 0.25)",
              }}>
                <Text style={{ fontSize: 26, lineHeight: 1 }}>📝</Text>
              </Box>
              <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 4 }}>Quiz</Text>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", lineHeight: 1.4 }}>Kiểm tra kiến thức ngay</Text>
              <Box style={{ marginTop: 12, padding: "6px 14px", borderRadius: "var(--radius-full)", background: "var(--color-primary-lighter)", display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Text style={{ fontSize: 11, fontWeight: 700, color: "var(--color-primary)" }}>{stats.quizzes} bài</Text>
              </Box>
            </Box>
          </Box>
        </Box>

        {/* TÀI LIỆU GẦN ĐÂY */}
        <Box>
          <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <Text className="ch-section-title" style={{ marginBottom: 0 }}>📂 Tài liệu gần đây</Text>
            <Box onClick={() => navigate("/vault")} style={{
              display: "flex", alignItems: "center", gap: 4, cursor: "pointer", padding: "4px 10px", borderRadius: "var(--radius-full)", background: "var(--color-bg-subtle)",
            }}>
              <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-primary)" }}>Xem tất cả</Text>
              <Icon icon="zi-chevron-right" style={{ fontSize: 12, color: "var(--color-primary)" }} />
            </Box>
          </Box>

          {loading ? (
            <Box style={{ display: "flex", justifyContent: "center", padding: 20 }}>
              <Text className="ch-caption">Đang tải...</Text>
            </Box>
          ) : (
            <Box style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(recentDocs.length === 0) ? (
                <Box style={{ textAlign: "center", padding: 20 }}>
                  <Text style={{ fontSize: 32, marginBottom: 8 }}>📭</Text>
                  <Text className="ch-caption">Chưa có tài liệu nào</Text>
                </Box>
              ) : recentDocs.map((doc, idx) => {
                const typeEmoji = doc.doc_type === "pdf" ? "📕" : doc.doc_type === "word" || doc.doc_type === "docx" ? "📘" : "📙";
                return (
                  <Box key={doc.id} className="ch-doc-item" onClick={() => navigate("/vault")}>
                    <Box className="ch-doc-icon" style={{
                      background: doc.doc_type === "pdf" ? "#FEE2E2" : doc.doc_type === "word" || doc.doc_type === "docx" ? "#DBEAFE" : "#FEF3C7",
                    }}>
                      <Text style={{ fontSize: 20 }}>{typeEmoji}</Text>
                    </Box>
                    <Box style={{ flex: 1, minWidth: 0 }}>
                      <Text style={{
                        fontSize: "var(--font-size-sm)", fontWeight: 700,
                        color: "var(--color-text-primary)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>{doc.name}</Text>
                      <Text className="ch-caption" style={{ marginTop: 3 }}>{
                        doc.summary ? `${(doc.summary.length / 1024).toFixed(1)} KB` : "N/A"
                      } · {new Date(doc.timestamp * 1000).toLocaleDateString("vi-VN")}</Text>
                    </Box>
                    <Icon icon="zi-chevron-right" style={{ fontSize: 14, color: "var(--color-text-tertiary)" }} />
                  </Box>
                );
              })}
            </Box>
          )}
        </Box>

        {/* MẸO HÔM NAY */}
        <Box style={{
          padding: "18px 20px", borderRadius: "var(--radius-xl)",
          background: "var(--color-primary-lighter)",
          border: "1px solid rgba(91, 76, 219, 0.12)",
          display: "flex", alignItems: "flex-start", gap: 14,
        }}>
          <Text style={{ fontSize: 28, lineHeight: 1 }}>💡</Text>
          <Box>
            <Text style={{
              fontSize: "var(--font-size-sm)", fontWeight: 700,
              color: "var(--color-primary-dark)", marginBottom: 4,
            }}>Mẹo hôm nay</Text>
            <Text style={{
              fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)",
              lineHeight: 1.5,
            }}>Ôn tập mỗi ngày 15 phút hiệu quả hơn học dồn 3 tiếng. Dùng Flashcard để ghi nhớ tốt hơn!</Text>
          </Box>
        </Box>

      </Box>
    </Page>
  );
}

export default HomePage;

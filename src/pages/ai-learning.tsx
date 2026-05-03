import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";

/* ─── Animated Counter ─── */
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

/* ─── Greeting ─── */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return { text: "Chào buổi sáng", emoji: "☀️" };
  if (h < 18) return { text: "Chào buổi chiều", emoji: "🌤️" };
  return { text: "Chào buổi tối", emoji: "🌙" };
}

function AILearningPage() {
  const navigate = useNavigate();
  const greeting = getGreeting();

  const [coin] = useState(1000);
  const [stats] = useState({ docs: 12, cards: 48, quizzes: 5, streakDays: 7 });
  const [masteredCards] = useState(15);

  const animatedCoin = useAnimatedNumber(coin);
  const animatedCards = useAnimatedNumber(stats.cards, 700);
  const animatedQuiz = useAnimatedNumber(stats.quizzes, 500);

  return (
    <Page className="ch-page">
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* ══════════════ HEADER ══════════════ */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Box style={{
              width: 46, height: 46, borderRadius: 16,
              background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "white", fontWeight: 900, fontSize: 20,
              boxShadow: "0 6px 20px rgba(139, 92, 246, 0.30)",
            }}>🤖</Box>
            <Box>
              <Text style={{
                fontSize: "var(--font-size-xl)", fontWeight: 900,
                color: "var(--color-text-primary)", letterSpacing: "-0.02em",
              }}>AI LEARNING</Text>
              <Text style={{
                fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)",
                fontWeight: 500, marginTop: 1,
              }}>{greeting.emoji} {greeting.text}</Text>
            </Box>
          </Box>
          <Box style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "#FEF3C7", borderRadius: "var(--radius-full)",
            padding: "6px 14px",
          }}>
            <span style={{ fontSize: 16 }}>🔥</span>
            <Text style={{ fontSize: 13, fontWeight: 800, color: "#B45309" }}>{stats.streakDays} ngày</Text>
          </Box>
        </Box>

        {/* ══════════════ COIN WALLET ══════════════ */}
        <Box style={{
          background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
          borderRadius: "var(--radius-xl)", padding: "26px 24px",
          position: "relative", overflow: "hidden",
        }}>
          <Box style={{ position: "relative", zIndex: 2 }}>
            <Text style={{
              fontSize: "var(--font-size-xs)", color: "rgba(255,255,255,0.65)",
              fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase",
            }}>Ví Coin học tập</Text>
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
              onClick={() => alert("Chuyển đến nạp xu...")}
            >
              <Text style={{ color: "white", fontWeight: 700, fontSize: 14 }}>Nạp Xu</Text>
              <Icon icon="zi-chevron-right" style={{ color: "rgba(255,255,255,0.7)", fontSize: 14 }} />
            </Box>
          </Box>
        </Box>

        {/* ══════════════ THỐNG KÊ HỌC TẬP ══════════════ */}
        <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          {[
            { label: "Flashcard", value: animatedCards, icon: "🃏", accent: "#8B5CF6", cls: "ch-stat-pill--purple" },
            { label: "Quiz", value: animatedQuiz, icon: "📝", accent: "#EC4899", cls: "ch-stat-pill--pink" },
            { label: "Đã thuộc", value: masteredCards, icon: "✅", accent: "#22C55E", cls: "ch-stat-pill--green" },
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

        {/* ══════════════ CHỨC NĂNG HỌC TẬP ══════════════ */}
        <Box>
          <Text className="ch-section-title">🧠 Học tập với AI</Text>
          <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>

            {/* Card: Flashcard */}
            <Box
              className="ch-card ch-card-interactive"
              style={{ padding: 20, textAlign: "center", cursor: "pointer" }}
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
              <Text style={{
                fontSize: "var(--font-size-base)", fontWeight: 800,
                color: "var(--color-text-primary)", marginBottom: 4,
              }}>Flashcard</Text>
              <Text style={{
                fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)",
                lineHeight: 1.4,
              }}>Ôn tập với thẻ ghi nhớ 3D</Text>
              <Box style={{
                marginTop: 12, padding: "6px 14px",
                borderRadius: "var(--radius-full)",
                background: "#FEF3C7",
                display: "inline-flex", alignItems: "center", gap: 4,
              }}>
                <Text style={{ fontSize: 11, fontWeight: 700, color: "#D97706" }}>
                  {stats.cards} thẻ
                </Text>
              </Box>
            </Box>

            {/* Card: Quiz */}
            <Box
              className="ch-card ch-card-interactive"
              style={{ padding: 20, textAlign: "center", cursor: "pointer" }}
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
              <Text style={{
                fontSize: "var(--font-size-base)", fontWeight: 800,
                color: "var(--color-text-primary)", marginBottom: 4,
              }}>Quiz</Text>
              <Text style={{
                fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)",
                lineHeight: 1.4,
              }}>Kiểm tra kiến thức ngay</Text>
              <Box style={{
                marginTop: 12, padding: "6px 14px",
                borderRadius: "var(--radius-full)",
                background: "#F3E8FF",
                display: "inline-flex", alignItems: "center", gap: 4,
              }}>
                <Text style={{ fontSize: 11, fontWeight: 700, color: "#8B5CF6" }}>
                  {stats.quizzes} bài
                </Text>
              </Box>
            </Box>
          </Box>
        </Box>

        {/* ══════════════ MẸO HỌC TẬP ══════════════ */}
        <Box style={{
          padding: "18px 20px", borderRadius: "var(--radius-xl)",
          background: "#F3E8FF",
          border: "1px solid rgba(139, 92, 246, 0.12)",
          display: "flex", alignItems: "flex-start", gap: 14,
        }}>
          <Text style={{ fontSize: 28, lineHeight: 1 }}>💡</Text>
          <Box>
            <Text style={{
              fontSize: "var(--font-size-sm)", fontWeight: 700,
              color: "#6D28D9", marginBottom: 4,
            }}>Mẹo hôm nay</Text>
            <Text style={{
              fontSize: "var(--font-size-xs)", color: "#7C3AED",
              lineHeight: 1.5,
            }}>Ôn tập mỗi ngày 15 phút hiệu quả hơn học dồn 3 tiếng. Dùng Flashcard để ghi nhớ tốt hơn!</Text>
          </Box>
        </Box>

      </Box>
    </Page>
  );
}

export default AILearningPage;

import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { coinService } from "../services/coinService";
import { documentService } from "../services/documentService";
import { studyService } from "../services/studyService";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import { getGreeting } from "../utils/greeting";
import {
  IconDoc, IconFire, IconBrain, IconFlashcard, IconQuiz,
  IconChevronRight, IconRefresh, IconAlertTriangle,
} from "../components/icons";

/* ─── Skeleton ─── */
function Skeleton({ w = "100%", h = 20, r = 10, style }: { w?: string | number; h?: number; r?: number; style?: React.CSSProperties }) {
  return <Box className="ch-skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

/* ─── Error ─── */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Box className="ch-error">
      <Box className="ch-error-icon"><IconAlertTriangle size={24} color="#EF4444" /></Box>
      <Text className="ch-error-title">Không thể tải dữ liệu</Text>
      <Text className="ch-error-desc">Kiểm tra kết nối mạng rồi thử lại nhé</Text>
      <button className="ch-retry-btn" onClick={onRetry}><IconRefresh size={16} /> Thử lại</button>
    </Box>
  );
}

function HubPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const greeting = getGreeting();

  const [coinBalance, setCoinBalance] = useState(0);
  const [docCount, setDocCount] = useState(0);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadData = () => {
    if (!user_id) { setLoading(false); return; }
    apiClient.setUserId(user_id);
    setLoading(true); setError(false);
    Promise.all([
      coinService.getBalance().catch(() => ({ balance: 0 })),
      documentService.getDocuments().catch(() => []),
      studyService.getStreak().catch(() => ({ current_streak: 0 })),
    ]).then(([coin, docs, str]) => {
      setCoinBalance(coin.balance || 0);
      setDocCount(Array.isArray(docs) ? docs.length : 0);
      setStreak(str.current_streak || 0);
      setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
  };

  useEffect(() => { loadData(); }, [user_id]);
  const animatedCoin = useAnimatedNumber(coinBalance);

  return (
    <Page className="ch-page ch-hub-page" style={{ background: "#F8F7FF" }}>
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 20, paddingTop: 24, paddingBottom: 32 }}>

        {/* ═══ HERO HEADER ═══ */}
        <Box style={{
          background: "linear-gradient(160deg, #7C3AED 0%, #6366F1 40%, #EC4899 100%)",
          borderRadius: 28, padding: "28px 24px 24px",
          position: "relative", overflow: "hidden",
          boxShadow: "0 12px 40px rgba(124,58,237,0.3)",
        }}>
          {/* Decorative circles */}
          <Box style={{ position: "absolute", top: -40, right: -30, width: 150, height: 150, borderRadius: "50%", background: "rgba(255,255,255,0.08)", animation: "floatOrb 8s ease-in-out infinite" }} />
          <Box style={{ position: "absolute", bottom: -30, left: -20, width: 100, height: 100, borderRadius: "50%", background: "rgba(255,255,255,0.05)", animation: "floatOrb 10s ease-in-out infinite reverse" }} />

          <Box style={{ position: "relative", zIndex: 2 }}>
            {/* Top row: Logo + Streak */}
            <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Box style={{
                  width: 48, height: 48, borderRadius: 16,
                  background: "rgba(255,255,255,0.2)", backdropFilter: "blur(12px)",
                  border: "1px solid rgba(255,255,255,0.3)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  animation: "pulseGlow 3s ease-in-out infinite",
                }}><Text style={{ fontSize: 24 }}>🤖</Text></Box>
                <Box>
                  <Text style={{ fontSize: 20, fontWeight: 900, color: "white", letterSpacing: "-0.02em" }}>Chat Hay</Text>
                  <Text style={{ fontSize: 11, color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>
                    {greeting.emoji} {greeting.text}
                  </Text>
                </Box>
              </Box>
              {/* Streak badge */}
              <Box style={{
                display: "flex", alignItems: "center", gap: 4,
                padding: "6px 12px", borderRadius: 20,
                background: streak > 0 ? "rgba(251,191,36,0.25)" : "rgba(255,255,255,0.12)",
                border: `1px solid ${streak > 0 ? "rgba(251,191,36,0.4)" : "rgba(255,255,255,0.2)"}`,
              }}>
                <IconFire size={14} color={streak > 0 ? "#FBBF24" : "rgba(255,255,255,0.5)"} />
                <Text style={{ fontSize: 13, fontWeight: 800, color: streak > 0 ? "#FBBF24" : "rgba(255,255,255,0.5)" }}>
                  {streak}
                </Text>
              </Box>
            </Box>

            {/* Stats row */}
            <Box style={{ display: "flex", gap: 10 }}>
              {[
                { label: "Xu học tập", value: loading ? "..." : animatedCoin.toLocaleString(), icon: "🪙", color: "#FBBF24" },
                { label: "Tài liệu", value: loading ? "..." : docCount, icon: "📚", color: "#60A5FA" },
                { label: "Streak", value: loading ? "..." : `${streak} ngày`, icon: "🔥", color: "#F97316" },
              ].map((s, i) => (
                <Box key={i} style={{
                  flex: 1, padding: "12px 10px", borderRadius: 16,
                  background: "rgba(255,255,255,0.12)", backdropFilter: "blur(8px)",
                  border: "1px solid rgba(255,255,255,0.15)",
                  textAlign: "center",
                }}>
                  <Text style={{ fontSize: 18, marginBottom: 2 }}>{s.icon}</Text>
                  <Text style={{ fontSize: 16, fontWeight: 900, color: "white", display: "block" }}>{s.value}</Text>
                  <Text style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", fontWeight: 600 }}>{s.label}</Text>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>

        {error ? <ErrorState onRetry={loadData} /> : (
          <>
            {/* ═══ MAIN FEATURES ═══ */}
            <Box>
              <Text style={{ fontSize: 13, fontWeight: 800, color: "#6B7280", letterSpacing: "0.06em", marginBottom: 12, paddingLeft: 4 }}>
                ⚡ BẮT ĐẦU NGAY
              </Text>
              <Box style={{ display: "flex", flexDirection: "column", gap: 12 }}>

                {/* Card 1: Chat AI — PRIMARY */}
                <Box onClick={() => navigate("/solve-problem")} style={{
                  position: "relative", overflow: "hidden", borderRadius: 24, cursor: "pointer",
                  background: "linear-gradient(135deg, #7C3AED, #6366F1)",
                  padding: "24px 22px",
                  boxShadow: "0 8px 28px rgba(124,58,237,0.3)",
                  transition: "transform 0.2s",
                }}>
                  <Box style={{ position: "absolute", top: -30, right: -20, width: 120, height: 120, borderRadius: "50%", background: "rgba(255,255,255,0.08)", animation: "floatOrb 7s ease-in-out infinite" }} />
                  <Box style={{ position: "relative", zIndex: 2, display: "flex", alignItems: "center", gap: 16 }}>
                    <Box style={{
                      width: 56, height: 56, borderRadius: 18,
                      background: "rgba(255,255,255,0.18)", backdropFilter: "blur(8px)",
                      border: "1px solid rgba(255,255,255,0.25)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}><Text style={{ fontSize: 28 }}>💬</Text></Box>
                    <Box style={{ flex: 1 }}>
                      <Box style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <Text style={{ fontSize: 18, fontWeight: 900, color: "white" }}>Chat Hay AI</Text>
                        <Box style={{ padding: "2px 8px", borderRadius: 8, background: "rgba(251,191,36,0.3)", border: "1px solid rgba(251,191,36,0.4)" }}>
                          <Text style={{ fontSize: 9, fontWeight: 800, color: "#FBBF24" }}>HOT</Text>
                        </Box>
                      </Box>
                      <Text style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", fontWeight: 500, lineHeight: 1.4 }}>
                        Chụp ảnh bài tập → AI giải chi tiết từng bước
                      </Text>
                    </Box>
                    <Box style={{
                      width: 36, height: 36, borderRadius: 12,
                      background: "rgba(255,255,255,0.2)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}><IconChevronRight size={16} color="white" /></Box>
                  </Box>
                </Box>

                {/* Card 2 & 3: Side by side */}
                <Box style={{ display: "flex", gap: 12 }}>
                  {/* File Processing */}
                  <Box onClick={() => navigate("/file-processing")} style={{
                    flex: 1, borderRadius: 22, cursor: "pointer",
                    background: "linear-gradient(160deg, #3B82F6, #1D4ED8)",
                    padding: "22px 18px",
                    boxShadow: "0 6px 24px rgba(59,130,246,0.25)",
                    position: "relative", overflow: "hidden",
                    transition: "transform 0.2s",
                  }}>
                    <Box style={{ position: "absolute", top: -20, right: -15, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.1)" }} />
                    <Box style={{ position: "relative", zIndex: 2 }}>
                      <Box style={{
                        width: 44, height: 44, borderRadius: 14,
                        background: "rgba(255,255,255,0.18)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        marginBottom: 14,
                      }}><Text style={{ fontSize: 22 }}>📄</Text></Box>
                      <Text style={{ fontSize: 15, fontWeight: 800, color: "white", marginBottom: 4 }}>Tóm tắt & Giải thích</Text>
                      <Text style={{ fontSize: 11, color: "rgba(255,255,255,0.65)", fontWeight: 500, lineHeight: 1.4 }}>
                        Upload → Tóm tắt → Q&A
                      </Text>
                      <Box style={{
                        marginTop: 14, display: "flex", alignItems: "center", gap: 4,
                        padding: "6px 12px", borderRadius: 10,
                        background: "rgba(255,255,255,0.15)", width: "fit-content",
                      }}>
                        <Text style={{ fontSize: 11, fontWeight: 700, color: "white" }}>Mở</Text>
                        <IconChevronRight size={12} color="rgba(255,255,255,0.7)" />
                      </Box>
                    </Box>
                  </Box>

                  {/* AI Learning */}
                  <Box onClick={() => navigate("/ai-learning")} style={{
                    flex: 1, borderRadius: 22, cursor: "pointer",
                    background: "linear-gradient(160deg, #EC4899, #BE185D)",
                    padding: "22px 18px",
                    boxShadow: "0 6px 24px rgba(236,72,153,0.25)",
                    position: "relative", overflow: "hidden",
                    transition: "transform 0.2s",
                  }}>
                    <Box style={{ position: "absolute", top: -20, right: -15, width: 80, height: 80, borderRadius: "50%", background: "rgba(255,255,255,0.1)" }} />
                    <Box style={{ position: "relative", zIndex: 2 }}>
                      <Box style={{
                        width: 44, height: 44, borderRadius: 14,
                        background: "rgba(255,255,255,0.18)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        marginBottom: 14,
                      }}><Text style={{ fontSize: 22 }}>🧠</Text></Box>
                      <Text style={{ fontSize: 15, fontWeight: 800, color: "white", marginBottom: 4 }}>AI Learning</Text>
                      <Text style={{ fontSize: 11, color: "rgba(255,255,255,0.65)", fontWeight: 500, lineHeight: 1.4 }}>
                        Quiz · Flashcard · Streak
                      </Text>
                      <Box style={{
                        marginTop: 14, display: "flex", alignItems: "center", gap: 4,
                        padding: "6px 12px", borderRadius: 10,
                        background: "rgba(255,255,255,0.15)", width: "fit-content",
                      }}>
                        <Text style={{ fontSize: 11, fontWeight: 700, color: "white" }}>Học</Text>
                        <IconChevronRight size={12} color="rgba(255,255,255,0.7)" />
                      </Box>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* ═══ QUICK ACCESS ═══ */}
            <Box>
              <Text style={{ fontSize: 13, fontWeight: 800, color: "#6B7280", letterSpacing: "0.06em", marginBottom: 12, paddingLeft: 4 }}>
                🎯 TRUY CẬP NHANH
              </Text>
              <Box style={{ display: "flex", gap: 10 }}>
                {[
                  { emoji: "📁", label: "Kho tài liệu", desc: `${docCount} file`, color: "#3B82F6", bg: "#EFF6FF", action: () => navigate("/vault") },
                  { emoji: "🗂️", label: "Flashcard", desc: "SM-2", color: "#8B5CF6", bg: "#F5F3FF", action: () => navigate("/flashcard") },
                  { emoji: "✅", label: "Quiz", desc: "Timer", color: "#EC4899", bg: "#FDF2F8", action: () => navigate("/quiz") },
                ].map((item, i) => (
                  <Box key={i} onClick={item.action} style={{
                    flex: 1, padding: "16px 10px", borderRadius: 18,
                    background: "white", border: "1px solid #E5E7EB",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                    textAlign: "center", cursor: "pointer",
                    transition: "all 0.2s",
                  }}>
                    <Box style={{
                      width: 44, height: 44, borderRadius: 14, margin: "0 auto 8px",
                      background: item.bg,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}><Text style={{ fontSize: 22 }}>{item.emoji}</Text></Box>
                    <Text style={{ fontSize: 12, fontWeight: 700, color: "#1F2937", marginBottom: 2 }}>{item.label}</Text>
                    <Text style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 600 }}>{item.desc}</Text>
                  </Box>
                ))}
              </Box>
            </Box>

            {/* ═══ TIP ═══ */}
            <Box style={{
              padding: "16px 18px", borderRadius: 18,
              background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
              border: "1px solid #FCD34D",
              display: "flex", alignItems: "center", gap: 12,
            }}>
              <Text style={{ fontSize: 24, flexShrink: 0 }}>💡</Text>
              <Box>
                <Text style={{ fontSize: 12, fontWeight: 700, color: "#92400E", marginBottom: 2 }}>Mẹo hôm nay</Text>
                <Text style={{ fontSize: 11, color: "#A16207", lineHeight: 1.5, fontWeight: 500 }}>
                  Chụp ảnh bài tập → AI giải chi tiết → Tạo Quiz ôn tập → Nhận Coin thưởng! 🎉
                </Text>
              </Box>
            </Box>
          </>
        )}
      </Box>
    </Page>
  );
}

export default HubPage;

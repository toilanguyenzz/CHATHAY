import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef } from "react";
import { coinService } from "../services/coinService";
import { documentService } from "../services/documentService";
import { studyService } from "../services/studyService";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import {
  IconBrain, IconFire, IconFlashcard, IconQuiz,
  IconChevronLeft, IconChevronRight, IconLightbulb,
  IconRefresh, IconAlertTriangle, IconDoc, IconFolder,
  IconCamera, IconInbox, IconUpload
} from "../components/icons";

/* ─── Skeleton ─── */
function Skeleton({ w = "100%", h = 20, r = 10, style }: { w?: string | number; h?: number; r?: number; style?: React.CSSProperties }) {
  return <Box className="ch-skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

/* ─── Error State ─── */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Box className="ch-error">
      <Box className="ch-error-icon"><IconAlertTriangle size={24} color="#EF4444" /></Box>
      <Text className="ch-error-title">Không thể tải dữ liệu</Text>
      <Text className="ch-error-desc">Kiểm tra kết nối mạng rồi thử lại</Text>
      <button className="ch-retry-btn" onClick={onRetry}><IconRefresh size={16} /> Thử lại</button>
    </Box>
  );
}

function AILearningPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [coinBalance, setCoinBalance] = useState(0);
  const [docs, setDocs] = useState<any[]>([]);
  const [streak, setStreak] = useState(0);
  const [streakMaintained, setStreakMaintained] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeRole, setActiveRole] = useState<"student" | "teacher">("student");

  const loadData = () => {
    if (!user_id) return;
    apiClient.setUserId(user_id);
    setLoading(true);
    setError(false);
    Promise.all([
      coinService.getBalance().catch(() => ({ balance: 0 })),
      documentService.getDocuments().catch(() => []),
      studyService.getStreak().catch(() => ({ current_streak: 0, streak_maintained: false })),
    ]).then(([coin, docList, str]) => {
      setCoinBalance((coin as any).balance || 0);
      setDocs(Array.isArray(docList) ? docList : []);
      setStreak((str as any).current_streak || 0);
      setStreakMaintained((str as any).streak_maintained || false);
      setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
  };

  useEffect(() => { loadData(); }, [user_id]);

  const animatedCoin = useAnimatedNumber(coinBalance);
  const totalFlashcards = docs.reduce((a, d) => a + (d.flashcard_count || 0), 0);
  const totalQuiz = docs.reduce((a, d) => a + (d.quiz_count || 0), 0);

  const handleCameraCapture = () => {
    if (fileInputRef.current) {
      fileInputRef.current.accept = "image/*";
      fileInputRef.current.capture = "environment";
      fileInputRef.current.click();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try { await documentService.uploadAndProcess(file); loadData(); } catch { }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /* ─── Consolidated Features ─── */
  const studentFeatures = [
    {
      icon: <IconQuiz size={26} color="white" />,
      title: "Làm Quiz",
      desc: "Chụp SGK hoặc chọn tài liệu → AI tạo quiz trắc nghiệm có đếm giờ",
      gradient: "linear-gradient(135deg, #7C3AED, #6366F1)",
      shadow: "rgba(124,58,237,0.35)",
      action: () => docs.length > 0 ? navigate("/quiz") : handleCameraCapture(),
      badge: totalQuiz > 0 ? `${totalQuiz} câu` : null,
    },
    {
      icon: <IconFlashcard size={26} color="white" />,
      title: "Flashcard",
      desc: "Ôn tập thẻ ghi nhớ SM-2 — lặp lại ngắt quãng, nhớ lâu hơn 3x",
      gradient: "linear-gradient(135deg, #F59E0B, #D97706)",
      shadow: "rgba(245,158,11,0.35)",
      action: () => navigate("/flashcard"),
      badge: totalFlashcards > 0 ? `${totalFlashcards} thẻ` : null,
    },
    {
      icon: <IconInbox size={26} color="white" />,
      title: "Hỏi Đáp AI",
      desc: "Hỏi bất kỳ câu gì — AI trả lời chính xác từ tài liệu của bạn (RAG)",
      gradient: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
      shadow: "rgba(59,130,246,0.35)",
      action: () => navigate("/file-processing"),
      badge: null,
    },
  ];

  const teacherFeatures = [
    {
      icon: <IconDoc size={26} color="white" />,
      title: "Tạo Đề Thi",
      desc: "Upload tài liệu → AI ra đề trắc nghiệm + đáp án tự động",
      gradient: "linear-gradient(135deg, #3B82F6, #1E40AF)",
      shadow: "rgba(59,130,246,0.35)",
      action: () => navigate("/file-processing"),
      badge: null,
    },
    {
      icon: <IconUpload size={26} color="white" />,
      title: "Giao Bài Zalo",
      desc: "Gửi link Quiz/Flashcard cho cả lớp — 1 click là xong",
      gradient: "linear-gradient(135deg, #22C55E, #16A34A)",
      shadow: "rgba(34,197,94,0.35)",
      action: () => navigate("/leaderboard"),
      badge: null,
    },
    {
      icon: <IconFolder size={26} color="white" />,
      title: "Kho Tài Liệu",
      desc: "Quản lý bộ đề, tóm tắt — tìm kiếm & lọc theo môn học",
      gradient: "linear-gradient(135deg, #F59E0B, #D97706)",
      shadow: "rgba(245,158,11,0.35)",
      action: () => navigate("/vault"),
      badge: docs.length > 0 ? `${docs.length} file` : null,
    },
  ];

  const features = activeRole === "student" ? studentFeatures : teacherFeatures;

  // ── Streak days ──
  const dayLabels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const todayIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;

  return (
    <Page className="ch-page">
      <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
        onChange={handleFileUpload} style={{ display: "none" }} />

      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        {/* ══════ HEADER ══════ */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Box onClick={() => navigate("/")} style={{
              width: 38, height: 38, borderRadius: 14,
              background: "white", border: "1px solid #E5E7EB",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }}><IconChevronLeft size={18} color="#6B7280" /></Box>
            <Box>
              <Text style={{ fontSize: 20, fontWeight: 900, color: "#1E1B4B", letterSpacing: "-0.02em" }}>
                AI Learning</Text>
              <Text style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 600 }}>
                Học thông minh, nhớ lâu hơn</Text>
            </Box>
          </Box>
          {/* Streak Badge */}
          <Box style={{
            display: "flex", alignItems: "center", gap: 5,
            background: streak > 0 ? "linear-gradient(135deg, #FEF3C7, #FDE68A)" : "#F3F4F6",
            borderRadius: 20, padding: "6px 14px",
            border: streak > 0 ? "1px solid #FCD34D" : "1px solid #E5E7EB",
          }}>
            <IconFire size={15} color={streak > 0 ? "#F97316" : "#9CA3AF"} />
            <Text style={{ fontSize: 13, fontWeight: 800, color: streak > 0 ? "#B45309" : "#9CA3AF" }}>
              {streak}</Text>
          </Box>
        </Box>

        {error ? <ErrorState onRetry={loadData} /> : (
          <>
            {/* ══════ COIN + STATS ROW ══════ */}
            <Box style={{
              background: "linear-gradient(135deg, #4F46E5, #7C3AED, #EC4899)",
              borderRadius: 22, padding: "18px 20px",
              position: "relative", overflow: "hidden",
            }}>
              <Box style={{
                position: "absolute", top: -40, right: -30,
                width: 140, height: 140, borderRadius: "50%",
                background: "rgba(255,255,255,0.07)",
              }} />
              <Box style={{ position: "relative", zIndex: 2 }}>
                {/* Coin row */}
                <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                  <Box style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                    {loading ? <Skeleton w={60} h={28} r={8} style={{ opacity: 0.3 }} /> : (
                      <Text style={{ fontSize: 28, fontWeight: 900, color: "white", letterSpacing: "-0.03em", lineHeight: 1 }}>
                        {animatedCoin.toLocaleString()}</Text>
                    )}
                    <Text style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", fontWeight: 600 }}>Coin</Text>
                  </Box>
                  <Box onClick={() => alert("Nạp xu qua ZaloPay...")} style={{
                    padding: "8px 16px", background: "rgba(255,255,255,0.15)",
                    backdropFilter: "blur(8px)", borderRadius: 12,
                    border: "1px solid rgba(255,255,255,0.2)", cursor: "pointer",
                  }}>
                    <Text style={{ color: "white", fontWeight: 700, fontSize: 12 }}>Nạp Xu</Text>
                  </Box>
                </Box>
                {/* Stats */}
                <Box style={{ display: "flex", gap: 8 }}>
                  {[
                    { label: "Tài liệu", value: docs.length, icon: <IconDoc size={16} color="rgba(255,255,255,0.8)" /> },
                    { label: "Flashcard", value: totalFlashcards, icon: <IconFlashcard size={16} color="rgba(255,255,255,0.8)" /> },
                    { label: "Quiz", value: totalQuiz, icon: <IconQuiz size={16} color="rgba(255,255,255,0.8)" /> },
                  ].map((s, i) => (
                    <Box key={i} style={{
                      flex: 1, textAlign: "center", padding: "10px 6px",
                      background: "rgba(255,255,255,0.1)", borderRadius: 14,
                      backdropFilter: "blur(4px)",
                    }}>
                      <Box style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>{s.icon}</Box>
                      {loading ? <Skeleton w={24} h={20} r={4} style={{ margin: "0 auto", opacity: 0.3 }} /> : (
                        <Text style={{ fontSize: 18, fontWeight: 900, color: "white", lineHeight: 1 }}>{s.value}</Text>
                      )}
                      <Text style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", fontWeight: 600, marginTop: 2 }}>{s.label}</Text>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Box>

            {/* ══════ ROLE SWITCHER ══════ */}
            <Box style={{
              display: "flex", borderRadius: 16, background: "#F3F4F6", padding: 3,
            }}>
              {[
                { key: "student" as const, label: "Học Sinh" },
                { key: "teacher" as const, label: "Giáo Viên" },
              ].map(role => (
                <Box key={role.key} onClick={() => setActiveRole(role.key)} style={{
                  flex: 1, textAlign: "center", padding: "10px 0",
                  borderRadius: 14, cursor: "pointer",
                  background: activeRole === role.key ? "white" : "transparent",
                  boxShadow: activeRole === role.key ? "0 2px 8px rgba(0,0,0,0.08)" : "none",
                  transition: "all 0.25s ease",
                }}>
                  <Text style={{
                    fontSize: 13, fontWeight: activeRole === role.key ? 800 : 600,
                    color: activeRole === role.key ? "#1E1B4B" : "#9CA3AF",
                  }}>{role.label}</Text>
                </Box>
              ))}
            </Box>

            {/* ══════ FEATURE CARDS — Clean list style ══════ */}
            <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {features.map((f, idx) => (
                <Box key={idx} onClick={f.action} style={{
                  display: "flex", alignItems: "center", gap: 14,
                  padding: "16px 18px", borderRadius: 20, cursor: "pointer",
                  background: "white", border: "1px solid #E5E7EB",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                  transition: "all 0.2s ease",
                  position: "relative", overflow: "hidden",
                }}>
                  {/* Icon */}
                  <Box style={{
                    width: 52, height: 52, borderRadius: 16, flexShrink: 0,
                    background: f.gradient,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: `0 6px 16px ${f.shadow}`,
                  }}>{f.icon}</Box>
                  {/* Text */}
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Box style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                      <Text style={{ fontSize: 15, fontWeight: 800, color: "#1F2937" }}>{f.title}</Text>
                      {f.badge && (
                        <Box style={{
                          padding: "2px 8px", borderRadius: 8,
                          background: "#EEF2FF", border: "1px solid #C7D2FE",
                        }}>
                          <Text style={{ fontSize: 10, fontWeight: 700, color: "#4F46E5" }}>{f.badge}</Text>
                        </Box>
                      )}
                    </Box>
                    <Text style={{
                      fontSize: 12, color: "#6B7280", lineHeight: 1.5, fontWeight: 500,
                    }}>{f.desc}</Text>
                  </Box>
                  {/* Arrow */}
                  <IconChevronRight size={18} color="#D1D5DB" />
                </Box>
              ))}
            </Box>

            {/* ══════ STREAK PROGRESS ══════ */}
            <Box style={{
              padding: "16px 18px", borderRadius: 20,
              background: streak > 0 ? "linear-gradient(135deg, #FFFBEB, #FEF3C7)" : "#F9FAFB",
              border: `1px solid ${streak > 0 ? "#FDE68A" : "#E5E7EB"}`,
            }}>
              <Box style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <IconFire size={20} color={streak > 0 ? "#F97316" : "#9CA3AF"} />
                <Box style={{ flex: 1 }}>
                  <Text style={{ fontSize: 13, fontWeight: 800, color: streak > 0 ? "#92400E" : "#374151" }}>
                    Chuỗi: {streak} ngày</Text>
                  <Text style={{ fontSize: 11, color: streak > 0 ? "#B45309" : "#9CA3AF", fontWeight: 500 }}>
                    {streakMaintained ? "Đã hoàn thành hôm nay" : streak > 0 ? "Hãy học để giữ streak!" : "Bắt đầu ngay!"}</Text>
                </Box>
              </Box>
              <Box style={{ display: "flex", gap: 5 }}>
                {dayLabels.map((day, i) => {
                  const isActive = i < streak % 7 || streak >= 7;
                  const isToday = i === todayIdx;
                  return (
                    <Box key={i} style={{
                      flex: 1, textAlign: "center", padding: "5px 0",
                      borderRadius: 10,
                      background: isActive ? "linear-gradient(135deg, #F59E0B, #EF4444)" : "white",
                      border: isToday ? "2px solid #F97316" : `1px solid ${isActive ? "transparent" : "#E5E7EB"}`,
                    }}>
                      <Text style={{ fontSize: 9, fontWeight: 700, color: isActive ? "white" : "#9CA3AF" }}>{day}</Text>
                      <Text style={{ fontSize: 11, lineHeight: 1 }}>{isActive ? "🔥" : "○"}</Text>
                    </Box>
                  );
                })}
              </Box>
            </Box>

            {/* ══════ QUICK LINKS ══════ */}
            <Box style={{ display: "flex", gap: 8 }}>
              {[
                { label: "Demo Quiz", icon: <IconQuiz size={18} color="#F59E0B" />, bg: "#FFFBEB", border: "#FDE68A", action: () => navigate("/demo-quiz") },
                { label: "Leaderboard", icon: <IconBrain size={18} color="#10B981" />, bg: "#ECFDF5", border: "#A7F3D0", action: () => navigate("/leaderboard") },
                { label: "Kho tài liệu", icon: <IconDoc size={18} color="#3B82F6" />, bg: "#EFF6FF", border: "#BFDBFE", action: () => navigate("/vault") },
              ].map((item, i) => (
                <Box key={i} onClick={item.action} style={{
                  flex: 1, padding: "12px 8px", borderRadius: 14, textAlign: "center",
                  background: item.bg, border: `1px solid ${item.border}`, cursor: "pointer",
                  transition: "all 0.2s",
                }}>
                  <Box style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>{item.icon}</Box>
                  <Text style={{ fontSize: 11, fontWeight: 700, color: "#374151" }}>{item.label}</Text>
                </Box>
              ))}
            </Box>

            {/* ══════ TIP ══════ */}
            <Box style={{
              padding: "14px 16px", borderRadius: 16,
              background: "#F3E8FF", border: "1px solid #DDD6FE",
              display: "flex", alignItems: "flex-start", gap: 10,
            }}>
              <IconLightbulb size={18} color="#7C3AED" style={{ flexShrink: 0, marginTop: 2 }} />
              <Text style={{ fontSize: 12, color: "#6D28D9", lineHeight: 1.5, fontWeight: 500 }}>
                <strong>SM-2:</strong> Câu nào làm sai sẽ tự xuất hiện lại vào đúng lúc bạn sắp quên — ghi nhớ tốt hơn 300%!</Text>
            </Box>
          </>
        )}
      </Box>
    </Page>
  );
}

export default AILearningPage;

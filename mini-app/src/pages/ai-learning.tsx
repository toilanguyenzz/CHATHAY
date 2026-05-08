import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef } from "react";
import { coinService } from "../services/coinService";
import { documentService } from "../services/documentService";
import { studyService } from "../services/studyService";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import { getGreeting } from "../utils/greeting";
import {
  IconBrain, IconCoin, IconFire, IconFlashcard, IconQuiz,
  IconCheck, IconChevronLeft, IconChevronRight, IconLightbulb,
  IconRefresh, IconAlertTriangle, IconDoc, IconUpload, IconSearch,
  IconFolder, IconCamera, IconInbox
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

/* ─── Section Header ─── */
function SectionHeader({ title, actionLabel, onAction }: { title: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <Text className="ch-section-title" style={{ marginBottom: 0 }}>{title}</Text>
      {actionLabel && onAction && (
        <Box onClick={onAction} style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
          <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-primary)" }}>{actionLabel}</Text>
          <IconChevronRight size={14} color="var(--color-primary)" />
        </Box>
      )}
    </Box>
  );
}

function AILearningPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const greeting = getGreeting();
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

  /* ─── Camera upload for "Chụp SGK → Quiz" ─── */
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
    try {
      await documentService.uploadAndProcess(file);
      loadData();
    } catch { }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /* ─── Student Features ─── */
  const studentFeatures = [
    {
      icon: <IconCamera size={24} color="white" />, 
      title: "Chụp SGK → Quiz",
      desc: "Chụp 1 trang sách → AI tạo 5 câu Quiz trong 15 giây",
      gradient: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
      action: handleCameraCapture,
    },
    {
      icon: <IconBrain size={24} color="white" />, 
      title: "Study Mode",
      desc: "Tóm tắt → Quiz → Flashcard SM-2 — Luồng học sâu tự động",
      gradient: "linear-gradient(135deg, #8B5CF6, #6D28D9)",
      action: () => docs.length > 0 ? navigate("/quiz") : navigate("/file-processing"),
    },
    {
      icon: <IconFlashcard size={24} color="white" />, 
      title: "Flashcard 3D",
      desc: "Ôn tập thẻ ghi nhớ với thuật toán SM-2 lặp lại ngắt quãng",
      gradient: "linear-gradient(135deg, #F59E0B, #D97706)",
      action: () => navigate("/flashcard"),
    },
    {
      icon: <IconQuiz size={24} color="white" />, 
      title: "Quiz Timer",
      desc: "Kiểm tra kiến thức có đếm ngược 30s + âm thanh phản hồi",
      gradient: "linear-gradient(135deg, #EC4899, #DB2777)",
      action: () => navigate("/quiz"),
    },
    {
      icon: <IconInbox size={24} color="white" />, 
      title: "Hỏi Đáp Q&A",
      desc: "Hỏi AI bất kỳ câu gì — trả lời chính xác từ tài liệu (RAG)",
      gradient: "linear-gradient(135deg, #6366F1, #4F46E5)",
      action: () => navigate("/file-processing"),
    },
    {
      icon: <IconUpload size={24} color="white" />, 
      title: "Chia Sẻ Kết Quả",
      desc: "Chia sẻ điểm Quiz & Flashcard qua Zalo — thách đấu bạn bè",
      gradient: "linear-gradient(135deg, #14B8A6, #0D9488)",
      action: () => navigate("/quiz"),
    },
  ];

  const teacherFeatures = [
    {
      icon: <IconDoc size={24} color="white" />, 
      title: "Tạo Đề Thi Tự Động",
      desc: "Upload tài liệu → AI ra đề 20 câu trắc nghiệm + đáp án",
      gradient: "linear-gradient(135deg, #3B82F6, #1E40AF)",
      action: () => navigate("/file-processing"),
    },
    {
      icon: <IconBrain size={24} color="white" />, 
      title: "Dashboard Lớp Học",
      desc: "Xem học sinh nào yếu chỗ nào → AI gợi ý bài ôn tập",
      gradient: "linear-gradient(135deg, #8B5CF6, #7C3AED)",
      action: () => alert("Tính năng sắp ra mắt!"),
    },
    {
      icon: <IconUpload size={24} color="white" />, 
      title: "Giao Bài Qua Zalo",
      desc: "Gửi link Quiz/Flashcard cho cả lớp — 1 click là xong",
      gradient: "linear-gradient(135deg, #22C55E, #16A34A)",
      action: () => alert("Tính năng sắp ra mắt!"),
    },
    {
      icon: <IconFolder size={24} color="white" />, 
      title: "Kho Tài Liệu",
      desc: "Quản lý bộ đề, tóm tắt — tìm kiếm & lọc theo loại file",
      gradient: "linear-gradient(135deg, #F59E0B, #D97706)",
      action: () => navigate("/vault"),
    },
  ];

  const features = activeRole === "student" ? studentFeatures : teacherFeatures;

  return (
    <Page className="ch-page">
      <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
        onChange={handleFileUpload} style={{ display: "none" }} />

      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 18 }}>

        {/* ══════ HEADER ══════ */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Box onClick={() => navigate("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            }}><IconChevronLeft size={18} color="var(--color-text-secondary)" /></Box>
            <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <Box style={{
                width: 46, height: 46, borderRadius: 16,
                background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 6px 20px rgba(139, 92, 246, 0.30)",
              }}><IconBrain size={22} color="white" /></Box>
              <Box>
                <Text style={{ fontSize: "var(--font-size-xl)", fontWeight: 900, color: "var(--color-text-primary)", letterSpacing: "-0.02em" }}>
                  AI LEARNING</Text>
                <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", fontWeight: 500 }}>
                  {greeting.emoji} {greeting.text}</Text>
              </Box>
            </Box>
          </Box>
          {/* Streak Badge */}
          <Box style={{
            display: "flex", alignItems: "center", gap: 6,
            background: streak > 0 ? "#FEF3C7" : "var(--color-bg-subtle)",
            borderRadius: "var(--radius-full)", padding: "6px 14px",
          }}>
            <IconFire size={16} color={streak > 0 ? "#F97316" : "#9E9BB8"} />
            <Text style={{ fontSize: 13, fontWeight: 800, color: streak > 0 ? "#B45309" : "var(--color-text-tertiary)" }}>
              {streak} ngày</Text>
          </Box>
        </Box>

        {error ? <ErrorState onRetry={loadData} /> : (
          <>
            {/* ══════ COIN WALLET (compact) ══════ */}
            <Box style={{
              background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
              borderRadius: "var(--radius-xl)", padding: "20px 22px",
              position: "relative", overflow: "hidden",
            }}>
              <Box style={{
                position: "absolute", top: "-50%", right: "-30%",
                width: 180, height: 180, borderRadius: "50%",
                background: "rgba(255,255,255,0.08)", animation: "floatOrb 8s ease-in-out infinite",
              }} />
              <Box style={{ position: "relative", zIndex: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                  <Text style={{ fontSize: 11, color: "rgba(255,255,255,0.65)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Ví Coin học tập</Text>
                  <Box style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 4 }}>
                    {loading ? <Skeleton w={80} h={36} r={8} style={{ opacity: 0.3 }} /> : (
                      <Text style={{ fontSize: 36, fontWeight: 900, color: "white", letterSpacing: "-0.03em", lineHeight: 1 }}>
                        {animatedCoin.toLocaleString()}</Text>
                    )}
                    <Text style={{ fontSize: 13, color: "rgba(255,255,255,0.50)", fontWeight: 600 }}>Coin</Text>
                  </Box>
                </Box>
                <Box onClick={() => alert("Nạp xu qua ZaloPay...")} style={{
                  padding: "10px 18px", background: "rgba(255,255,255,0.18)",
                  backdropFilter: "blur(8px)", borderRadius: "var(--radius-md)",
                  border: "1px solid rgba(255,255,255,0.25)", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 6,
                }}>
                  <Text style={{ color: "white", fontWeight: 700, fontSize: 13 }}>Nạp Xu</Text>
                  <IconChevronRight size={14} color="rgba(255,255,255,0.7)" />
                </Box>
              </Box>
            </Box>

            {/* ══════ ROLE SWITCHER: Học Sinh / Giáo Viên ══════ */}
            <Box style={{
              display: "flex", gap: 0, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", padding: 4,
              border: "1px solid var(--color-border)",
            }}>
              {[
                { key: "student" as const, label: "📚 Học Sinh", count: studentFeatures.length },
                { key: "teacher" as const, label: "👩‍🏫 Giáo Viên", count: teacherFeatures.length },
              ].map(role => (
                <Box key={role.key} onClick={() => setActiveRole(role.key)} style={{
                  flex: 1, textAlign: "center", padding: "10px 0",
                  borderRadius: "var(--radius-full)", cursor: "pointer",
                  background: activeRole === role.key ? "var(--color-bg-card)" : "transparent",
                  boxShadow: activeRole === role.key ? "var(--shadow-sm)" : "none",
                  transition: "all 0.3s",
                }}>
                  <Text style={{
                    fontSize: 13, fontWeight: activeRole === role.key ? 800 : 600,
                    color: activeRole === role.key ? "var(--color-text-primary)" : "var(--color-text-tertiary)",
                  }}>{role.label}</Text>
                </Box>
              ))}
            </Box>

            {/* ══════ LEARNING STATS ROW ══════ */}
            <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              {[
                { label: "Tài liệu", value: docs.length, icon: <IconDoc size={20} color="#3B82F6" />, accent: "#3B82F6" },
                { label: "Flashcard", value: docs.reduce((a, d) => a + (d.flashcard_count || 0), 0), icon: <IconFlashcard size={20} color="#8B5CF6" />, accent: "#8B5CF6" },
                { label: "Quiz", value: docs.reduce((a, d) => a + (d.quiz_count || 0), 0), icon: <IconQuiz size={20} color="#EC4899" />, accent: "#EC4899" },
              ].map((s, idx) => (
                <Box key={idx} className="ch-stat-pill">
                  <Box style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>{s.icon}</Box>
                  {loading ? <Skeleton w={30} h={26} r={6} style={{ margin: "0 auto" }} /> : (
                    <Text style={{ fontSize: 24, fontWeight: 900, color: s.accent, letterSpacing: "-0.02em", lineHeight: 1 }}>
                      {s.value}</Text>
                  )}
                  <Text style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-tertiary)", marginTop: 4 }}>
                    {s.label}</Text>
                </Box>
              ))}
            </Box>

            {/* ══════ FEATURE CARDS ══════ */}
            <Box>
              <SectionHeader
                title={activeRole === "student" ? "Công cụ Học Sinh" : "Công cụ Giáo Viên"}
              />
              <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {features.map((f, idx) => (
                  <Box key={idx} onClick={f.action} className="ch-bento-card" style={{
                    display: "flex", flexDirection: "column",
                    padding: "16px 14px", borderRadius: 20, cursor: "pointer",
                    background: "white", border: "1px solid #E5E7EB",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                    position: "relative", overflow: "hidden",
                  }}>
                    {/* Decorative subtle background icon */}
                    <Box style={{
                      position: "absolute", right: -10, top: -5, opacity: 0.05,
                      fontSize: 60, pointerEvents: "none", filter: "grayscale(1)",
                    }}>{f.icon}</Box>
                    
                    <Box style={{
                      width: 42, height: 42, borderRadius: 14,
                      background: f.gradient,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      marginBottom: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                    }}>
                      <Text style={{ fontSize: 20, lineHeight: 1 }}>{f.icon}</Text>
                    </Box>
                    
                    <Text style={{
                      fontSize: 14, fontWeight: 800, color: "#1F2937",
                      marginBottom: 4, lineHeight: 1.3,
                    }}>{f.title}</Text>
                    
                    <Text style={{
                      fontSize: 11, color: "#6B7280", lineHeight: 1.4, fontWeight: 500,
                      display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden"
                    }}>{f.desc}</Text>
                  </Box>
                ))}
              </Box>
            </Box>

            {/* ══════ STREAK PROGRESS ══════ */}
            <Box style={{
              padding: "18px 20px", borderRadius: "var(--radius-xl)",
              background: streak > 0 ? "#FEF3C7" : "var(--color-bg-subtle)",
              border: `1px solid ${streak > 0 ? "rgba(245,158,11,0.2)" : "var(--color-border)"}`,
            }}>
              <Box style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                <IconFire size={24} color={streak > 0 ? "#F97316" : "#9E9BB8"} />
                <Box>
                  <Text style={{ fontSize: 14, fontWeight: 800, color: streak > 0 ? "#92400E" : "var(--color-text-primary)" }}>
                    Chuỗi học tập: {streak} ngày</Text>
                  <Text style={{ fontSize: 12, color: streak > 0 ? "#B45309" : "var(--color-text-tertiary)" }}>
                    {streakMaintained ? "✅ Đã hoàn thành hôm nay" : streak > 0 ? "⚠️ Hãy học để giữ streak!" : "Bắt đầu streak đầu tiên!"}
                  </Text>
                </Box>
              </Box>
              {/* 7-day streak visual */}
              <Box style={{ display: "flex", gap: 6, justifyContent: "space-between" }}>
                {["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map((day, i) => {
                  const isActive = i < streak % 7 || (streak >= 7);
                  const isToday = i === new Date().getDay() - 1 || (new Date().getDay() === 0 && i === 6);
                  return (
                    <Box key={i} style={{
                      flex: 1, textAlign: "center", padding: "6px 0",
                      borderRadius: "var(--radius-md)",
                      background: isActive ? "linear-gradient(135deg, #F59E0B, #EF4444)" : "var(--color-bg-card)",
                      border: isToday ? "2px solid #F97316" : `1px solid ${isActive ? "transparent" : "var(--color-border)"}`,
                    }}>
                      <Text style={{
                        fontSize: 10, fontWeight: 700,
                        color: isActive ? "white" : "var(--color-text-tertiary)",
                      }}>{day}</Text>
                      <Text style={{ fontSize: 12, lineHeight: 1 }}>{isActive ? "🔥" : "○"}</Text>
                    </Box>
                  );
                })}
              </Box>
            </Box>

            {/* ══════ DAILY TIP ══════ */}
            <Box style={{
              padding: "16px 18px", borderRadius: "var(--radius-xl)",
              background: "#F3E8FF", border: "1px solid rgba(139, 92, 246, 0.12)",
              display: "flex", alignItems: "flex-start", gap: 12,
            }}>
              <IconLightbulb size={22} color="#6D28D9" style={{ flexShrink: 0, marginTop: 2 }} />
              <Box>
                <Text style={{ fontSize: 13, fontWeight: 700, color: "#6D28D9", marginBottom: 4 }}>
                  Adaptive Learning</Text>
                <Text style={{ fontSize: 12, color: "#7C3AED", lineHeight: 1.5 }}>
                  Hệ thống SM-2 theo dõi điểm yếu của bạn. Câu nào làm sai sẽ tự động xuất hiện lại vào đúng thời điểm bạn sắp quên — giúp ghi nhớ tốt hơn 300%!</Text>
              </Box>
            </Box>

          </>
        )}
      </Box>
    </Page>
  );
}

export default AILearningPage;

import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { apiClient } from "../services/api";
import { IconChevronLeft, IconTrophy, IconUsers, IconTarget, IconLink } from "../components/icons";

interface QuizResult {
  user_id: string;
  display_name: string;
  avatar_url?: string;
  score: number;
  total: number;
  percentage: number;
  time_seconds: number;
  completed_at: string;
  attempt_number: number;
}

interface TeacherDashboardPageProps {
  quizId?: string;
}

function TeacherDashboardPage({ quizId }: TeacherDashboardPageProps) {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const [loading, setLoading] = useState(true);
  const [quizInfo, setQuizInfo] = useState<{ title: string; total_questions: number; share_code?: string } | null>(null);
  const [results, setResults] = useState<QuizResult[]>([]);
  const [stats, setStats] = useState<{ total_students: number; average_score: number; average_percentage: number } | null>(null);
  const [showShareLink, setShowShareLink] = useState(false);

  useEffect(() => {
    if (!user_id || !quizId) return;
    loadResults();
  }, [user_id, quizId]);

  const loadResults = async () => {
    setLoading(true);
    try {
      const userId = user_id || "";
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/teacher/quiz/${quizId}/results`,
        {
          headers: {
            "X-User-Id": userId,
          },
        }
      );

      const data = await response.json();
      if (data.quiz_id) {
        setQuizInfo({ title: data.title, total_questions: data.total_questions });
        setStats({
          total_students: data.total_students,
          average_score: data.average_score,
          average_percentage: data.average_percentage,
        });
        setResults(data.results || []);
      }
    } catch (err) {
      console.error("Failed to load results:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}p ${secs}s`;
  };

  const getGradeColor = (percentage: number) => {
    if (percentage >= 80) return "#10B981";
    if (percentage >= 60) return "#3B82F6";
    if (percentage >= 40) return "#F59E0B";
    return "#EF4444";
  };

  const generateShareCode = async () => {
    if (!quizId) return;
    setLoading(true);
    try {
      const userId = user_id || "";
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/shared-quiz/create`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-Id": userId,
          },
          body: JSON.stringify({
            user_id: userId,
            doc_id: quizId,
            title: quizInfo?.title || "Quiz",
            subject: "tong_hop",
            chapter: "",
          }),
        }
      );
      const data = await response.json();
      if (data.success) {
        setQuizInfo((prev) => prev ? { ...prev, share_code: data.share_code } : null);
        setShowShareLink(true);
        if (window.ZMP) window.ZMP.hapticFeedback("light");
      }
    } catch (err) {
      console.error("Failed to generate share code:", err);
      alert("Không thể tạo link share. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const copyShareLink = () => {
    if (!quizInfo?.share_code) return;
    const link = `${window.location.origin}/quiz/${quizInfo.share_code}`;
    navigator.clipboard.writeText(link);
    alert("✅ Đã copy link!");
    if (window.ZMP) window.ZMP.hapticFeedback("medium");
  };

  return (
    <Page className="ch-page">
      <Box className="ch-container" style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 16 }}>
        {/* Header */}
        <Box style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <Box
            onClick={() => navigate("/")}
            style={{
              width: 38,
              height: 38,
              borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)",
              border: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
            }}
          >
            <IconChevronLeft size={18} />
          </Box>
          <Box>
            <Text className="ch-caption" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>
              GIÁO VIÊN
            </Text>
            <Text className="ch-heading-lg" style={{ marginTop: 2 }}>
              📊 Dashboard Lớp Học
            </Text>
          </Box>
        </Box>

        {!loading && stats && (
          <>
            {/* Quiz Info Card */}
            <Box
              style={{
                padding: "18px 20px",
                borderRadius: "var(--radius-xl)",
                background: "linear-gradient(135deg, #667EEA, #764BA2)",
                color: "white",
              }}
            >
              <Text style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>{quizInfo?.title}</Text>
              <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                <Box>
                  <Box style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <IconUsers size={14} />
                    <Text style={{ fontSize: 11, opacity: 0.8 }}>Học sinh</Text>
                  </Box>
                  <Text style={{ fontSize: 24, fontWeight: 900 }}>{stats.total_students}</Text>
                </Box>
                <Box>
                  <Box style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <IconTarget size={14} />
                    <Text style={{ fontSize: 11, opacity: 0.8 }}>Trung bình</Text>
                  </Box>
                  <Text style={{ fontSize: 24, fontWeight: 900 }}>{Math.round(stats.average_percentage)}%</Text>
                </Box>
                <Box>
                  <Box style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <IconTrophy size={14} />
                    <Text style={{ fontSize: 11, opacity: 0.8 }}>Điểm cao</Text>
                  </Box>
                  <Text style={{ fontSize: 24, fontWeight: 900 }}>
                    {results.length > 0 ? Math.round((results[0].score / results[0].total) * 100) : 0}%
                  </Text>
                </Box>
              </Box>
            </Box>

            {/* Share Link Section */}
            {showShareLink && quizInfo?.share_code && (
              <Box style={{ marginTop: 12 }}>
                <Text style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                  🔗 Link chia sẻ quiz:
                </Text>
                <Box
                  onClick={copyShareLink}
                  style={{
                    padding: "12px 16px",
                    borderRadius: "var(--radius-lg)",
                    background: "linear-gradient(135deg, #10B981, #059669)",
                    color: "white",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(16,185,129,0.3)",
                  }}
                >
                  <IconLink size={18} color="white" />
                  <Text style={{ flex: 1, fontSize: 13, fontWeight: 600, wordBreak: "break-all" }}>
                    {window.location.origin}/quiz/{quizInfo.share_code}
                  </Text>
                  <Text style={{ fontSize: 16 }}>📋</Text>
                </Box>
                <Text style={{ fontSize: 11, color: "var(--color-text-tertiary)", marginTop: 6 }}>
                  Chạm để copy link — gửi cho học sinh qua Zalo
                </Text>
              </Box>
            )}

            {!showShareLink && (
              <Box
                onClick={generateShareCode}
                style={{
                  marginTop: 12,
                  padding: "14px",
                  borderRadius: "var(--radius-lg)",
                  background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  cursor: "pointer",
                  boxShadow: "0 4px 12px rgba(99,102,241,0.3)",
                }}
              >
                <IconLink size={18} color="white" />
                <Text style={{ fontSize: 14, fontWeight: 700 }}>Tạo link share quiz</Text>
              </Box>
            )}

            {/* Results List */}
            <Box>
              <Text
                style={{
                  fontSize: 13,
                  fontWeight: 800,
                  color: "var(--color-text-tertiary)",
                  marginBottom: 10,
                  paddingLeft: 4,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                📋 Kết Quả Làm Bài
              </Text>

              <Box
                style={{
                  background: "white",
                  borderRadius: "var(--radius-xl)",
                  border: "1px solid var(--color-border)",
                  overflow: "hidden",
                }}
              >
                {results.length === 0 ? (
                  <Box
                    style={{
                      padding: "40px 20px",
                      textAlign: "center",
                    }}
                  >
                    <Text style={{ fontSize: 48 }}>📭</Text>
                    <Text style={{ fontSize: 14, fontWeight: 700, marginTop: 12, color: "var(--color-text-secondary)" }}>
                      Chưa có học sinh nào làm bài
                    </Text>
                    <Text style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 4 }}>
                      Hãy share link quiz cho lớp nhé!
                    </Text>
                  </Box>
                ) : (
                  results.map((result, index) => (
                    <Box
                      key={result.user_id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        padding: "14px 16px",
                        borderTop: index > 0 ? "1px solid var(--color-border)" : "none",
                        background: index < 3 ? "linear-gradient(90deg, rgba(251,191,36,0.05), transparent)" : "white",
                      }}
                    >
                      {/* Rank */}
                      <Box style={{ width: 32, textAlign: "center", marginRight: 12 }}>
                        {index === 0 ? (
                          <Text style={{ fontSize: 20 }}>🥇</Text>
                        ) : index === 1 ? (
                          <Text style={{ fontSize: 20 }}>🥈</Text>
                        ) : index === 2 ? (
                          <Text style={{ fontSize: 20 }}>🥉</Text>
                        ) : (
                          <Text style={{ fontSize: 14, fontWeight: 800, color: "var(--color-text-secondary)" }}>#{index + 1}</Text>
                        )}
                      </Box>

                      {/* Avatar/Name */}
                      <Box style={{ flex: 1 }}>
                        <Text
                          style={{
                            fontSize: 14,
                            fontWeight: 700,
                            color: "var(--color-text-primary)",
                          }}
                        >
                          {result.display_name}
                        </Text>
                        <Box style={{ display: "flex", gap: 8, marginTop: 2 }}>
                          <Box
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 2,
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: "rgba(99,102,241,0.1)",
                            }}
                          >
                            <Text style={{ fontSize: 9, fontWeight: 700, color: "#6366F1" }}>
                              {formatTime(result.time_seconds)}
                            </Text>
                          </Box>
                          <Text style={{ fontSize: 10, color: "var(--color-text-tertiary)", fontWeight: 600 }}>
                            Lần {result.attempt_number}
                          </Text>
                        </Box>
                      </Box>

                      {/* Score */}
                      <Box style={{ textAlign: "right" }}>
                        <Text
                          style={{
                            fontSize: 18,
                            fontWeight: 900,
                            color: getGradeColor(result.percentage),
                          }}
                        >
                          {result.score}/{result.total}
                        </Text>
                        <Text
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: getGradeColor(result.percentage),
                          }}
                        >
                          {Math.round(result.percentage)}%
                        </Text>
                      </Box>
                    </Box>
                  ))
                )}
              </Box>
            </Box>

            {/* Refresh Button */}
            <Box
              onClick={loadResults}
              style={{
                padding: "14px",
                borderRadius: "var(--radius-lg)",
                background: "var(--color-bg-subtle)",
                border: "1px solid var(--color-border)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <Text style={{ fontSize: 16 }}>🔄</Text>
              <Text style={{ fontSize: 13, fontWeight: 700 }}>Làm mới dữ liệu</Text>
            </Box>
          </>
        )}

        {loading && (
          <Box
            style={{
              padding: 20,
              background: "white",
              borderRadius: "var(--radius-xl)",
              border: "1px solid var(--color-border)",
            }}
          >
            {[1, 2, 3, 4, 5].map((i) => (
              <Box
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "12px 0",
                  borderBottom: i < 5 ? "1px solid var(--color-border)" : "none",
                }}
              >
                <Box
                  style={{
                    width: 32,
                    height: 20,
                    borderRadius: 4,
                    background: "var(--color-bg-subtle)",
                    marginRight: 12,
                  }}
                />
                <Box
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: "50%",
                    background: "var(--color-bg-subtle)",
                    marginRight: 12,
                  }}
                />
                <Box style={{ flex: 1 }}>
                  <Box
                    style={{
                      width: 100,
                      height: 14,
                      borderRadius: 4,
                      background: "var(--color-bg-subtle)",
                      marginBottom: 6,
                    }}
                  />
                  <Box
                    style={{
                      width: 60,
                      height: 10,
                      borderRadius: 4,
                      background: "var(--color-bg-subtle)",
                    }}
                  />
                </Box>
                <Box
                  style={{
                    width: 50,
                    height: 20,
                    borderRadius: 4,
                    background: "var(--color-bg-subtle)",
                  }}
                />
              </Box>
            ))}
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default TeacherDashboardPage;
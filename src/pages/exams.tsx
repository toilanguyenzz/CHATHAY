/* ─── Exam Library Page - Kho Đề Thi Công Cộng ─── */
import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { IconDoc, IconChevronRight, IconChevronLeft, IconRefresh } from "../components/icons";

interface Exam {
  id: string;
  name: string;
  doc_type: string;
  quiz_count: number;
  flashcard_count: number;
  created_at: number;
}

function ExamLibraryPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterSubject, setFilterSubject] = useState("all");
  const refreshTimeout = useRef<NodeJS.Timeout>();

  const loadExams = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.get<Exam[]>("/api/miniapp/public-exams");
      setExams(data || []);
    } catch (err) {
      setError("Không thể tải danh sách đề thi. Vui lòng thử lại.");
      console.error("Load exams error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadExams();
  }, [loadExams]);

  // Pull-to-refresh handler
  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    await loadExams();
  };

  // Auto-refresh every 30s to get new exams
  useEffect(() => {
    const interval = setInterval(loadExams, 30000);
    return () => clearInterval(interval);
  }, [loadExams]);

  // Filter logic
  const filteredExams = filterSubject === "all"
    ? exams
    : exams.filter(e => e.name.toLowerCase().includes(filterSubject));

  // Group by subject
  const subjects = [
    { key: "all", label: "Tất cả", emoji: "📚" },
    { key: "toan", label: "Toán", emoji: "🧮" },
    { key: "ly", label: "Lý", emoji: "⚡" },
    { key: "hoa", label: "Hóa", emoji: "🧪" },
    { key: "sinh", label: "Sinh", emoji: "🌱" },
    { key: "su", label: "Sử", emoji: "📜" },
    { key: "dia", label: "Địa", emoji: "🗺️" },
    { key: "anh", label: "Anh", emoji: "🇬🇧" },
    { key: "van", label: "Văn", emoji: "📖" },
  ];

  if (loading) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 80px)" }}>
          <Box style={{ textAlign: "center" }}>
            <Box style={{
              width: 48, height: 48, borderRadius: "50%",
              border: "3px solid var(--color-border)",
              borderTopColor: "var(--color-primary)",
              animation: "spin 1s linear infinite",
              margin: "0 auto 16px"
            }} />
            <Text style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>Đang tải đề thi...</Text>
          </Box>
        </Box>
      </Page>
    );
  }

  return (
    <Page className="ch-page" onRefresh={handleRefresh}>
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 16, paddingBottom: 24 }}>

        {/* HEADER */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Box onClick={() => navigate("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            }}>
              <IconChevronLeft size={18} color="var(--color-text-secondary)" />
            </Box>
            <Box>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 800, color: "var(--color-text-primary)" }}>
                📚 Kho Đề Thi
              </Text>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)" }}>
                {exams.length} đề thi đã sẵn sàng
              </Text>
            </Box>
          </Box>
          <Box onClick={handleRefresh} style={{
            width: 38, height: 38, borderRadius: "var(--radius-full)",
            background: refreshing ? "var(--gradient-primary)" : "var(--color-bg-subtle)",
            display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            transition: "all 0.3s",
          }}>
            <IconRefresh size={18} color={refreshing ? "white" : "var(--color-text-secondary)"} />
          </Box>
        </Box>

        {/* SUBJECT FILTER */}
        <Box style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8 }}>
          {subjects.map(sub => (
            <Box
              key={sub.key}
              onClick={() => setFilterSubject(sub.key)}
              style={{
                padding: "8px 16px", borderRadius: "var(--radius-full)",
                background: filterSubject === sub.key ? "var(--gradient-primary)" : "var(--color-bg-subtle)",
                color: filterSubject === sub.key ? "white" : "var(--color-text-secondary)",
                fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", cursor: "pointer",
                border: filterSubject === sub.key ? "none" : "1px solid var(--color-border)",
                flexShrink: 0, transition: "all 0.2s",
              }}
            >
              {sub.emoji} {sub.label}
            </Box>
          ))}
        </Box>

        {/* ERROR STATE */}
        {error && (
          <Box style={{
            padding: 16, borderRadius: "var(--radius-lg)",
            background: "#FEE2E2", border: "1px solid #EF4444",
          }}>
            <Text style={{ fontSize: 13, color: "#991B1B" }}>{error}</Text>
            <Box onClick={loadExams} style={{
              marginTop: 8, padding: "6px 12px", borderRadius: "var(--radius-md)",
              background: "#EF4444", color: "white", fontSize: 12, fontWeight: 700,
              display: "inline-block", cursor: "pointer",
            }}>
              Thử lại
            </Box>
          </Box>
        )}

        {/* EXAMS LIST */}
        {filteredExams.length === 0 ? (
          <Box style={{
            textAlign: "center", padding: 48,
            background: "var(--color-bg-subtle)", borderRadius: "var(--radius-xl)",
          }}>
            <Text style={{ fontSize: 48, marginBottom: 12 }}>📭</Text>
            <Text style={{ fontSize: 16, fontWeight: 700, color: "var(--color-text-secondary)" }}>
              Chưa có đề thi nào
            </Text>
            <Text style={{ fontSize: 13, color: "var(--color-text-tertiary)", marginTop: 4 }}>
              Hãy chờ giáo viên upload đề nhé!
            </Text>
          </Box>
        ) : (
          <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filteredExams.map((exam, idx) => (
              <Box
                key={exam.id}
                onClick={() => navigate(`/quiz?doc_id=${exam.id}`)}
                style={{
                  padding: "16px", borderRadius: "var(--radius-xl)",
                  background: "var(--color-bg-card)", border: "1px solid var(--color-border)",
                  display: "flex", alignItems: "center", gap: 14, cursor: "pointer",
                  transition: "all 0.2s", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                }}
              >
                {/* Icon */}
                <Box style={{
                  width: 52, height: 52, borderRadius: 14,
                  background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0,
                }}>
                  <IconDoc size={26} color="#6366F1" />
                </Box>

                {/* Info */}
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{
                    fontSize: 15, fontWeight: 800, color: "var(--color-text-primary)",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    marginBottom: 4,
                  }}>
                    {exam.name}
                  </Text>
                  <Box style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {exam.quiz_count > 0 && (
                      <Box style={{
                        padding: "4px 10px", borderRadius: "var(--radius-md)",
                        background: "linear-gradient(135deg, #10B981, #34D399)",
                        color: "white", fontSize: 11, fontWeight: 800,
                      }}>
                        {exam.quiz_count} câu Quiz
                      </Box>
                    )}
                    {exam.flashcard_count > 0 && (
                      <Box style={{
                        padding: "4px 10px", borderRadius: "var(--radius-md)",
                        background: "linear-gradient(135deg, #F59E0B, #FBBF24)",
                        color: "white", fontSize: 11, fontWeight: 800,
                      }}>
                        {exam.flashcard_count} thẻ
                      </Box>
                    )}
                  </Box>
                </Box>

                {/* Arrow */}
                <Box style={{ color: "var(--color-text-tertiary)" }}>
                  <IconChevronRight size={20} />
                </Box>
              </Box>
            ))}
          </Box>
        )}

        {/* FOOTER */}
        <Box style={{ textAlign: "center", marginTop: 16 }}>
          <Text style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>
            🤖 Cập nhật tự động mỗi 30 giây
          </Text>
        </Box>
      </Box>
    </Page>
  );
}

export default ExamLibraryPage;
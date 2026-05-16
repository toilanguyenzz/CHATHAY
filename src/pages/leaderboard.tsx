import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { apiClient } from "../services/api";
import { IconChevronLeft, IconFire, IconTrophy, IconUser } from "../components/icons";

interface Student {
  id: string;
  name: string;
  avatar?: string;
  quiz_score: number;
  quiz_count: number;
  flashcard_count: number;
  streak: number;
  rank?: number;
}

interface ClassData {
  id: string;
  name: string;
  student_count: number;
  avg_score: number;
}

function LeaderboardPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const [loading, setLoading] = useState(true);
  const [selectedClass, setSelectedClass] = useState<string>("my-class");
  const [currentClass, setCurrentClass] = useState<ClassData | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [userRank, setUserRank] = useState<number>(0);

  // Mock data for demo
  const mockStudents: Student[] = [
    { id: "1", name: "Nguyễn Văn A", quiz_score: 950, quiz_count: 28, flashcard_count: 156, streak: 12, rank: 1 },
    { id: "2", name: "Trần Thị B", quiz_score: 880, quiz_count: 24, flashcard_count: 142, streak: 10, rank: 2 },
    { id: "3", name: "Lê Văn C", quiz_score: 820, quiz_count: 22, flashcard_count: 128, streak: 8, rank: 3 },
    { id: "4", name: "Phạm Thu D", quiz_score: 780, quiz_count: 20, flashcard_count: 115, streak: 7, rank: 4 },
    { id: "5", name: "Vũ Đình E", quiz_score: 750, quiz_count: 19, flashcard_count: 108, streak: 6, rank: 5 },
    { id: "6", name: "Hoàng Mai F", quiz_score: 720, quiz_count: 18, flashcard_count: 95, streak: 5, rank: 6 },
    { id: "7", name: "Đỗ Minh G", quiz_score: 680, quiz_count: 16, flashcard_count: 88, streak: 4, rank: 7 },
    { id: "8", name: "Ngô Thị H", quiz_score: 650, quiz_count: 15, flashcard_count: 82, streak: 4, rank: 8 },
    { id: "9", name: "Bùi Văn I", quiz_score: 620, quiz_count: 14, flashcard_count: 75, rank: 9, streak: 3 },
    { id: "10", name: "Đặng Thu J", quiz_score: 580, quiz_count: 13, flashcard_count: 68, streak: 2, rank: 10 },
  ];

  const mockClasses: ClassData[] = [
    { id: "class-1", name: "Lớp 12A1", student_count: 45, avg_score: 72 },
    { id: "class-2", name: "Lớp 12A2", student_count: 42, avg_score: 68 },
    { id: "class-3", name: "Lớp 11A5", student_count: 38, avg_score: 75 },
  ];

  useEffect(() => {
    if (!user_id) return;
    apiClient.setUserId(user_id);
    loadLeaderboard();
  }, [user_id, selectedClass]);

  const loadLeaderboard = () => {
    setLoading(true);
    // In production, fetch from API here
    setTimeout(() => {
      setStudents(mockStudents);
      setCurrentClass(mockClasses[0]);
      // Find user rank (mock: user is at rank 5)
      setUserRank(5);
      setLoading(false);
    }, 800);
  };

  const getMedal = (rank: number) => {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return null;
  };

  const getRankColor = (rank: number) => {
    if (rank === 1) return "#F59E0B";
    if (rank === 2) return "#9CA3AF";
    if (rank === 3) return "#B45309";
    return "var(--color-text-secondary)";
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
              LEADERBOARD
            </Text>
            <Text className="ch-heading-lg" style={{ marginTop: 2 }}>
              🏆 Bảng Xếp Hạng
            </Text>
          </Box>
        </Box>

        {/* Class Selector */}
        <Box
          style={{
            display: "flex",
            gap: 8,
            padding: 4,
            background: "var(--color-bg-subtle)",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-border)",
          }}
        >
          {[
            { key: "my-class", label: "Lớp tôi" },
            { key: "school", label: "Toàn trường" },
            { key: "top", label: "Top Việt Nam" },
          ].map((tab) => (
            <Box
              key={tab.key}
              onClick={() => setSelectedClass(tab.key)}
              style={{
                flex: 1,
                textAlign: "center",
                padding: "10px 0",
                borderRadius: "var(--radius-full)",
                cursor: "pointer",
                background: selectedClass === tab.key ? "white" : "transparent",
                boxShadow: selectedClass === tab.key ? "var(--shadow-sm)" : "none",
                transition: "all 0.2s",
              }}
            >
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: selectedClass === tab.key ? 800 : 600,
                  color: selectedClass === tab.key ? "var(--color-text-primary)" : "var(--color-text-tertiary)",
                }}
              >
                {tab.label}
              </Text>
            </Box>
          ))}
        </Box>

        {/* Class Stats */}
        {!loading && currentClass && (
          <Box
            style={{
              padding: "18px 20px",
              borderRadius: "var(--radius-xl)",
              background: "linear-gradient(135deg, #667EEA, #764BA2)",
              color: "white",
            }}
          >
            <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Box>
                <Text style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{currentClass.name}</Text>
                <Box style={{ display: "flex", gap: 16 }}>
                  <Box>
                    <Text style={{ fontSize: 20, fontWeight: 900 }}>{currentClass.student_count}</Text>
                    <Text style={{ fontSize: 10, color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>Học sinh</Text>
                  </Box>
                  <Box>
                    <Text style={{ fontSize: 20, fontWeight: 900 }}>{currentClass.avg_score}</Text>
                    <Text style={{ fontSize: 10, color: "rgba(255,255,255,0.7)", fontWeight: 600 }}>ĐTB</Text>
                  </Box>
                </Box>
              </Box>
              <Box
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <IconTrophy size={20} />
              </Box>
            </Box>
          </Box>
        )}

        {/* Top 3 Podium */}
        {!loading && (
          <Box style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 8, marginBottom: 16 }}>
            {/* 2nd Place */}
            {students[1] && (
              <Box
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  width: 80,
                }}
              >
                <Box
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #9CA3AF, #6B7280)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 4,
                    border: "3px solid white",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                  }}
                >
                  <Text style={{ fontSize: 20 }}>{getMedal(2) || "👤"}</Text>
                </Box>
                <Text
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#6B7280",
                    maxWidth: 70,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {students[1].name.split(" ").pop()}
                </Text>
                <Text style={{ fontSize: 14, fontWeight: 900, color: "#6B7280" }}>{students[1].quiz_score}</Text>
                <Box
                  style={{
                    width: "100%",
                    height: 60,
                    background: "linear-gradient(180deg, #E5E7EB, #D1D5DB)",
                    borderRadius: "8px 8px 0 0",
                  }}
                />
              </Box>
            )}

            {/* 1st Place */}
            {students[0] && (
              <Box
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  width: 90,
                }}
              >
                <Box
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #F59E0B, #FBBF24)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 4,
                    border: "3px solid white",
                    boxShadow: "0 6px 16px rgba(245,158,11,0.3)",
                  }}
                >
                  <Text style={{ fontSize: 24 }}>{getMedal(1) || "👤"}</Text>
                </Box>
                <Text
                  style={{
                    fontSize: 11,
                    fontWeight: 800,
                    color: "#F59E0B",
                    maxWidth: 80,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {students[0].name.split(" ").pop()}
                </Text>
                <Text style={{ fontSize: 16, fontWeight: 900, color: "#F59E0B" }}>{students[0].quiz_score}</Text>
                <Box
                  style={{
                    width: "100%",
                    height: 80,
                    background: "linear-gradient(180deg, #F59E0B, #FBBF24)",
                    borderRadius: "8px 8px 0 0",
                  }}
                />
              </Box>
            )}

            {/* 3rd Place */}
            {students[2] && (
              <Box
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  width: 80,
                }}
              >
                <Box
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #B45309, #D97706)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 4,
                    border: "3px solid white",
                    boxShadow: "0 4px 12px rgba(180,83,9,0.3)",
                  }}
                >
                  <Text style={{ fontSize: 20 }}>{getMedal(3) || "👤"}</Text>
                </Box>
                <Text
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#92400E",
                    maxWidth: 70,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {students[2].name.split(" ").pop()}
                </Text>
                <Text style={{ fontSize: 14, fontWeight: 900, color: "#92400E" }}>{students[2].quiz_score}</Text>
                <Box
                  style={{
                    width: "100%",
                    height: 45,
                    background: "linear-gradient(180deg, #D97706, #B45309)",
                    borderRadius: "8px 8px 0 0",
                  }}
                />
              </Box>
            )}
          </Box>
        )}

        {/* Full Leaderboard List */}
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
            📋 Danh Sách Xếp Hạng
          </Text>

          {!loading ? (
            <Box
              style={{
                background: "white",
                borderRadius: "var(--radius-xl)",
                border: "1px solid var(--color-border)",
                overflow: "hidden",
              }}
            >
              {students.slice(3).map((student, index) => (
                <Box
                  key={student.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "14px 16px",
                    borderTop: index > 0 ? "1px solid var(--color-border)" : "none",
                    background: student.id === user_id ? "rgba(99,102,241,0.05)" : "white",
                  }}
                >
                  {/* Rank */}
                  <Box style={{ width: 32, textAlign: "center" }}>
                    {student.rank === 1 ? (
                      <Text style={{ fontSize: 20 }}>🥇</Text>
                    ) : student.rank === 2 ? (
                      <Text style={{ fontSize: 20 }}>🥈</Text>
                    ) : student.rank === 3 ? (
                      <Text style={{ fontSize: 20 }}>🥉</Text>
                    ) : (
                      <Text
                        style={{
                          fontSize: 14,
                          fontWeight: 800,
                          color: getRankColor(student.rank || index + 4),
                        }}
                      >
                        #{student.rank || index + 4}
                      </Text>
                    )}
                  </Box>

                  {/* Avatar */}
                  <Box
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #667EEA, #764BA2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginRight: 12,
                    }}
                  >
                    <IconUser size={20} color="white" />
                  </Box>

                  {/* Info */}
                  <Box style={{ flex: 1 }}>
                    <Text
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: student.id === user_id ? "#6366F1" : "var(--color-text-primary)",
                      }}
                    >
                      {student.name}
                      {student.id === user_id && (
                        <Text style={{ fontSize: 10, color: "#6366F1", fontWeight: 600, marginLeft: 4 }}>
                          (Bạn)
                        </Text>
                      )}
                    </Text>
                    <Box style={{ display: "flex", gap: 8, marginTop: 2 }}>
                      <Box
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 2,
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "rgba(234,179,8,0.1)",
                        }}
                      >
                        <IconFire size={10} color="#EAB308" />
                        <Text style={{ fontSize: 9, fontWeight: 700, color: "#854D0E" }}>
                          {student.streak} ngày
                        </Text>
                      </Box>
                      <Text style={{ fontSize: 10, color: "var(--color-text-tertiary)", fontWeight: 600 }}>
                        {student.quiz_count} quiz
                      </Text>
                    </Box>
                  </Box>

                  {/* Score */}
                  <Box style={{ textAlign: "right" }}>
                    <Text
                      style={{
                        fontSize: 16,
                        fontWeight: 900,
                        color: "var(--color-primary)",
                      }}
                    >
                      {student.quiz_score}
                    </Text>
                    <Text style={{ fontSize: 9, color: "var(--color-text-tertiary)", fontWeight: 600 }}>
                      điểm
                    </Text>
                  </Box>
                </Box>
              ))}
            </Box>
          ) : (
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
                      width: 40,
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

        {/* Your Rank Card */}
        {!loading && (
          <Box
            style={{
              padding: "16px",
              borderRadius: "var(--radius-xl)",
              background: "linear-gradient(135deg, #10B981, #059669)",
              color: "white",
              marginTop: 8,
            }}
          >
            <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Box>
                <Text style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, opacity: 0.9 }}>Xếp hạng của bạn</Text>
                <Box style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <Text style={{ fontSize: 28, fontWeight: 900 }}>#{userRank}</Text>
                  <Text style={{ fontSize: 12, fontWeight: 600, opacity: 0.9 }}>/ {students.length} học sinh</Text>
                </Box>
              </Box>
              <Box style={{ textAlign: "right" }}>
                <Text style={{ fontSize: 24, fontWeight: 900 }}>{mockStudents.find((s) => s.id === user_id)?.quiz_score || 0}</Text>
                <Text style={{ fontSize: 10, fontWeight: 600, opacity: 0.9 }}>điểm</Text>
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default LeaderboardPage;
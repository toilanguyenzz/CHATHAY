import { Box, Text } from "zmp-ui";

export interface QuizShareCardProps {
  score: number;
  total: number;
  percentage: number;
  docName?: string;
  className?: string;
}

export function QuizShareCard({ score, total, percentage, docName }: QuizShareCardProps) {
  const getGrade = () => {
    if (percentage >= 90) return { emoji: "🏆", title: "Xuất sắc!", color: "#F59E0B" };
    if (percentage >= 80) return { emoji: "⭐", title: "Rất giỏi!", color: "#10B981" };
    if (percentage >= 70) return { emoji: "👍", title: "Khá tốt", color: "#3B82F6" };
    if (percentage >= 60) return { emoji: "📚", title: "Trung bình", color: "#8B5CF6" };
    return { emoji: "💪", title: "Cố gắng!", color: "#EF4444" };
  };

  const grade = getGrade();

  const handleCopyImage = async () => {
    alert("Tính năng tạo ảnh đang được phát triển! Hiện tại đang copy text thay thế.");
    const text = `${grade.emoji} ${grade.title}\n📊 ${score}/${total} (${percentage}%)\n📚 ${docName || "Quiz"}\n\nHọc cùng ChatHay: chathay.vn`;
    navigator.clipboard?.writeText(text);
  };

  return (
    <Box
      className="quiz-share-card"
      style={{
        width: 320,
        padding: 0,
        borderRadius: 20,
        background: "linear-gradient(135deg, #667EEA, #764BA2)",
        boxShadow: "0 10px 40px rgba(102,126,234,0.3)",
        overflow: "hidden",
        fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {/* Header */}
      <Box
        style={{
          padding: "24px 24px 16px",
          textAlign: "center",
          background: "rgba(255,255,255,0.1)",
        }}
      >
        <Text style={{ fontSize: 48, lineHeight: 1 }}>{grade.emoji}</Text>
        <Text
          style={{
            fontSize: 24,
            fontWeight: 900,
            color: "white",
            marginTop: 8,
            letterSpacing: "-0.02em",
          }}
        >
          {grade.title}
        </Text>
      </Box>

      {/* Score Section */}
      <Box
        style={{
          padding: "24px",
          background: "white",
          margin: 16,
          borderRadius: 16,
          textAlign: "center",
          boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
        }}
      >
        <Text
          style={{
            fontSize: 56,
            fontWeight: 900,
            color: grade.color,
            lineHeight: 1,
            marginBottom: 8,
          }}
        >
          {score}<span style={{ fontSize: 32, color: "#9CA3AF", fontWeight: 600 }}>/</span>
          <span style={{ fontSize: 32, color: "#9CA3AF", fontWeight: 600 }}>{total}</span>
        </Text>
        <Box
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            borderRadius: "full",
            background: `${grade.color}20`,
            width: "fit-content",
            margin: "0 auto",
          }}
        >
          <Text style={{ fontSize: 14, fontWeight: 800, color: grade.color }}>{percentage}% chính xác</Text>
        </Box>
      </Box>

      {/* Document Info */}
      {docName && (
        <Box
          style={{
            padding: "0 24px 16px",
          }}
        >
          <Box
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 16px",
              borderRadius: 12,
              background: "rgba(255,255,255,0.1)",
            }}
          >
            <Text style={{ fontSize: 16 }}>📚</Text>
            <Text
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "white",
                flex: 1,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {docName}
            </Text>
          </Box>
        </Box>
      )}

      {/* Footer */}
      <Box
        style={{
          padding: "16px 24px 24px",
          textAlign: "center",
          background: "rgba(0,0,0,0.1)",
        }}
      >
        <Text
          style={{
            fontSize: 12,
            color: "rgba(255,255,255,0.7)",
            fontWeight: 600,
            letterSpacing: "0.05em",
          }}
        >
          ChatHay - Học Vui Thi Giỏi
        </Text>
        <Text
          style={{
            fontSize: 11,
            color: "rgba(255,255,255,0.5)",
            marginTop: 4,
          }}
        >
          chathay.vn
        </Text>
      </Box>

      {/* Copy Button */}
      <Box
        onClick={handleCopyImage}
        style={{
          position: "absolute",
          top: 12,
          right: 12,
          padding: "8px 12px",
          borderRadius: 8,
          background: "rgba(255,255,255,0.2)",
          backdropFilter: "blur(8px)",
          cursor: "pointer",
        }}
      >
        <Text style={{ fontSize: 10, color: "white", fontWeight: 700 }}>📋 Copy</Text>
      </Box>
    </Box>
  );
}

export interface FlashcardShareCardProps {
  reviewed: number;
  remembered: number;
  forgotten: number;
  docName?: string;
}

export function FlashcardShareCard({ reviewed, remembered, forgotten, docName }: FlashcardShareCardProps) {
  const percent = Math.round((remembered / reviewed) * 100) || 0;

  return (
    <Box
      style={{
        width: 320,
        padding: 0,
        borderRadius: 20,
        background: "linear-gradient(135deg, #F59E0B, #EF4444)",
        boxShadow: "0 10px 40px rgba(245,158,11,0.3)",
        overflow: "hidden",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Header */}
      <Box
        style={{
          padding: "24px 24px 16px",
          textAlign: "center",
          background: "rgba(255,255,255,0.1)",
        }}
      >
        <Text style={{ fontSize: 48, lineHeight: 1 }}>🗂️</Text>
        <Text
          style={{
            fontSize: 24,
            fontWeight: 900,
            color: "white",
            marginTop: 8,
          }}
        >
          Flashcard Done!
        </Text>
      </Box>

      {/* Stats */}
      <Box
        style={{
          padding: "24px",
          background: "white",
          margin: 16,
          borderRadius: 16,
        }}
      >
        <Box
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 12,
            textAlign: "center",
          }}
        >
          <Box>
            <Text
              style={{
                fontSize: 32,
                fontWeight: 900,
                color: "#10B981",
                lineHeight: 1,
              }}
            >
              {remembered}
            </Text>
            <Text
              style={{
                fontSize: 11,
                color: "#9CA3AF",
                fontWeight: 600,
                marginTop: 4,
              }}
            >
              Đã thuộc
            </Text>
          </Box>
          <Box>
            <Text
              style={{
                fontSize: 32,
                fontWeight: 900,
                color: "#EF4444",
                lineHeight: 1,
              }}
            >
              {forgotten}
            </Text>
            <Text
              style={{
                fontSize: 11,
                color: "#9CA3AF",
                fontWeight: 600,
                marginTop: 4,
              }}
            >
              Chưa nhớ
            </Text>
          </Box>
          <Box>
            <Text
              style={{
                fontSize: 32,
                fontWeight: 900,
                color: "#3B82F6",
                lineHeight: 1,
              }}
            >
              {reviewed}
            </Text>
            <Text
              style={{
                fontSize: 11,
                color: "#9CA3AF",
                fontWeight: 600,
                marginTop: 4,
              }}
            >
              Tổng
            </Text>
          </Box>
        </Box>

        {/* Progress Bar */}
        <Box
          style={{
            marginTop: 16,
            padding: "12px",
            borderRadius: 8,
            background: "#F3F4F6",
          }}
        >
          <Box
            style={{
              width: `${percent}%`,
              height: 8,
              borderRadius: 4,
              background: "linear-gradient(90deg, #10B981, #059669)",
              transition: "width 0.3s",
            }}
          />
          <Text
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: "#6B7280",
              marginTop: 6,
              textAlign: "center",
            }}
          >
            Tỷ lệ nhớ: {percent}%
          </Text>
        </Box>
      </Box>

      {/* Footer */}
      <Box
        style={{
          padding: "16px 24px 24px",
          textAlign: "center",
          background: "rgba(0,0,0,0.1)",
        }}
      >
        <Text
          style={{
            fontSize: 12,
            color: "rgba(255,255,255,0.7)",
            fontWeight: 600,
          }}
        >
          ChatHay - Ôn Tập Thông Minh
        </Text>
      </Box>
    </Box>
  );
}
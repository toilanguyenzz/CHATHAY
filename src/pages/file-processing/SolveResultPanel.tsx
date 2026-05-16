/* ─── Solve Problem Result Panel ─── */
import { Box, Text } from "zmp-ui";

interface SolveResultPanelProps {
  result: {
    question: string;
    steps: string[];
    answer: string;
  } | null;
  onClose: () => void;
  onCreateQuiz?: () => void;
}

export function SolveResultPanel({ result, onClose, onCreateQuiz }: SolveResultPanelProps) {
  if (!result) return null;

  return (
    <Box
      style={{
        padding: 20,
        borderRadius: "var(--radius-xl)",
        background: "linear-gradient(135deg, #F0FDF4, #DCFCE7)",
        border: "2px solid #10B981",
        animation: "slideIn 0.3s ease-out",
      }}
    >
      <Box
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#047857" }}>
          ✅ Kết quả giải bài
        </Text>
        <Box onClick={onClose} style={{ cursor: "pointer", fontSize: 20 }}>✕</Box>
      </Box>

      <Text
        style={{
          fontSize: 16,
          fontWeight: 800,
          color: "#064E3B",
          marginBottom: 12,
        }}
      >
        📝 {result.question}
      </Text>

      <Box
        style={{
          padding: "14px",
          marginBottom: 12,
          borderRadius: "var(--radius-lg)",
          background: "white",
          border: "1px solid #10B981",
        }}
      >
        <Text
          style={{
            fontWeight: 700,
            color: "#047857",
            marginBottom: 8,
            display: "block",
          }}
        >
          📋 Lời giải chi tiết:
        </Text>
        {result.steps.map((step, i) => (
          <Text
            key={i}
            style={{
              fontSize: 13,
              color: "#064E3B",
              lineHeight: 1.6,
              display: "block",
              marginBottom: 6,
            }}
          >
            {i + 1}. {step}
          </Text>
        ))}
      </Box>

      <Box
        style={{
          padding: "12px 16px",
          borderRadius: "var(--radius-lg)",
          background: "linear-gradient(135deg, #10B981, #34D399)",
          color: "white",
          textAlign: "center",
          marginBottom: 12,
        }}
      >
        <Text style={{ fontSize: 16, fontWeight: 900 }}>🎯 Đáp án: {result.answer}</Text>
      </Box>

      {onCreateQuiz && (
        <Box
          onClick={onCreateQuiz}
          style={{
            padding: "12px 16px",
            borderRadius: "var(--radius-lg)",
            background: "rgba(255,255,255,0.9)",
            border: "2px dashed #10B981",
            cursor: "pointer",
            textAlign: "center",
            marginTop: 8,
          }}
        >
          <Text style={{ fontSize: 14, fontWeight: 700, color: "#047857" }}>
            🧠 Tạo 5 câu quiz từ bài này để ôn tập
          </Text>
        </Box>
      )}

      <Box
        style={{
          padding: "10px 14px",
          borderRadius: "var(--radius-lg)",
          background: "rgba(255,255,255,0.8)",
        }}
      >
        <Text style={{ fontSize: "var(--font-size-xs)", color: "#047857", fontWeight: 600 }}>
          💡 Chưa hiểu? Hỏi AI ngay bên dưới để được giải thích thêm!
        </Text>
      </Box>
    </Box>
  );
}

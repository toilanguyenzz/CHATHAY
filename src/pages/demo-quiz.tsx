import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { playCorrectSound, playWrongSound, playTickSound } from "../hooks/useSound";
import { IconChevronLeft, IconChevronRight, IconHome, IconRefresh } from "../components/icons";

const demoQuestions = [
  {
    id: 1,
    question: "Công thức tính đạo hàm của hàm số y = x³ là gì?",
    options: [
      { label: "A", text: "3x²", isCorrect: true },
      { label: "B", text: "x²", isCorrect: false },
      { label: "C", text: "3x", isCorrect: false },
      { label: "D", text: "x³", isCorrect: false },
    ],
    explanation: "Theo quy tắc đạo hàm: (xⁿ)' = n·xⁿ⁻¹. Vậy (x³)' = 3·x²",
    category: "Toán 12",
    difficulty: "easy",
  },
  {
    id: 2,
    question: "Chất nào sau đây là chất điện li mạnh?",
    options: [
      { label: "A", text: "NaCl", isCorrect: true },
      { label: "B", text: "CH₃COOH", isCorrect: false },
      { label: "C", text: "H₂O", isCorrect: false },
      { label: "D", text: "C₆H₁₂O₆", isCorrect: false },
    ],
    explanation: "NaCl là muối tan tốt trong nước và phân li hoàn toàn thành Na⁺ và Cl⁻",
    category: "Hóa 11",
    difficulty: "medium",
  },
  {
    id: 3,
    question: "Con lắc lò xo dao động điều hòa có chu kỳ T phụ thuộc vào:",
    options: [
      { label: "A", text: "Khối lượng vật và độ cứng lò", isCorrect: true },
      { label: "B", text: "Biên độ dao động", isCorrect: false },
      { label: "C", text: "Nhiệt độ môi trường", isCorrect: false },
      { label: "D", text: "Lực cản không khí", isCorrect: false },
    ],
    explanation: "T = 2π√(m/k) - chu kỳ phụ thuộc vào khối lượng m và độ cứng k",
    category: "Lý 12",
    difficulty: "hard",
  },
  {
    id: 4,
    question: "Tác giả của 'Truyện Kiều' là ai?",
    options: [
      { label: "A", text: "Nguyễn Du", isCorrect: true },
      { label: "B", text: "Nguyễn Khản", isCorrect: false },
      { label: "C", text: "Nguyễn Nghiễm", isCorrect: false },
      { label: "D", text: "Nguyễn Công Trứ", isCorrect: false },
    ],
    explanation: "Nguyễn Du (1765-1820) là tác giả của 'Truyện Kiều' - kiệt tác văn học Việt Nam",
    category: "Văn 9",
    difficulty: "easy",
  },
  {
    id: 5,
    question: "Trong lịch sử VN, khởi nghĩa Bắc Sơn xảy ra năm nào?",
    options: [
      { label: "A", text: "1940", isCorrect: true },
      { label: "B", text: "1941", isCorrect: false },
      { label: "C", text: "1945", isCorrect: false },
      { label: "D", text: "1930", isCorrect: false },
    ],
    explanation: "Khởi nghĩa Bắc Sơn nổ ra ngày 27/9/1940 do Đảng Cộng sản Đông Dương lãnh đạo",
    category: "Lịch sử 12",
    difficulty: "medium",
  },
];

const diffConfig: Record<string, { label: string; color: string; bg: string; emoji: string }> = {
  easy: { label: "Dễ", color: "#16A34A", bg: "#DCFCE7", emoji: "🟢" },
  medium: { label: "Trung bình", color: "#D97706", bg: "#FEF3C7", emoji: "🟡" },
  hard: { label: "Khó", color: "#DC2626", bg: "#FEE2E2", emoji: "🔴" },
};

function DemoQuizPage() {
  const navigate = useNavigate();
  const [currentQ, setCurrentQ] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [quizDone, setQuizDone] = useState(false);
  const [timer, setTimer] = useState(30);

  const total = demoQuestions.length;
  const question = demoQuestions[currentQ];
  const progress = total > 0 ? ((currentQ + 1) / total) * 100 : 0;
  const diff = diffConfig[question?.difficulty || "medium"] || diffConfig["medium"];

  // Timer countdown
  useEffect(() => {
    if (quizDone || showResult || total === 0) return;
    setTimer(30);
    const interval = setInterval(() => {
      setTimer((t) => {
        if (t <= 5 && t > 0) playTickSound();
        if (t <= 1) {
          clearInterval(interval);
          handleSelect(-1);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [currentQ, quizDone, showResult, total]);

  const handleSelect = (idx: number) => {
    if (showResult) return;
    setSelected(idx);
    setShowResult(true);

    if (idx < 0) return; // Skip

    if (question && question.options[idx]?.isCorrect) {
      playCorrectSound();
      setScore((s) => s + 1);
    } else {
      playWrongSound();
    }
  };

  const nextQuestion = () => {
    if (currentQ + 1 >= total) {
      setQuizDone(true);
      return;
    }
    setCurrentQ((p) => p + 1);
    setSelected(null);
    setShowResult(false);
    setTimer(30);
  };

  const resetQuiz = () => {
    setCurrentQ(0);
    setSelected(null);
    setShowResult(false);
    setScore(0);
    setQuizDone(false);
    setTimer(30);
  };

  if (quizDone) {
    const percent = Math.round((score / total) * 100);
    const getMessage = () => {
      if (percent >= 80)
        return { emoji: "🏆", title: "Xuất sắc!", desc: "Bạn có nền tảng rất tốt! Muốn ôn luyện chuyên sâu? Upload tài liệu của bạn ngay!" };
      if (percent >= 50)
        return { emoji: "👍", title: "Khá tốt!", desc: "Bạn có kiến thức cơ bản. Hãy upload tài liệu để học thêm nhé!" };
      return { emoji: "💪", title: "Cố gắng thêm!", desc: "Ôn tập chưa kỹ? Upload tài liệu và bắt đầu học ngay nào!" };
    };
    const msg = getMessage();

    return (
      <Page className="ch-page">
        <Box
          className="ch-container"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "calc(100vh - 80px)",
            gap: 24,
            padding: 24,
          }}
        >
          <Text style={{ fontSize: 72, lineHeight: 1 }}>{msg.emoji}</Text>
          <Text className="ch-heading-xl" style={{ textAlign: "center", marginBottom: 8 }}>
            {msg.title}
          </Text>
          <Text className="ch-body" style={{ textAlign: "center", color: "var(--color-text-secondary)", maxWidth: 280 }}>
            {msg.desc}
          </Text>

          <Box
            style={{
              background: "var(--color-bg-card)",
              borderRadius: "var(--radius-xl)",
              padding: "24px 28px",
              width: "100%",
              maxWidth: 280,
              border: "2px solid var(--color-border)",
              textAlign: "center",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <Text className="ch-caption" style={{ color: "var(--color-text-tertiary)", marginBottom: 8 }}>
              ĐIỂM DEMO
            </Text>
            <Box style={{ fontSize: 48, fontWeight: 900, color: "var(--color-primary)", marginBottom: 4 }}>
              {score}/{total}
            </Box>
            <Text className="ch-caption" style={{ color: "var(--color-text-tertiary)" }}>
              {percent}% chính xác
            </Text>
          </Box>

          {/* Upload Now Button */}
          <Box
            className="ch-btn-primary"
            onClick={() => navigate("/file-processing")}
            style={{
              width: "100%",
              maxWidth: 280,
              justifyContent: "center",
              background: "linear-gradient(135deg, #10B981, #059669)",
              padding: "16px 24px",
            }}
          >
            <Text style={{ fontSize: 18, marginRight: 8 }}>📚</Text>
            <span>Upload tài liệu ngay</span>
          </Box>

          {/* Share Button */}
          <Box
            className="ch-btn-secondary"
            onClick={() => {
              const shareText = `🎯 Tôi vừa làm ${score}/${total} điểm Demo Quiz trên ChatHay!\n📊 ${percent}% chính xác\n👉 Thử ngay: chathay.vn`;
              navigator.clipboard?.writeText(shareText);
              alert("Đã copy! Dán vào Zalo để chia sẻ nhé!");
            }}
            style={{ width: "100%", maxWidth: 280, justifyContent: "center" }}
          >
            <Text style={{ fontSize: 18 }}>📤</Text>
            <span>Chia sẻ kết quả</span>
          </Box>

          {/* Retry Button */}
          <Box
            className="ch-btn-secondary"
            onClick={resetQuiz}
            style={{ width: "100%", maxWidth: 280, justifyContent: "center" }}
          >
            <IconRefresh size={18} />
            <span style={{ marginLeft: 8 }}>Làm lại</span>
          </Box>

          {/* Home Button */}
          <Box
            onClick={() => navigate("/")}
            style={{
              marginTop: 8,
              padding: "12px 28px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-bg-subtle)",
              border: "1px solid var(--color-border)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              justifyContent: "center",
              width: "100%",
              maxWidth: 280,
            }}
          >
            <IconHome size={16} />
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "var(--color-text-secondary)" }}>
              Về trang chủ
            </Text>
          </Box>
        </Box>
      </Page>
    );
  }

  return (
    <Page className="ch-page">
      <Box
        className="ch-container"
        style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - 80px)", gap: 0 }}
      >
        {/* Top Bar */}
        <Box
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
            padding: "4px 0",
          }}
        >
          <Box
            style={{ display: "flex", alignItems: "center", gap: 10 }}
            onClick={() => navigate("/")}
          >
            <Box
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
                flexShrink: 0,
              }}
            >
              <IconChevronLeft size={18} />
            </Box>
            <Box style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Text className="ch-caption" style={{ fontWeight: 600 }}>
                Demo Quiz
              </Text>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "var(--color-text-primary)" }}>
                {currentQ + 1}<span style={{ color: "var(--color-text-tertiary)", fontWeight: 500 }}>/{total}</span>
              </Text>
            </Box>
          </Box>
          {/* Timer */}
          <Box
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 14px",
              borderRadius: "var(--radius-full)",
              background: timer <= 10 ? "var(--color-danger-light)" : "var(--color-bg-subtle)",
              transition: "background 0.3s",
            }}
          >
            <Text style={{ fontSize: 14 }}>⏱️</Text>
            <Text
              style={{
                fontSize: 14,
                fontWeight: 800,
                color: timer <= 10 ? "var(--color-danger)" : "var(--color-text-secondary)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              00:{timer.toString().padStart(2, "0")}
            </Text>
          </Box>
        </Box>

        {/* Progress */}
        <Box className="ch-progress" style={{ marginBottom: 20 }}>
          <Box className="ch-progress-bar" style={{ width: `${progress}%` }} />
        </Box>

        {/* Badge */}
        <Box
          className="ch-badge"
          style={{
            background: diff.bg,
            color: diff.color,
            alignSelf: "flex-start",
            marginBottom: 14,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          {diff.emoji} {diff.label} • {question?.category}
        </Box>

        {/* Question */}
        <Text
          style={{
            fontSize: "var(--font-size-lg)",
            fontWeight: 800,
            color: "var(--color-text-primary)",
            lineHeight: 1.5,
            marginBottom: 24,
            letterSpacing: "-0.01em",
          }}
        >
          {question?.question}
        </Text>

        {/* Options */}
        <Box style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
          {question?.options.map((opt, idx) => {
            let className = "";
            if (!showResult) {
              className = idx === selected ? "selected" : "";
            } else {
              if (opt.isCorrect) className = "correct";
              else if (idx === selected && !opt.isCorrect) className = "wrong";
            }

            return (
              <Box
                key={idx}
                className={`ch-quiz-option ${className}`}
                onClick={() => handleSelect(idx)}
                style={{
                  opacity: showResult && idx !== selected && !opt.isCorrect ? 0.5 : 1,
                }}
              >
                <Box className="ch-quiz-option-label">{opt.label}</Box>
                <Text
                  style={{
                    flex: 1,
                    fontSize: "var(--font-size-sm)",
                    fontWeight: 600,
                    color: "var(--color-text-primary)",
                  }}
                >
                  {opt.text}
                </Text>
                {showResult && opt.isCorrect && <Text style={{ fontSize: 20, lineHeight: 1 }}>✅</Text>}
                {showResult && idx === selected && !opt.isCorrect && <Text style={{ fontSize: 20, lineHeight: 1 }}>❌</Text>}
              </Box>
            );
          })}
        </Box>

        {/* Explanation */}
        {showResult && (
          <Box
            className="ch-explanation"
            style={{
              marginTop: 16,
              padding: "14px 16px",
              borderRadius: "var(--radius-lg)",
              background: "var(--color-primary-lighter)",
              border: "1px solid var(--color-border)",
            }}
          >
            <Text
              style={{
                fontSize: "var(--font-size-sm)",
                fontWeight: 600,
                color: "#92400E",
                lineHeight: 1.6,
              }}
            >
              💡 {question?.explanation}
            </Text>
          </Box>
        )}

        {/* Skip & Next Buttons */}
        {!showResult ? (
          <Box
            className="ch-btn-secondary"
            onClick={() => handleSelect(-1)}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
          >
            <Text style={{ fontSize: 16 }}>⏭️</Text>
            <span style={{ marginLeft: 8 }}>Bỏ qua</span>
          </Box>
        ) : (
          <Box
            className="ch-btn-primary"
            onClick={nextQuestion}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
          >
            <span>{currentQ + 1 >= total ? "Xem kết quả" : "Câu tiếp theo"}</span>
            <IconChevronRight size={16} style={{ marginLeft: 8 }} />
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default DemoQuizPage;
import { Box, Page, Text, useNavigate, useParams } from "zmp-ui";
import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { playCorrectSound, playWrongSound, playTickSound } from "../hooks/useSound";
import { IconChevronLeft, IconChevronRight } from "../components/icons";

interface Question {
  question: string;
  options: string[];
  correct: number;
  explanation: string;
  difficulty: string;
}

interface SharedQuizData {
  quiz_id: string;
  title: string;
  questions: Question[];
  max_attempts: number;
}

function SharedQuizPage() {
  const { shareCode } = useParams<{ shareCode: string }>();
  const navigate = useNavigate();
  const { user_id } = useAuth();

  const [loading, setLoading] = useState(true);
  const [quizStarted, setQuizStarted] = useState(false);
  const [quizData, setQuizData] = useState<SharedQuizData | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [quizDone, setQuizDone] = useState(false);
  const [timer, setTimer] = useState(30);
  const [answers, setAnswers] = useState<{ question_index: number; selected_option: number; time_spent: number }[]>([]);
  const [timePerQuestion, setTimePerQuestion] = useState<number[]>([]);
  const [startTime, setStartTime] = useState<number>(0);

  // Load quiz info
  useEffect(() => {
    if (!shareCode) return;
    loadQuizInfo();
  }, [shareCode]);

  const loadQuizInfo = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/shared-quiz/${shareCode}`
      );
      const data = await response.json();
      if (data.error) {
        alert(data.error);
        navigate("/");
      }
    } catch (err) {
      console.error("Failed to load quiz info:", err);
    } finally {
      setLoading(false);
    }
  };

  const startQuiz = async () => {
    if (!user_id || !shareCode) return;
    setLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/shared-quiz/${shareCode}/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-Id": user_id,
          },
          body: JSON.stringify({ user_id }),
        }
      );

      const data = await response.json();
      if (data.error) {
        alert(data.error);
        if (data.error.includes("Maximum attempts")) {
          navigate("/");
          return;
        }
      }

      setQuizData({
        quiz_id: data.quiz_id,
        title: data.title,
        questions: data.questions,
        max_attempts: data.max_attempts,
      });
      setQuizStarted(true);
      setStartTime(Date.now());
    } catch (err) {
      console.error("Failed to start quiz:", err);
      alert("Không thể bắt đầu quiz. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  // Timer countdown
  useEffect(() => {
    if (!quizStarted || quizDone || showResult || !quizData) return;
    setTimer(30);
    const questionStartTime = Date.now();
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
  }, [currentQ, quizDone, showResult, quizStarted, quizData]);

  const handleSelect = (idx: number) => {
    if (showResult) return;
    setSelected(idx);
    setShowResult(true);

    const timeSpent = 30 - timer;
    setTimePerQuestion((prev) => [...prev, timeSpent]);

    if (idx < 0) {
      setAnswers((prev) => [...prev, { question_index: currentQ, selected_option: -1, time_spent: timeSpent }]);
      return;
    }

    if (idx === quizData?.questions[currentQ]?.correct) {
      playCorrectSound();
      setScore((s) => s + 1);
    } else {
      playWrongSound();
    }

    setAnswers((prev) => [...prev, { question_index: currentQ, selected_option: idx, time_spent: timeSpent }]);
  };

  const nextQuestion = () => {
    if (!quizData) return;
    if (currentQ + 1 >= quizData.questions.length) {
      finishQuiz();
      return;
    }
    setCurrentQ((p) => p + 1);
    setSelected(null);
    setShowResult(false);
    setTimer(30);
  };

  const finishQuiz = async () => {
    if (!user_id || !shareCode || !quizData) return;
    setQuizDone(true);

    const total_time = Date.now() - startTime;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/shared-quiz/${shareCode}/submit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-Id": user_id,
          },
          body: JSON.stringify({
            user_id,
            display_name: user_id, // TODO: Get from user profile
            answers: answers.map((a, i) => ({
              ...a,
              time_spent: timePerQuestion[i] || 30,
            })),
          }),
        }
      );

      const data = await response.json();
      if (data.success) {
        setScore(data.score);
      }
    } catch (err) {
      console.error("Failed to submit quiz:", err);
    }
  };

  if (loading) {
    return (
      <Page className="ch-page">
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
          <Text>Đang tải quiz...</Text>
        </Box>
      </Page>
    );
  }

  if (!quizStarted && quizData) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", gap: 24, padding: 24 }}>
          <Text style={{ fontSize: 64 }}>📚</Text>
          <Text className="ch-heading-xl" style={{ textAlign: "center" }}>{quizData.title}</Text>
          <Box
            style={{
              padding: "20px 28px",
              borderRadius: "var(--radius-xl)",
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              textAlign: "center",
              maxWidth: 320,
            }}
          >
            <Text style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
              {quizData.questions.length} câu hỏi
            </Text>
            <Text style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 4 }}>
              Thời gian: 30s/câu
            </Text>
          </Box>
          <Box
            className="ch-btn-primary"
            onClick={startQuiz}
            style={{ width: "100%", maxWidth: 280, justifyContent: "center", background: "linear-gradient(135deg, #10B981, #059669)", padding: "16px" }}
          >
            <Text style={{ fontSize: 16, fontWeight: 800 }}>Bắt đầu làm bài</Text>
          </Box>
        </Box>
      </Page>
    );
  }

  if (!quizData) {
    return (
      <Page className="ch-page">
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
          <Text>Quiz không tồn tại</Text>
        </Box>
      </Page>
    );
  }

  if (quizDone) {
    const percent = Math.round((score / quizData.questions.length) * 100);
    const getMessage = () => {
      if (percent >= 80) return { emoji: "🏆", title: "Xuất sắc!", desc: "Bạn làm rất tốt!" };
      if (percent >= 60) return { emoji: "👍", title: "Khá tốt!", desc: "Cố gắng hơn nữa!" };
      return { emoji: "💪", title: "Cố gắng thêm!", desc: "Hãy ôn tập thêm nhé!" };
    };
    const msg = getMessage();

    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", gap: 24, padding: 24 }}>
          <Text style={{ fontSize: 64 }}>{msg.emoji}</Text>
          <Text className="ch-heading-xl">{msg.title}</Text>
          <Box
            style={{
              padding: "24px 28px",
              borderRadius: "var(--radius-xl)",
              background: "var(--color-bg-card)",
              border: "2px solid var(--color-border)",
              textAlign: "center",
              maxWidth: 280,
            }}
          >
            <Text style={{ fontSize: 48, fontWeight: 900, color: "var(--color-primary)" }}>{score}/{quizData.questions.length}</Text>
            <Text style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 8 }}>{percent}%</Text>
          </Box>
          <Box
            className="ch-btn-secondary"
            onClick={() => navigate("/")}
            style={{ width: "100%", maxWidth: 280, justifyContent: "center" }}
          >
            <Text style={{ fontSize: 16 }}>🏠</Text>
            <Text style={{ marginLeft: 8 }}>Về trang chủ</Text>
          </Box>
        </Box>
      </Page>
    );
  }

  const question = quizData.questions[currentQ];
  const total = quizData.questions.length;
  const progress = ((currentQ + 1) / total) * 100;

  return (
    <Page className="ch-page">
      <Box className="ch-container" style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - 80px)", gap: 0 }}>
        {/* Top Bar */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, padding: "4px 0" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Text className="ch-caption" style={{ fontWeight: 600 }}>Câu hỏi</Text>
            <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "var(--color-text-primary)" }}>
              {currentQ + 1}<span style={{ color: "var(--color-text-tertiary)", fontWeight: 500 }}>/{total}</span>
            </Text>
          </Box>
          <Box
            style={{
              display: "flex", alignItems: "center", gap: 6, padding: "6px 14px",
              borderRadius: "var(--radius-full)",
              background: timer <= 10 ? "var(--color-danger-light)" : "var(--color-bg-subtle)",
            }}
          >
            <Text style={{ fontSize: 14 }}>⏱️</Text>
            <Text
              style={{
                fontSize: 14, fontWeight: 800,
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

        {/* Question */}
        <Text
          style={{
            fontSize: "var(--font-size-lg)", fontWeight: 800, color: "var(--color-text-primary)",
            lineHeight: 1.5, marginBottom: 24,
          }}
        >
          {question.question}
        </Text>

        {/* Options */}
        <Box style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
          {question.options.map((opt, idx) => {
            let className = "";
            if (!showResult) {
              className = idx === selected ? "selected" : "";
            } else {
              if (idx === question.correct) className = "correct";
              else if (idx === selected && idx !== question.correct) className = "wrong";
            }

            return (
              <Box
                key={idx}
                className={`ch-quiz-option ${className}`}
                onClick={() => handleSelect(idx)}
              >
                <Box className="ch-quiz-option-label">{String.fromCharCode(65 + idx)}</Box>
                <Text style={{ flex: 1, fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>{opt}</Text>
                {showResult && idx === question.correct && <Text style={{ fontSize: 20 }}>✅</Text>}
                {showResult && idx === selected && idx !== question.correct && <Text style={{ fontSize: 20 }}>❌</Text>}
              </Box>
            );
          })}
        </Box>

        {/* Explanation */}
        {showResult && (
          <Box
            className="ch-explanation"
            style={{
              marginTop: 16, padding: "14px 16px", borderRadius: "var(--radius-lg)",
              background: "var(--color-primary-lighter)", border: "1px solid var(--color-border)",
            }}
          >
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "#92400E", lineHeight: 1.6 }}>
              💡 {question.explanation}
            </Text>
          </Box>
        )}

        {/* Next Button */}
        {!showResult ? (
          <Box
            className="ch-btn-secondary"
            onClick={() => handleSelect(-1)}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
          >
            <Text>⏭️ Bỏ qua</Text>
          </Box>
        ) : (
          <Box
            className="ch-btn-primary"
            onClick={nextQuestion}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
          >
            <Text>{currentQ + 1 >= total ? "Xem kết quả" : "Câu tiếp theo"}</Text>
            <IconChevronRight size={16} style={{ marginLeft: 8 }} />
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default SharedQuizPage;
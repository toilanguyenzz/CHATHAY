import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { studyService } from "../services/studyService";
import { useAuth } from "../hooks/useAuth";

interface Question {
  id: number;
  question: string;
  options: { label: string; text: string; isCorrect: boolean }[];
  explanation: string;
  category: string;
}

function QuizPage() {
  const nav = useNavigate();
  const { user_id } = useAuth();
  const { docId } = useParams<{ docId?: string }>();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentQ, setCurrentQ] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [quizDone, setQuizDone] = useState(false);
  const [timer, setTimer] = useState(30);
  const [animateOption, setAnimateOption] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Load quiz questions
  useEffect(() => {
    if (!user_id) return;
    setLoading(true);
    const id = docId || new URLSearchParams(window.location.search).get("doc");

    const loadQuiz = async () => {
      try {
        if (id) {
          // Start quiz session via backend
          const session = await studyService.startQuiz(id);
          setSessionId(session.session_id);
          // Load questions from the session
          const qs = await studyService.getQuizQuestions(id);
          setQuestions(qs || []);
        } else {
          // Load default mock if no doc
          setQuestions([]);
        }
      } catch (e) {
        console.error("Failed to load quiz:", e);
      } finally {
        setLoading(false);
      }
    };

    loadQuiz();
  }, [user_id, docId]);

  const total = questions.length;
  const question = questions[currentQ];
  const progress = total > 0 ? ((currentQ + 1) / total) * 100 : 0;

  // Timer countdown
  useEffect(() => {
    if (quizDone || showResult || total === 0) return;
    setTimer(30);
    const interval = setInterval(() => {
      setTimer(t => {
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
    setAnimateOption(true);

    if (sessionId && idx >= 0 && question) {
      // Call backend to record answer
      const answerLetter = String.fromCharCode(65 + idx); // A, B, C, D
      studyService.answerQuiz(sessionId, answerLetter).then(result => {
        if (result.is_correct) setScore(s => s + 1);
        if (result.is_last) {
          setQuizDone(true);
        }
      }).catch(() => {});
    } else {
      if (idx >= 0 && question && question.options[idx]?.isCorrect) {
        setScore(s => s + 1);
      }
    }

    setTimeout(() => setAnimateOption(false), 300);
  };

  const nextQuestion = () => {
    if (currentQ + 1 >= total) { setQuizDone(true); return; }
    setCurrentQ(p => p + 1);
    setSelected(null);
    setShowResult(false);
  };

  const resetQuiz = () => {
    setCurrentQ(0); setSelected(null); setShowResult(false);
    setScore(0); setQuizDone(false); setTimer(30);
  };

  const getOptionClass = (idx: number, opt: { isCorrect: boolean }) => {
    if (!showResult) return idx === selected ? "selected" : "";
    if (opt.isCorrect) return "correct";
    if (idx === selected && !opt.isCorrect) return "wrong";
    return "";
  };

  if (loading) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <Text className="ch-caption">Đang tải câu hỏi...</Text>
        </Box>
      </Page>
    );
  }

  if (total === 0) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16 }}>
          <Text style={{ fontSize: 48 }}>📭</Text>
          <Text className="ch-heading-lg">Chưa có Quiz</Text>
          <Text className="ch-caption">Tải tài liệu để tự động tạo Quiz nhé!</Text>
          <Box className="ch-btn-primary" onClick={() => nav("/file-processing")} style={{ marginTop: 8 }}>
            <span>Tải tài liệu</span>
          </Box>
        </Box>
      </Page>
    );
  }

  /* Quiz Done Screen */
  if (quizDone) {
    const percent = Math.round((score / total) * 100);
    const getMessage = () => {
      if (percent >= 80) return { emoji: "🏆", title: "Xuất sắc!", desc: "Bạn nắm rất chắc kiến thức. Tiếp tục phát huy!" };
      if (percent >= 50) return { emoji: "👍", title: "Khá tốt!", desc: "Hãy ôn tập thêm những phần chưa chắc nhé." };
      return { emoji: "💪", title: "Cố gắng thêm!", desc: "Hãy quay lại Flashcard để học kỹ hơn." };
    };
    const msg = getMessage();

    return (
      <Page className="ch-page">
        <Box className="ch-container animate-scale-in" style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", minHeight: "calc(100vh - 80px)", gap: 24,
        }}>
          <Text style={{ fontSize: 64, lineHeight: 1 }}>{msg.emoji}</Text>
          <Text className="ch-heading-xl" style={{ textAlign: "center" }}>{msg.title}</Text>
          <Box style={{
            background: "var(--color-bg-card)", borderRadius: "var(--radius-xl)",
            padding: "20px 24px", width: "100%", maxWidth: 320,
            border: "1px solid var(--color-border)", textAlign: "center",
          }}>
            <Text className="ch-body-sm" style={{ lineHeight: 1.6 }}>{msg.desc}</Text>
          </Box>
          <Box style={{ fontSize: 40, fontWeight: 900 }}>{score}/{total}</Box>
          <Box className="ch-btn-primary" onClick={resetQuiz} style={{ marginTop: 8, width: "100%", maxWidth: 280, justifyContent: "center" }}>
            <Text style={{ fontSize: 18 }}>🔄</Text>
            <span>Làm lại</span>
          </Box>
          <Box onClick={() => nav("/")} style={{
            marginTop: 4, padding: "12px 28px", borderRadius: "var(--radius-md)",
            background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
            cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
            justifyContent: "center", width: "100%", maxWidth: 280,
          }}>
            <Text style={{ fontSize: 16 }}>🏠</Text>
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "var(--color-text-secondary)" }}>Về trang chủ</Text>
          </Box>
        </Box>
      </Page>
    );
  }

  /* Quiz Active Screen */
  return (
    <Page className="ch-page">
      <Box className="ch-container animate-fade-in" style={{
        display: "flex", flexDirection: "column", minHeight: "calc(100vh - 80px)", gap: 0,
      }}>
        {/* Top Bar */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Box onClick={() => nav("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0,
            }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 18, color: "var(--color-text-secondary)" }} />
            </Box>
            <Box style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Text className="ch-caption" style={{ fontWeight: 600 }}>Câu hỏi</Text>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "var(--color-text-primary)" }}>
                {currentQ + 1}<span style={{ color: "var(--color-text-tertiary)", fontWeight: 500 }}>/{total}</span>
              </Text>
            </Box>
          </Box>
          {/* Timer */}
          <Box style={{
            display: "flex", alignItems: "center", gap: 6, padding: "6px 14px",
            borderRadius: "var(--radius-full)",
            background: timer <= 10 ? "var(--color-danger-light)" : "var(--color-bg-subtle)",
            transition: "background 0.3s",
          }}>
            <Text style={{ fontSize: 14 }}>⏱️</Text>
            <Text style={{
              fontSize: 14, fontWeight: 800, color: timer <= 10 ? "var(--color-danger)" : "var(--color-text-secondary)",
              fontVariantNumeric: "tabular-nums",
            }}>00:{timer.toString().padStart(2, "0")}</Text>
          </Box>
        </Box>

        {/* Progress */}
        <Box className="ch-progress" style={{ marginBottom: 20 }}>
          <Box className="ch-progress-bar" style={{ width: `${progress}%` }} />
        </Box>

        {/* Category Badge */}
        <Box className="ch-badge" style={{
          background: "var(--color-primary-lighter)", color: "var(--color-primary)",
          alignSelf: "flex-start", marginBottom: 14,
        }}>
          📚 {question?.category || "Học tập"}
        </Box>

        {/* Question */}
        <Text style={{
          fontSize: "var(--font-size-lg)", fontWeight: 800, color: "var(--color-text-primary)",
          lineHeight: 1.5, marginBottom: 24, letterSpacing: "-0.01em",
        }}>{question?.question}</Text>

        {/* Options */}
        <Box style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}>
          {question?.options.map((opt, idx) => {
            const cls = getOptionClass(idx, opt);
            return (
              <Box key={idx} className={`ch-quiz-option ${cls}`} onClick={() => handleSelect(idx)}
                style={{
                  animation: animateOption && (cls === "correct" || cls === "wrong")
                    ? "scaleIn 0.3s var(--ease-spring)" : undefined,
                }}
              >
                <Box className="ch-quiz-option-label">{opt.label}</Box>
                <Text style={{ flex: 1, fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>{opt.text}</Text>
                {showResult && opt.isCorrect && <Text style={{ fontSize: 20, lineHeight: 1 }}>✅</Text>}
                {showResult && idx === selected && !opt.isCorrect && <Text style={{ fontSize: 20, lineHeight: 1 }}>❌</Text>}
              </Box>
            );
          })}
        </Box>

        {/* Explanation */}
        {showResult && (
          <Box className="ch-explanation animate-slide-up" style={{ marginTop: 16 }}>
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "#92400E", lineHeight: 1.6 }}>
              💡 {question?.explanation}
            </Text>
          </Box>
        )}

        {/* Next Button */}
        {showResult && (
          <Box className="ch-btn-primary animate-slide-up" onClick={nextQuestion}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}>
            <span>{currentQ + 1 >= total ? "Xem kết quả" : "Câu tiếp theo"}</span>
            <Icon icon="zi-chevron-right" style={{ fontSize: 16 }} />
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default QuizPage;

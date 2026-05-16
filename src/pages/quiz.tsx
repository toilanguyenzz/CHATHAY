import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { studyService } from "../services/studyService";
import { documentService } from "../services/documentService";
import { useAuth } from "../hooks/useAuth";
import { EmptyState } from "../components/EmptyState";
import { playCorrectSound, playWrongSound, playTickSound } from "../hooks/useSound";
import { QuizShareCard } from "../components/ShareCard";

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
  const [reviewMode, setReviewMode] = useState(false);
  const [reviewData, setReviewData] = useState<any>(null);
  const [reviewIdx, setReviewIdx] = useState(0);
  const [allDocs, setAllDocs] = useState<any[]>([]);
  const [showShareCard, setShowShareCard] = useState(false);

  // Inline upload state (must be before any early returns)
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Load all documents for suggestion
  useEffect(() => {
    if (!user_id) return;
    documentService.getDocuments().then(docs => {
      setAllDocs(Array.isArray(docs) ? docs : []);
    }).catch(() => {});
  }, [user_id]);

  // Load quiz questions
  useEffect(() => {
    if (!user_id) return;
    setLoading(true);
    const id = docId || new URLSearchParams(window.location.search).get("doc_id") || new URLSearchParams(window.location.search).get("doc");

    const loadQuiz = async () => {
      try {
        if (id) {
          // Step 1: Try loading pre-generated quiz questions from DB
          let qs = await studyService.getQuizQuestions(id);
          let loadedQs = Array.isArray(qs) ? qs : [];

          // Step 2: Start a session for score tracking (or generate if missing)
          try {
            const session = await studyService.startQuiz(id);
            if (session?.session_id) {
              setSessionId(session.session_id);
              // Restore progress from sessionStorage
              const savedQ = sessionStorage.getItem(`quiz_${id}_currentQ`);
              const savedSession = sessionStorage.getItem(`quiz_${id}_sessionId`);
              if (savedQ && savedSession === session.session_id) {
                setCurrentQ(parseInt(savedQ, 10));
              }
            }

            // If questions were empty, startQuiz just generated them, so fetch again!
            if (loadedQs.length === 0) {
              qs = await studyService.getQuizQuestions(id);
              loadedQs = Array.isArray(qs) ? qs : [];
            }
          } catch (sessionErr) {
            console.warn("Quiz session start failed:", sessionErr);
          }

          if (loadedQs.length > 0) {
            // Transform raw quiz data to match Question interface
            const formattedQs = loadedQs.map((q: any, idx: number) => {
              if (q.options?.[0]?.isCorrect !== undefined) return q;

              const options = (q.options || []).map((opt: any, i: number) => {
                const text = typeof opt === "string" ? opt : (opt.text || opt.label || String(opt));
                return {
                  label: String.fromCharCode(65 + i),
                  text,
                  isCorrect: i === q.correct,
                };
              });

              return {
                id: q.id || idx,
                question: q.question,
                options,
                explanation: q.explanation || "",
                category: q.category || q.difficulty || "Học tập",
              };
            });

            setQuestions(formattedQs);
          } else {
            setQuestions([]);
          }
        } else {
          setQuestions([]);
        }
      } catch (e) {
        console.error("Failed to load quiz:", e);
        setQuestions([]);
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
        if (t <= 5 && t > 0) playTickSound(); // Tick sound warning
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

    // Skip: không chọn đáp án - vẫn hiện explanation
    if (idx < 0) {
      setTimeout(() => setAnimateOption(false), 300);
      return; // Skip không gọi API, không tính điểm
    }

    // Play sound
    if (question && question.options[idx]?.isCorrect) {
      playCorrectSound();
    } else {
      playWrongSound();
    }

    if (sessionId && question) {
      const answerLetter = String.fromCharCode(65 + idx);
      studyService.answerQuiz(sessionId, answerLetter).then(result => {
        if (result.is_correct) setScore(s => s + 1);
        if (result.is_last) setQuizDone(true);
      }).catch(() => {});
    } else {
      if (question && question.options[idx]?.isCorrect) {
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

  // Save progress to sessionStorage
  useEffect(() => {
    if (!quizDone && sessionId && docId) {
      sessionStorage.setItem(`quiz_${docId}_currentQ`, currentQ.toString());
      sessionStorage.setItem(`quiz_${docId}_sessionId`, sessionId);
    }
  }, [currentQ, sessionId, docId, quizDone]);

  const resetQuiz = () => {
    setCurrentQ(0); setSelected(null); setShowResult(false);
    setScore(0); setQuizDone(false); setTimer(30);
    // Clear sessionStorage
    if (docId) {
      sessionStorage.removeItem(`quiz_${docId}_currentQ`);
      sessionStorage.removeItem(`quiz_${docId}_sessionId`);
    }
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
        <EmptyState
          emoji="⏳️"
          title="Đang tải câu hỏi..."
          description="Vui lòng chờ trong giây lát"
        />
      </Page>
    );
  }

  const handleInlineUpload = async (file: File) => {
    const validExts = [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".webp"];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));
    if (!validExts.includes(ext)) {
      return;
    }
    if (file.size > 10 * 1024 * 1024) return;

    setUploading(true);
    setUploadProgress("⚡ Đang trích xuất nội dung...");
    try {
      const result = await documentService.fastUpload(file, "quiz");
      setUploadProgress("🧠 Đang tạo Quiz từ file...");
      // Reload quiz with the new doc_id
      window.location.href = `/quiz?doc_id=${result.id}`;
    } catch (err: any) {
      setUploadProgress("❌ " + (err.message || "Lỗi xử lý file"));
      setTimeout(() => {
        setUploading(false);
        setUploadProgress("");
      }, 2000);
    }
  };

  if (total === 0 && !uploading) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 80px)", gap: 20 }}>
          
          {/* Header */}
          <Box style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", marginBottom: 8 }}>
            <Box onClick={() => nav("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 18, color: "var(--color-text-secondary)" }} />
            </Box>
            <Text style={{ fontSize: 20, fontWeight: 900, color: "var(--color-text-primary)" }}>🧠 Quiz & Flashcard</Text>
          </Box>

          {/* Upload Area */}
          <Box style={{
            width: "100%", maxWidth: 380, padding: "32px 24px", textAlign: "center",
            borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)",
            border: "2px dashed #6366F1",
          }}>
            <Text style={{ fontSize: 48, lineHeight: 1, marginBottom: 12 }}>📄</Text>
            <Text style={{ fontSize: 18, fontWeight: 900, color: "#4338CA", marginBottom: 6 }}>
              Tải file lên để làm Quiz
            </Text>
            <Text style={{ fontSize: 13, color: "#6366F1", lineHeight: 1.5, marginBottom: 20 }}>
              AI sẽ trích xuất TẤT CẢ câu hỏi trong file
              {"\n"}+ tạo Flashcard tự động
            </Text>

            {/* Quick Action Buttons */}
            <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
              <Box onClick={() => cameraInputRef.current?.click()} style={{
                padding: "14px 8px", borderRadius: 14,
                background: "linear-gradient(135deg,#10B981,#059669)",
                color: "white", cursor: "pointer", textAlign: "center",
                boxShadow: "0 4px 12px rgba(16,185,129,0.3)",
              }}>
                <Text style={{ fontSize: 22, lineHeight: 1, marginBottom: 4 }}>📸</Text>
                <Text style={{ fontSize: 12, fontWeight: 700, color: "white" }}>Chụp đề thi</Text>
              </Box>
              <Box onClick={() => fileInputRef.current?.click()} style={{
                padding: "14px 8px", borderRadius: 14,
                background: "linear-gradient(135deg,#8B5CF6,#7C3AED)",
                color: "white", cursor: "pointer", textAlign: "center",
                boxShadow: "0 4px 12px rgba(139,92,246,0.3)",
              }}>
                <Text style={{ fontSize: 22, lineHeight: 1, marginBottom: 4 }}>📁</Text>
                <Text style={{ fontSize: 12, fontWeight: 700, color: "white" }}>Chọn file</Text>
              </Box>
            </Box>

            <Text style={{ fontSize: 11, color: "#818CF8", fontWeight: 600 }}>
              PDF, Word, Ảnh — Không giới hạn số câu
            </Text>
          </Box>

          {/* Existing documents */}
          {allDocs.length > 0 && (
            <Box style={{ width: "100%", maxWidth: 380 }}>
              <Text style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                📚 Hoặc chọn tài liệu đã có:
              </Text>
              {allDocs.slice(0, 5).map((doc: any) => (
                <Box key={doc.id} onClick={() => {
                  window.location.href = `/quiz?doc_id=${doc.id}`;
                }} style={{
                  padding: "12px 16px", borderRadius: 12, marginBottom: 6,
                  background: "var(--color-bg-card)", border: "1px solid var(--color-border)",
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 10,
                }}>
                  <Text style={{ fontSize: 16 }}>📖</Text>
                  <Text style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-primary)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {doc.name || "Tài liệu"}
                  </Text>
                  <Icon icon="zi-chevron-right" style={{ fontSize: 14, color: "var(--color-text-tertiary)" }} />
                </Box>
              ))}
            </Box>
          )}

          <Box onClick={() => nav("/")} style={{
            marginTop: 4, padding: "12px 28px", borderRadius: "var(--radius-md)",
            background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
            cursor: "pointer",
          }}>
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: "var(--color-text-secondary)" }}>🏠 Về trang chủ</Text>
          </Box>

          {/* Hidden inputs */}
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleInlineUpload(f); e.target.value = ""; }}
            style={{ display: "none" }} />
          <input ref={cameraInputRef} type="file" accept="image/*" capture="environment"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleInlineUpload(f); e.target.value = ""; }}
            style={{ display: "none" }} />
        </Box>
      </Page>
    );
  }

  // Uploading state
  if (uploading) {
    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 80px)", gap: 20 }}>
          <Box style={{
            width: 56, height: 56, borderRadius: "50%",
            border: "3px solid #E9D5FF", borderTopColor: "#8B5CF6",
            animation: "spin 1s linear infinite",
          }} />
          <Text style={{ fontSize: 16, fontWeight: 800, color: "#7C3AED" }}>{uploadProgress}</Text>
          <Text style={{ fontSize: 13, color: "var(--color-text-tertiary)" }}>Đang xử lý file, vui lòng chờ...</Text>
        </Box>
      </Page>
    );
  }

  /* Review Screen */
  if (reviewMode && reviewData) {
    const item = reviewData.questions[reviewIdx];

    return (
      <Page className="ch-page">
        <Box className="ch-container" style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - 80px)", gap: 16 }}>
          {/* Header */}
          <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Box onClick={() => { setReviewMode(false); setReviewIdx(0); }} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 18, color: "var(--color-text-secondary)" }} />
            </Box>
            <Box>
              <Text className="ch-caption" style={{ fontWeight: 600 }}>XEM LẠI CÂU SAI</Text>
              <Text className="ch-heading-lg" style={{ marginTop: 2 }}>{reviewIdx + 1} / {reviewData.questions.length}</Text>
            </Box>
          </Box>

          {/* Progress */}
          <Box style={{ marginBottom: 6 }}>
            <Box className="ch-progress">
              <Box className="ch-progress-bar" style={{ width: `${((reviewIdx + 1) / reviewData.questions.length) * 100}%` }} />
            </Box>
          </Box>

          {/* Question */}
          <Box style={{
            background: item.is_correct ? "var(--color-success-light)" : "var(--color-danger-light)",
            borderRadius: "var(--radius-lg)", padding: "20px",
            border: `2px solid ${item.is_correct ? "var(--color-success)" : "var(--color-danger)"}`,
          }}>
            <Box style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Text style={{ fontSize: 24, lineHeight: 1 }}>{item.is_correct ? "✅" : "❌"}</Text>
              <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 700, color: item.is_correct ? "var(--color-success)" : "var(--color-danger)" }}>
                {item.is_correct ? "Đáp án đúng" : `Sai - Đáp án: ${String.fromCharCode(65 + item.correct)}`}
              </Text>
            </Box>
            <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 700, color: "var(--color-text-primary)", lineHeight: 1.6 }}>
              {item.question}
            </Text>
          </Box>

          {/* Options (read-only) */}
          <Box style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {item.options.map((opt: string, idx: number) => (
              <Box key={idx} className={`ch-quiz-option ${idx === item.correct ? "correct" : (idx === item.your_answer.charCodeAt(0) - 65 ? "wrong" : "")}`}
                style={{ cursor: "default" }}
              >
                <Box className="ch-quiz-option-label">{String.fromCharCode(65 + idx)}</Box>
                <Text style={{ flex: 1, fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>{opt}</Text>
                {idx === item.correct && <Text style={{ fontSize: 20, lineHeight: 1 }}>✅</Text>}
                {idx === item.your_answer.charCodeAt(0) - 65 && idx !== item.correct && <Text style={{ fontSize: 20, lineHeight: 1 }}>❌</Text>}
              </Box>
            ))}
          </Box>

          {/* Explanation */}
          <Box className="ch-explanation" style={{ marginTop: 12 }}>
            <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "#92400E", lineHeight: 1.6 }}>
              💡 {item.explanation}
            </Text>
          </Box>

          {/* Navigation */}
          <Box style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: "auto", paddingBottom: 8 }}>
            <Box className="ch-fab ch-fab--secondary" onClick={() => setReviewIdx(i => Math.max(0, i - 1))} style={{ width: 50, height: 50 }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 22, color: "var(--color-text-secondary)" }} />
            </Box>
            <Box className="ch-fab ch-fab--primary" onClick={() => {
              if (reviewIdx + 1 >= reviewData.questions.length) {
                setReviewMode(false); setReviewIdx(0);
              } else {
                setReviewIdx(i => i + 1);
              }
            }} style={{ width: 58, height: 58 }}>
              <Text style={{ fontSize: 24, lineHeight: 1 }}>{reviewIdx + 1 >= reviewData.questions.length ? "🏠" : "🔄"}</Text>
            </Box>
            <Box className="ch-fab ch-fab--secondary" onClick={() => {
              if (reviewIdx + 1 >= reviewData.questions.length) {
                setReviewMode(false); setReviewIdx(0);
              } else {
                setReviewIdx(i => Math.min(i + 1, reviewData.questions.length - 1));
              }
            }} style={{ width: 50, height: 50 }}>
              <Icon icon="zi-chevron-right" style={{ fontSize: 22, color: "var(--color-text-secondary)" }} />
            </Box>
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
    const shareText = studyService.generateQuizShareText(
      { correct: score, total, percentage: percent, grade: msg.title },
      questions[0]?.category || "Quiz"
    );

    const handleShare = async () => {
      try {
        // Show share card preview first
        setShowShareCard(true);
      } catch (e) {
        // User cancelled share
      }
    };

    const handleReview = async () => {
      if (!sessionId) return;
      const data = await studyService.getQuizReview(sessionId);
      setReviewData(data);
      setReviewIdx(0);
      setReviewMode(true);
    };

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

          {/* Review Button */}
          {reviewData && reviewData.wrong > 0 && (
            <Box className="ch-btn-secondary" onClick={handleReview} style={{ width: "100%", maxWidth: 280, justifyContent: "center" }}>
              <Text style={{ fontSize: 18 }}>📝</Text>
              <span>Xem lại {reviewData.wrong} câu sai</span>
            </Box>
          )}

          {/* Share Button */}
          <Box className="ch-btn-secondary" onClick={handleShare} style={{ width: "100%", maxWidth: 280, justifyContent: "center" }}>
            <Text style={{ fontSize: 18 }}>📤</Text>
            <span>Chia sẻ kết quả</span>
          </Box>

          {/* Next Document Suggestion */}
          {allDocs.filter((d: any) => d.id !== docId).length > 0 && (
            <Box style={{ width: "100%", maxWidth: 280 }}>
              <Text className="ch-caption" style={{ marginBottom: 8, textAlign: "center" }}>📚 Học tiếp tài liệu khác:</Text>
              {allDocs.filter((d: any) => d.id !== docId).slice(0, 3).map((doc: any) => (
                <Box key={doc.id} className="ch-btn-secondary" onClick={() => {
                  nav(`/quiz?doc=${doc.id}`);
                  resetQuiz();
                }} style={{ width: "100%", justifyContent: "center", marginBottom: 6 }}>
                  <Text style={{ fontSize: 16 }}>📖</Text>
                  <span>{doc.name || "Tài liệu"}</span>
                </Box>
              ))}
            </Box>
          )}

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

        {/* Share Card Modal */}
        {showShareCard && (
          <Box
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.75)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10000,
              padding: 20,
              backdropFilter: "blur(4px)",
            }}
            onClick={() => setShowShareCard(false)}
          >
            <Box
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "100%",
                maxWidth: 360,
                background: "transparent",
                borderRadius: 20,
                padding: 20,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <QuizShareCard
                score={score}
                total={total}
                percentage={percent}
                docName={docId || "Quiz"}
              />
              <Text
                style={{
                  marginTop: 16,
                  fontSize: 12,
                  color: "rgba(255,255,255,0.7)",
                  textAlign: "center",
                }}
              >
                Chạm để đóng
              </Text>
            </Box>
          </Box>
        )}
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
            {selected != null && selected < 0 ? (
              <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "#6B7280", lineHeight: 1.6 }}>
                ⏭️ Bạn đã bỏ qua câu này.
                {question && (() => {
                  const correctIdx = question.options.findIndex((o: any) => o.isCorrect);
                  return correctIdx >= 0 ? ` Đáp án đúng: ${String.fromCharCode(65 + correctIdx)}` : "";
                })()}
              </Text>
            ) : selected != null ? (
              <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: "#92400E", lineHeight: 1.6 }}>
                💡 {question?.explanation}
              </Text>
            ) : null}
          </Box>
        )}

        {/* Skip & Next Buttons */}
        {!showResult ? (
          <Box className="ch-btn-secondary animate-slide-up" onClick={() => handleSelect(-1)}
            style={{ marginTop: 16, width: "100%", justifyContent: "center" }}>
            <Text style={{ fontSize: 16 }}>⏭️</Text>
            <span>Bỏ qua (Skip)</span>
          </Box>
        ) : (
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

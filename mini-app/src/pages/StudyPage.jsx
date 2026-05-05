import { useEffect, useState, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const tabs = {
  welcome: 'Chọn chế độ',
  chat: '💬 Chat Hay',
  learn: '🎯 Học tập'
};

export default function StudyPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const docId = location.state?.docId;
  const chatEndRef = useRef(null);

  const [currentTab, setCurrentTab] = useState('welcome');

  // Chat state
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');

  // Learn state (quiz/flashcard - giữ nguyên từ code cũ)
  const [mode, setMode] = useState('select'); // select, quiz, flashcard, result
  const [quiz, setQuiz] = useState(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [score, setScore] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);

  const [flashcards, setFlashcards] = useState([]);
  const [currentCard, setCurrentCard] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [cardRating, setCardRating] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [coinsEarned, setCoinsEarned] = useState(0);

  useEffect(() => {
    if (!docId) {
      navigate('/vault');
    }
  }, [docId, navigate]);

  // Auto scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Chat functions
  const sendMessage = async () => {
    if (!question.trim() || chatLoading) return;

    const userMsg = { role: 'user', content: question.trim() };
    setMessages(prev => [...prev, userMsg]);
    setQuestion('');
    setChatLoading(true);
    setChatError('');

    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) throw new Error('Vui lòng đăng nhập');
      const user = JSON.parse(userStr);

      const headers = { 'X-User-Id': user.id };
      const response = await fetch(`${API_BASE_URL}/api/miniapp/chat/ask`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: docId,
          question: userMsg.content
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Không thể nhận câu trả lời');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources || [] }]);
    } catch (err) {
      setChatError(err.message);
    } finally {
      setChatLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Start Quiz (giữ nguyên)
  const startQuiz = async () => {
    setLoading(true);
    setError('');
    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) throw new Error('Vui lòng đăng nhập');
      const user = JSON.parse(userStr);

      const headers = { 'X-User-Id': user.id };
      const response = await fetch(`${API_BASE_URL}/api/miniapp/quiz/start`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Không thể tạo Quiz');
      }

      const data = await response.json();
      setQuiz(data);
      setAnswers(new Array(data.questions.length).fill(null));
      setCurrentQ(0);
      setShowResult(false);
      setScore(0);
      setSelectedOption(null);
      setShowExplanation(false);
      setMode('quiz');
      setCurrentTab('learn');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Submit Answer
  const submitAnswer = useCallback(async (questionIdx, selectedIdx) => {
    if (selectedIdx === null) return;

    const newAnswers = [...answers];
    newAnswers[questionIdx] = selectedIdx;
    setAnswers(newAnswers);
    setSelectedOption(selectedIdx);
    setShowExplanation(true);

    try {
      const userStr = localStorage.getItem('user');
      const user = JSON.parse(userStr);
      await fetch(`${API_BASE_URL}/api/miniapp/quiz/answer`, {
        method: 'POST',
        headers: { 'X-User-Id': user.id, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: docId,
          question_index: questionIdx,
          selected_answer: selectedIdx,
        }),
      });
    } catch (err) {
      console.error('Submit answer error:', err);
    }
  }, [answers, docId]);

  // Next Question
  const nextQuestion = () => {
    if (currentQ < quiz.questions.length - 1) {
      setCurrentQ(currentQ + 1);
      setSelectedOption(null);
      setShowExplanation(false);
    } else {
      let correct = 0;
      quiz.questions.forEach((q, idx) => {
        if (answers[idx] === q.correct_answer) correct++;
      });
      setScore(correct);
      setShowResult(true);
      setMode('result');

      if (correct >= quiz.questions.length * 0.7) {
        setCoinsEarned(50);
      }
    }
  };

  // Start Flashcard
  const startFlashcard = async () => {
    setLoading(true);
    setError('');
    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) throw new Error('Vui lòng đăng nhập');
      const user = JSON.parse(userStr);

      const headers = { 'X-User-Id': user.id };
      const response = await fetch(`${API_BASE_URL}/api/miniapp/flashcard/start`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Không thể tạo Flashcard');
      }

      const data = await response.json();
      setFlashcards(data.cards || []);
      setCurrentCard(0);
      setFlipped(false);
      setCardRating(null);
      setMode('flashcard');
      setCurrentTab('learn');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Review Flashcard
  const reviewFlashcard = async (quality) => {
    setCardRating(quality);

    try {
      const userStr = localStorage.getItem('user');
      const user = JSON.parse(userStr);
      await fetch(`${API_BASE_URL}/api/miniapp/flashcard/review`, {
        method: 'POST',
        headers: { 'X-User-Id': user.id, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          card_id: flashcards[currentCard].id,
          quality: quality,
        }),
      });
    } catch (err) {
      console.error('Review error:', err);
    }

    setTimeout(() => {
      if (currentCard < flashcards.length - 1) {
        setCurrentCard(currentCard + 1);
        setFlipped(false);
        setCardRating(null);
      } else {
        alert('🎉 Hoàn thành bộ Flashcard! +30 Coin');
        setCoinsEarned(30);
        setMode('select');
        setCurrentTab('learn');
      }
    }, 300);
  };

  if (!docId) return null;

  // WELCOME TAB
  if (currentTab === 'welcome') {
    return (
      <div className="p-4 space-y-6 fade-in-up pb-safe">
        <div className="text-center pt-4 pb-6 rounded-b-3xl" style={{
          background: 'linear-gradient(135deg, #58cc02 0%, #1cb0f6 100%)',
          margin: '-1rem -1rem 0 -1rem',
          padding: '2rem 1rem 3rem 1rem'
        }}>
          <h1 className="text-5xl font-black text-white mb-2 bounce-in" style={{
            textShadow: '0 4px 0 rgba(0,0,0,0.2)'
          }}>CHỌN CHẾ ĐỘ</h1>
          <p className="text-white font-bold text-lg" style={{opacity: 0.95}}>Học tập thông minh với AI ✨</p>
        </div>

        {/* Chat Hay Card */}
        <button
          onClick={() => setCurrentTab('chat')}
          className="card w-full flex flex-col items-center gap-4 py-10 lift-on-hover bounce-in"
          style={{
            background: 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 50%, #60a5fa 100%)',
            borderColor: '#3b82f6',
            borderWidth: '3px',
            boxShadow: '0 8px 0 #1d4ed8, 0 12px 30px rgba(59, 130, 246, 0.3)'
          }}
        >
          <span className="text-7xl bounce-in" style={{animationDelay: '0s'}}>💬</span>
          <div className="text-center">
            <div className="text-2xl font-black text-blue-900 mb-2">Chat Hay</div>
            <div className="text-sm text-blue-800 font-medium max-w-xs">Hỏi đáp nhanh với AI về tài liệu của bạn</div>
          </div>
          <div className="badge badge-business mt-3 text-lg py-2 px-6">Hỏi bất cứ điều gì</div>
        </button>

        {/* AI Learning Card */}
        <button
          onClick={() => setCurrentTab('learn')}
          className="card w-full flex flex-col items-center gap-4 py-10 lift-on-hover bounce-in"
          style={{
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fbbf24 100%)',
            borderColor: '#f59e0b',
            borderWidth: '3px',
            boxShadow: '0 8px 0 #d97706, 0 12px 30px rgba(251, 191, 36, 0.3)'
          }}
        >
          <span className="text-7xl bounce-in" style={{animationDelay: '0.1s'}}>🎯</span>
          <div className="text-center">
            <div className="text-2xl font-black text-yellow-900 mb-2">AI Learning</div>
            <div className="text-sm text-yellow-800 font-medium max-w-xs">Quiz & Flashcard được tạo tự động từ tài liệu</div>
          </div>
          <div className="badge badge-education mt-3 text-lg py-2 px-6">+50 Coin nếu đạt ≥70%</div>
        </button>

        {/* Tips */}
        <div className="card text-center py-4" style={{
          background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
          borderColor: '#10b981',
          borderWidth: '2px'
        }}>
          <p className="text-sm font-bold text-green-800">
            💡 <strong>Mẹo:</strong> Dùng Chat Hay để hiểu nhanh, dùng AI Learning để ghi nhớ lâu dài
          </p>
        </div>
      </div>
    );
  }

  // CHAT TAB
  if (currentTab === 'chat') {
    return (
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="p-4 border-b-3 border-blue-200 bg-gradient-to-r from-blue-50 to-sky-50">
          <button
            onClick={() => setCurrentTab('welcome')}
            className="text-blue-600 font-black text-sm mb-2 flex items-center gap-1"
          >
            ← Quay lại chọn chế độ
          </button>
          <h1 className="text-2xl font-black text-blue-900">💬 Chat Hay</h1>
          <p className="text-xs text-blue-600 font-medium">Hỏi đáp về tài liệu của bạn</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🤖</div>
              <p className="text-gray-600 font-bold text-lg">Bắt đầu trò chuyện!</p>
              <p className="text-sm text-gray-500 mt-2">Hỏi AI bất cứ điều gì về tài liệu này</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-md bounce-in ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white rounded-br-md'
                    : 'bg-gray-100 text-gray-800 rounded-bl-md'
                }`}
                style={{
                  borderWidth: msg.role === 'user' ? '0' : '2px',
                  borderColor: msg.role === 'user' ? 'transparent' : '#e5e7eb'
                }}
              >
                <div className="whitespace-pre-wrap font-medium leading-relaxed">{msg.content}</div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-blue-200/30">
                    <p className="text-xs font-black mb-2 opacity-80">📎 Nguồn:</p>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((src, sIdx) => (
                        <span
                          key={sIdx}
                          className="text-xs px-2 py-1 rounded-full font-bold bg-white/20 backdrop-blur"
                          style={{
                            backgroundColor: msg.role === 'user' ? 'rgba(255,255,255,0.2)' : '#f3f4f6',
                            color: msg.role === 'user' ? 'white' : '#374151'
                          }}
                        >
                          {src.file_name || 'File'} {src.page && `- Trang ${src.page}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-800 rounded-2xl rounded-bl-md px-4 py-3 shadow-md">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></span>
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></span>
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></span>
                </div>
              </div>
            </div>
          )}

          {chatError && (
            <div className="bg-red-50 border-2 border-red-200 text-red-700 p-3 rounded-xl font-medium">
              ❌ {chatError}
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t-3 border-gray-100 bg-white">
          <div className="flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Nhập câu hỏi..."
              className="flex-1 px-4 py-3 rounded-2xl border-3 border-gray-200 focus:border-blue-500 focus:outline-none font-medium"
              disabled={chatLoading}
            />
            <button
              onClick={sendMessage}
              disabled={chatLoading || !question.trim()}
              className="px-6 py-3 rounded-2xl font-black text-white shadow-md disabled:opacity-50 disabled:cursor-not-allowed bounce-in"
              style={{
                background: 'linear-gradient(135deg, #58cc02 0%, #46a703 100%)',
                border: 'none',
                boxShadow: '0 4px 0 #3d8b02'
              }}
            >
              Gửi
            </button>
          </div>
        </div>
      </div>
    );
  }

  // LEARN TAB - giữ nguyên toàn bộ code quiz/flashcard
  if (currentTab === 'learn') {
    // SELECT MODE
    if (mode === 'select' || mode === undefined) {
      return (
        <div className="p-4 space-y-6 fade-in-up pb-safe">
          <div className="text-center pt-2">
            <button onClick={() => setCurrentTab('welcome')} className="text-blue-500 text-sm mb-2">
              ← Quay lại
            </button>
            <h1 className="text-3xl font-black gradient-text mb-2">🎯 Chọn chế độ học</h1>
            <p className="text-gray-600 font-medium">Làm Quiz hoặc lật Flashcard</p>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-200 text-red-700 p-4 rounded-xl font-medium fade-in-up">
              ❌ {error}
            </div>
          )}

          <div className="space-y-4">
            <button
              onClick={startQuiz}
              disabled={loading}
              className="card w-full flex flex-col items-center gap-4 py-8 lift-on-hover disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%)',
                borderColor: '#3b82f6',
                borderWidth: '3px'
              }}
            >
              <div className="text-6xl">📝</div>
              <div>
                <div className="text-2xl font-black text-gray-800 mb-1">Làm Quiz</div>
                <div className="text-sm text-gray-600 font-medium">10 câu hỏi trắc nghiệm</div>
              </div>
              <div className="badge badge-education mt-2">+50 Coin nếu đạt ≥70%</div>
            </button>

            <button
              onClick={startFlashcard}
              disabled={loading}
              className="card w-full flex flex-col items-center gap-4 py-8 lift-on-hover disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                borderColor: '#f59e0b',
                borderWidth: '3px'
              }}
            >
              <div className="text-6xl">🃏</div>
              <div>
                <div className="text-2xl font-black text-gray-800 mb-1">Flashcard 3D</div>
                <div className="text-sm text-gray-600 font-medium">Lật thẻ để ghi nhớ</div>
              </div>
              <div className="badge badge-business mt-2">+30 Coin khi hoàn thành</div>
            </button>
          </div>

          <div className="card bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-300">
            <div className="text-center">
              <div className="text-3xl font-black text-orange-600 mb-2">💡 Aha Moment</div>
              <p className="text-sm text-orange-800 font-medium">
                AI tự động tạo Quiz & Flashcard từ tài liệu của bạn chỉ trong 15 giây!
              </p>
            </div>
          </div>
        </div>
      );
    }

    // LOADING STATE
    if (loading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
            <p className="mt-4 text-gray-600 font-bold">AI đang xử lý...</p>
          </div>
        </div>
      );
    }

    // QUIZ MODE
    if (mode === 'quiz' && quiz) {
      const question = quiz.questions[currentQ];
      const isLast = currentQ === quiz.questions.length - 1;
      const isAnswered = answers[currentQ] !== null;

      return (
        <div className="p-4 space-y-6 fade-in-up pb-safe">
          {/* Header */}
          <div className="flex justify-between items-center bg-blue-50 px-4 py-3 rounded-2xl" style={{border: '3px solid #3b82f6'}}>
            <button onClick={() => { setMode('select'); setCurrentTab('welcome'); }} className="text-blue-600 font-black text-sm hover:scale-105 transition-transform">
              ← Quay lại
            </button>
            <div className="flex items-center gap-2 bg-yellow-100 px-3 py-1 rounded-full" style={{border: '2px solid #fbbf24'}}>
              <span className="text-2xl">⭐</span>
              <span className="font-black text-yellow-700">{score} điểm</span>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-black">
              <span className="text-blue-700">Câu {currentQ + 1} / {quiz.questions.length}</span>
              <span className="text-blue-600 bg-blue-100 px-2 py-1 rounded-full">{Math.round(((currentQ + 1) / quiz.questions.length) * 100)}%</span>
            </div>
            <div className="progress-bar h-4" style={{background: '#dbeafe'}}>
              <div
                className="progress-fill"
                style={{
                  width: `${((currentQ + 1) / quiz.questions.length) * 100}%`,
                  background: 'linear-gradient(90deg, #1cb0f6, #58cc02)',
                  boxShadow: '0 0 10px rgba(28, 176, 246, 0.5)'
                }}
              ></div>
            </div>
          </div>

          {/* Question Card */}
          <div className="card bounce-in" style={{
            background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
            borderColor: '#1cb0f6',
            borderWidth: '3px'
          }}>
            <h2 className="text-2xl font-black mb-6 leading-relaxed text-gray-800">{question.question}</h2>

            <div className="space-y-3">
              {question.options.map((opt, idx) => {
                let optionClass = 'quiz-option';

                if (isAnswered) {
                  if (idx === question.correct_answer) {
                    optionClass += ' correct';
                  } else if (idx === selectedOption && idx !== question.correct_answer) {
                    optionClass += ' wrong';
                  }
                } else if (selectedOption === idx) {
                  optionClass += ' selected';
                }

                return (
                  <button
                    key={idx}
                    onClick={() => !isAnswered && submitAnswer(currentQ, idx)}
                    disabled={isAnswered}
                    className={`${optionClass} w-full text-left p-5 bounce-in`}
                    style={{
                      animationDelay: `${idx * 0.1}s`,
                      borderWidth: '3px',
                      transform: selectedOption === idx ? 'scale(1.02)' : 'scale(1)'
                    }}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center font-black text-lg ${
                        isAnswered && idx === question.correct_answer
                          ? 'bg-green-500 text-white shadow-lg'
                          : isAnswered && idx === selectedOption && idx !== question.correct_answer
                          ? 'bg-red-500 text-white shadow-lg'
                          : selectedOption === idx
                          ? 'bg-blue-500 text-white shadow-lg'
                          : 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-600'
                      }`} style={{boxShadow: '0 4px 0 rgba(0,0,0,0.2)'}}>
                        {isAnswered && idx === question.correct_answer ? '✓' :
                         isAnswered && idx === selectedOption && idx !== question.correct_answer ? '✗' :
                         String.fromCharCode(65 + idx)}
                      </div>
                      <span className="text-lg font-bold">{opt}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Explanation */}
          {showExplanation && (
            <div className="card fade-in-up" style={{
              background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
              borderColor: '#3b82f6',
              borderWidth: '3px'
            }}>
              <div className="flex items-start gap-3">
                <span className="text-3xl">💡</span>
                <div>
                  <div className="font-black text-blue-900 mb-2 text-lg">Giải thích:</div>
                  <p className="text-blue-800 font-medium">{question.explanation}</p>
                </div>
              </div>
            </div>
          )}

          {/* Next Button */}
          <button
            onClick={nextQuestion}
            disabled={!isAnswered}
            className="btn text-lg py-5 bounce-in disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: 'linear-gradient(135deg, #58cc02 0%, #46a703 100%)',
              color: 'white',
              border: 'none',
              boxShadow: '0 6px 0 #3d8b02, 0 8px 20px rgba(88, 204, 2, 0.3)',
              fontWeight: 900,
              fontSize: '1.25rem'
            }}
          >
            {isLast ? '🎉 Xem kết quả' : 'Câu tiếp theo →'}
          </button>
        </div>
      );
    }

    // RESULT MODE
    if (mode === 'result') {
      const percentage = Math.round((score / quiz.questions.length) * 100);
      const passed = score >= quiz.questions.length * 0.7;

      return (
        <div className="p-4 space-y-6 text-center fade-in-up pb-safe">
          <div className="pt-4">
            {passed ? (
              <div className="bounce-in">
                <div className="success-check">✓</div>
              </div>
            ) : (
              <div className="text-8xl mb-4 wiggle">💪</div>
            )}

            <h1 className="text-4xl font-black mb-2 bounce-in" style={{
              color: passed ? '#58cc02' : '#f97316',
              textShadow: passed ? '0 4px 0 #3d8b02' : '0 4px 0 #c2410c'
            }}>
              {passed ? 'Xuất sắc!' : 'Cố gắng hơn!'}
            </h1>
            <p className="text-gray-700 font-bold text-lg">
              Bạn đúng {score}/{quiz.questions.length} câu ({percentage}%)
            </p>
          </div>

          <div className="card bounce-in" style={{
            background: passed
              ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)'
              : 'linear-gradient(135deg, #fed7aa 0%, #fdba74 100%)',
            borderColor: passed ? '#22c55e' : '#f97316',
            borderWidth: '3px'
          }}>
            <div className="text-6xl font-black gradient-text mb-4">{score}/{quiz.questions.length}</div>
            <div className="space-y-3 text-left">
              <div className="flex justify-between items-center bg-white bg-opacity-50 p-2 rounded-lg">
                <span className="font-bold">📊 Tỷ lệ đúng</span>
                <span className="font-black text-lg">{percentage}%</span>
              </div>
              <div className="flex justify-between items-center bg-white bg-opacity-50 p-2 rounded-lg">
                <span className="font-bold">⏱️ Thời gian</span>
                <span className="font-black">~2 phút</span>
              </div>
              <div className="flex justify-between items-center bg-white bg-opacity-50 p-2 rounded-lg">
                <span className="font-bold">💰 Coin nhận được</span>
                <span className={`font-black text-lg ${passed ? 'text-yellow-600' : 'text-gray-500'}`}>
                  {passed ? `+${coinsEarned} 🎉` : '0'}
                </span>
              </div>
            </div>
          </div>

          {passed && (
            <div className="card shimmer" style={{
              background: 'linear-gradient(135deg, #fef08a 0%, #fde047 50%, #facc15 100%)',
              borderColor: '#eab308',
              borderWidth: '3px'
            }}>
              <div className="text-center">
                <div className="text-5xl font-black text-yellow-700 mb-2 bounce-in">🎉</div>
                <p className="text-yellow-900 font-black text-lg">Chúc mừng! Bạn đã đạt 70%+</p>
                <p className="text-yellow-800 font-bold mt-2">+50 Coin đã được cộng vào ví 💰</p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => { setMode('select'); setQuiz(null); setCoinsEarned(0); }}
              className="btn text-lg py-4 bounce-in"
              style={{
                background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
                color: '#4338ca',
                border: '3px solid #818cf8',
                fontWeight: 900
              }}
            >
              ↺ Làm lại Quiz
            </button>
            <button
              onClick={() => setCurrentTab('welcome')}
              className="btn text-lg py-4 bounce-in"
              style={{
                background: 'linear-gradient(135deg, #58cc02 0%, #46a703 100%)',
                color: 'white',
                border: 'none',
                boxShadow: '0 6px 0 #3d8b02',
                fontWeight: 900
              }}
            >
              Về trang chọn →
            </button>
          </div>
        </div>
      );
    }

    // FLASHCARD MODE
    if (mode === 'flashcard' && flashcards.length > 0) {
      const card = flashcards[currentCard];
      const isLast = currentCard === flashcards.length - 1;

      return (
        <div className="p-4 space-y-6 fade-in-up pb-safe">
          {/* Header */}
          <div className="flex justify-between items-center bg-purple-50 px-4 py-3 rounded-2xl" style={{border: '3px solid #a855f7'}}>
            <button onClick={() => { setMode('select'); setCurrentTab('welcome'); }} className="text-purple-600 font-black text-sm hover:scale-105 transition-transform">
              ← Quay lại
            </button>
            <div className="flex items-center gap-2 bg-purple-100 px-3 py-1 rounded-full" style={{border: '2px solid #c084fc'}}>
              <span className="text-2xl">🃏</span>
              <span className="font-black text-purple-700">{currentCard + 1}/{flashcards.length}</span>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-black">
              <span className="text-purple-700">Tiến độ Flashcard</span>
              <span className="text-purple-600 bg-purple-100 px-2 py-1 rounded-full">{Math.round(((currentCard + 1) / flashcards.length) * 100)}%</span>
            </div>
            <div className="progress-bar h-4" style={{background: '#e9d5ff'}}>
              <div
                className="progress-fill"
                style={{
                  width: `${((currentCard + 1) / flashcards.length) * 100}%`,
                  background: 'linear-gradient(90deg, #a855f7, #ec4899)',
                  boxShadow: '0 0 10px rgba(168, 85, 247, 0.5)'
                }}
              ></div>
            </div>
          </div>

          {/* 3D Flashcard */}
          <div
            onClick={() => !cardRating && setFlipped(!flipped)}
            className="flashcard-container bounce-in"
            style={{perspective: '1000px', height: '350px'}}
          >
            <div className={`flashcard ${flipped ? 'flipped' : ''}`} style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              transformStyle: 'preserve-3d',
              transition: 'transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              transform: flipped ? 'rotateY(180deg)' : 'rotateY(0)'
            }}>
              <div className="flashcard-face flashcard-front" style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                backfaceVisibility: 'hidden',
                background: 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 50%, #60a5fa 100%)',
                border: '4px solid #3b82f6',
                borderRadius: '2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem'
              }}>
                <div className="text-center">
                  <div className="text-sm font-black text-blue-800 mb-4 uppercase tracking-widest">CÂU HỎI</div>
                  <div className="text-3xl font-black text-blue-900 leading-relaxed">{card.front}</div>
                  <div className="mt-8 text-blue-700 text-lg">
                    {!flipped ? '👆 Nhấn để lật' : '📝 Đánh giá bên dưới'}
                  </div>
                </div>
              </div>
              <div className="flashcard-face flashcard-back" style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                backfaceVisibility: 'hidden',
                transform: 'rotateY(180deg)',
                background: 'linear-gradient(135deg, #faf5ff 0%, #e9d5ff 50%, #d8b4fe 100%)',
                border: '4px solid #a855f7',
                borderRadius: '2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem'
              }}>
                <div className="text-center">
                  <div className="text-sm font-black text-purple-800 mb-4 uppercase tracking-widest">ĐÁP ÁN</div>
                  <div className="text-3xl font-black text-purple-900 leading-relaxed">{card.back}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Rating Buttons */}
          {flipped && !cardRating && (
            <div className="space-y-3 fade-in-up">
              <p className="text-center text-sm font-black text-gray-700 mb-2">Bạn thấy thẻ này thế nào?</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => reviewFlashcard(1)}
                  className="py-4 px-4 rounded-2xl font-black text-white text-lg bounce-in"
                  style={{
                    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                    border: 'none',
                    boxShadow: '0 4px 0 #991b1b',
                    animationDelay: '0s'
                  }}
                >
                  🔥 Khó
                </button>
                <button
                  onClick={() => reviewFlashcard(2)}
                  className="py-4 px-4 rounded-2xl font-black text-white text-lg bounce-in"
                  style={{
                    background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                    border: 'none',
                    boxShadow: '0 4px 0 #9a3412',
                    animationDelay: '0.1s'
                  }}
                >
                  😕 Lẫn lộn
                </button>
                <button
                  onClick={() => reviewFlashcard(3)}
                  className="py-4 px-4 rounded-2xl font-black text-white text-lg bounce-in"
                  style={{
                    background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                    border: 'none',
                    boxShadow: '0 4px 0 #15803d',
                    animationDelay: '0.2s'
                  }}
                >
                  🙂 Khá
                </button>
                <button
                  onClick={() => reviewFlashcard(4)}
                  className="py-4 px-4 rounded-2xl font-black text-white text-lg bounce-in"
                  style={{
                    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                    border: 'none',
                    boxShadow: '0 4px 0 #1e40af',
                    animationDelay: '0.3s'
                  }}
                >
                  😎 Dễ
                </button>
              </div>
            </div>
          )}

          {cardRating && (
            <div className="card text-center fade-in-up" style={{
              background: 'linear-gradient(135deg, #faf5ff 0%, #e9d5ff 100%)',
              borderColor: '#a855f7',
              borderWidth: '3px'
            }}>
              <div className="text-3xl font-black text-purple-600 mb-2">
                {cardRating <= 2 ? '🔄 Sẽ gặp lại sớm!' : cardRating === 3 ? '✓ Tốt! Tiếp tục' : '🎉 Xuất sắc!'}
              </div>
              <div className="text-sm text-purple-700 font-bold">Đang chuyển sang thẻ tiếp theo...</div>
            </div>
          )}

          {/* Completion */}
          {isLast && flipped && cardRating && (
            <div className="card shimmer text-center" style={{
              background: 'linear-gradient(135deg, #faf5ff 0%, #e9d5ff 50%, #d8b4fe 100%)',
              borderColor: '#a855f7',
              borderWidth: '3px'
            }}>
              <div className="text-6xl font-black text-purple-600 mb-2 bounce-in">🎉</div>
              <p className="font-black text-purple-900 text-xl mb-1">Hoàn thành!</p>
              <p className="text-purple-800 font-bold">+30 Coin đã được cộng 💰</p>
            </div>
          )}
        </div>
      );
    }

    return null;
  }

  return null;
}

import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useRef, useEffect } from "react";
import { documentService } from "../services/documentService";
import { useAuth } from "../hooks/useAuth";
import {
  IconChevronLeft, IconCamera, IconImage, IconDoc,
  IconRefresh, IconLightbulb, IconQuiz,
} from "../components/icons";

const SendIcon = ({ size = 20, color = "white" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} stroke="none"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
);
const PlusIcon = ({ size = 22, color = "currentColor" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
);
const SparkleIcon = ({ size = 20, color = "#FBBF24" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} stroke="none"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/></svg>
);

interface ChatMessage {
  id: string; role: "user" | "ai"; type: "text" | "image" | "solution";
  content: string; imageUrl?: string;
  solution?: { question: string; steps: string[]; answer: string };
}

/* ─── Typing dots ─── */
function TypingDots() {
  return (
    <Box style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "4px 0" }}>
      <Box style={{
        width: 36, height: 36, borderRadius: "50%", flexShrink: 0,
        background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 3px 12px rgba(139,92,246,0.3)",
      }}><SparkleIcon size={18} color="white" /></Box>
      <Box style={{
        padding: "16px 20px", borderRadius: "20px 20px 20px 6px",
        background: "white", border: "1px solid #E5E7EB",
        display: "flex", gap: 6, alignItems: "center",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        {[0, 1, 2].map(i => (
          <Box key={i} style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
            animation: `bounce 1.4s ease-in-out ${i * 0.16}s infinite`,
            opacity: 0.6,
          }} />
        ))}
        <Text style={{ fontSize: 12, color: "#9CA3AF", marginLeft: 4, fontWeight: 500 }}>Đang suy nghĩ...</Text>
      </Box>
    </Box>
  );
}

/* ─── Solution Card ─── */
function SolutionCard({ solution, onQuiz }: {
  solution: { question: string; steps: string[]; answer: string }; onQuiz: () => void;
}) {
  return (
    <Box style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Box style={{ padding: "14px 16px", borderRadius: 16, background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)", border: "1px solid #C7D2FE" }}>
        <Text style={{ fontSize: 10, fontWeight: 800, color: "#6366F1", letterSpacing: "0.08em", marginBottom: 6 }}>📋 ĐỀ BÀI</Text>
        <Text style={{ fontSize: 14, color: "#1E1B4B", lineHeight: 1.7, fontWeight: 600 }}>{solution.question}</Text>
      </Box>
      {solution.steps.map((step, i) => (
        <Box key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "12px 14px", borderRadius: 14, background: "#FFFBEB", borderLeft: "4px solid #F59E0B" }}>
          <Box style={{ width: 24, height: 24, borderRadius: "50%", background: "linear-gradient(135deg, #F59E0B, #D97706)", color: "white", fontSize: 11, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</Box>
          <Text style={{ fontSize: 13, color: "#1C1917", lineHeight: 1.7, flex: 1 }}>{step}</Text>
        </Box>
      ))}
      <Box style={{ padding: "16px", borderRadius: 16, background: "linear-gradient(135deg, #7C3AED, #EC4899)", boxShadow: "0 6px 20px rgba(124,58,237,0.3)" }}>
        <Text style={{ fontSize: 10, fontWeight: 800, color: "rgba(255,255,255,0.7)", letterSpacing: "0.08em", marginBottom: 4 }}>🎯 ĐÁP ÁN</Text>
        <Text style={{ fontSize: 17, fontWeight: 900, color: "white", lineHeight: 1.4 }}>{solution.answer}</Text>
      </Box>
      <Box onClick={onQuiz} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: "12px", borderRadius: 14, background: "linear-gradient(135deg, #EEF2FF, #FCE7F3)", border: "1px solid #C7D2FE", cursor: "pointer" }}>
        <IconQuiz size={16} color="#7C3AED" />
        <Text style={{ fontSize: 13, fontWeight: 700, color: "#7C3AED" }}>✨ Tạo Quiz ôn tập từ bài giải</Text>
      </Box>
    </Box>
  );
}

/* ─── Chat Bubble ─── */
function Bubble({ msg, onQuiz }: { msg: ChatMessage; onQuiz: () => void }) {
  const isUser = msg.role === "user";
  return (
    <Box style={{ display: "flex", flexDirection: isUser ? "row-reverse" : "row", alignItems: "flex-end", gap: 8, animation: "slideUp 0.3s ease-out" }}>
      {!isUser && (
        <Box style={{ width: 36, height: 36, borderRadius: "50%", flexShrink: 0, background: "linear-gradient(135deg, #8B5CF6, #EC4899)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 3px 12px rgba(139,92,246,0.3)" }}>
          <SparkleIcon size={18} color="white" />
        </Box>
      )}
      <Box style={{
        maxWidth: isUser ? "75%" : "82%",
        padding: msg.type === "image" ? 6 : "14px 18px",
        borderRadius: isUser ? "20px 20px 6px 20px" : "20px 20px 20px 6px",
        background: isUser ? "linear-gradient(135deg, #7C3AED, #6366F1)" : "white",
        border: isUser ? "none" : "1px solid #E5E7EB",
        boxShadow: isUser ? "0 4px 16px rgba(124,58,237,0.25)" : "0 2px 8px rgba(0,0,0,0.04)",
      }}>
        {msg.type === "image" && msg.imageUrl && (
          <img src={msg.imageUrl} alt="" style={{ width: "100%", maxWidth: 220, borderRadius: 16, display: "block" }} />
        )}
        {msg.type === "text" && (
          <Text style={{ fontSize: 14, lineHeight: 1.7, color: isUser ? "white" : "#1C1917", whiteSpace: "pre-wrap" }}>{msg.content}</Text>
        )}
        {msg.type === "solution" && msg.solution && <SolutionCard solution={msg.solution} onQuiz={onQuiz} />}
      </Box>
    </Box>
  );
}

/* ═══ MAIN PAGE ═══ */
function SolveProblemPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const camRef = useRef<HTMLInputElement>(null);
  const galRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [showMenu, setShowMenu] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [thinking, setThinking] = useState(false);
  const [lastSolution, setLastSolution] = useState<any>(null);
  const [suggestedPrompts, setSuggestedPrompts] = useState([
    { emoji: "📐", text: "Giải phương trình x² - 5x + 6 = 0", color: "#6366F1", tag: "" },
    { emoji: "📊", text: "Tính tích phân ∫(2x+1)dx từ 0 đến 3", color: "#EC4899", tag: "" },
    { emoji: "🧪", text: "Cân bằng phương trình: Fe + O₂ → Fe₂O₃", color: "#F59E0B", tag: "" },
  ]);

  useEffect(() => {
    // Fetch documents to generate smart FOMO suggestions
    documentService.getDocuments().then(docs => {
      if (docs && docs.length > 0) {
        // Lấy 3 file gần nhất, bỏ đuôi mở rộng
        const recentDocs = docs.slice(0, 3).map(d => d.name.replace(/\.[^/.]+$/, ""));
        const newPrompts: any[] = [];
        
        if (recentDocs[0]) {
           newPrompts.push({ emoji: "🔥", text: `Giải chi tiết câu 5 trong "${recentDocs[0]}"`, color: "#EF4444", tag: "Nhiều bạn đang hỏi" });
        }
        if (recentDocs[1]) {
           newPrompts.push({ emoji: "🎯", text: `Giải thích kiến thức khó nhất bài "${recentDocs[1]}"`, color: "#8B5CF6", tag: "Tài liệu của bạn" });
        }
        if (recentDocs[2]) {
           newPrompts.push({ emoji: "💡", text: `Mẹo giải nhanh dạng bài trong "${recentDocs[2]}"`, color: "#F59E0B", tag: "Hot hôm nay" });
        }

        const defaults = [
          { emoji: "📐", text: "Giải phương trình x² - 5x + 6 = 0", color: "#6366F1", tag: "" },
          { emoji: "📊", text: "Tính tích phân ∫(2x+1)dx từ 0 đến 3", color: "#EC4899", tag: "" },
        ];
        
        while (newPrompts.length < 3 && defaults.length > 0) {
           newPrompts.push(defaults.shift() as any);
        }

        setSuggestedPrompts(newPrompts);
      }
    }).catch(e => console.warn("Failed to fetch docs for suggestions", e));
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, thinking]);

  const add = (m: Omit<ChatMessage, "id">) => setMessages(p => [...p, { ...m, id: Date.now().toString() + Math.random() }]);

  const handleImg = async (file: File) => {
    const url = URL.createObjectURL(file);
    add({ role: "user", type: "image", content: "" , imageUrl: url });
    setThinking(true);
    try {
      const r = await documentService.solveProblem(file);
      setLastSolution(r);
      add({ role: "ai", type: "solution", content: "", solution: r });
    } catch (e: any) {
      add({ role: "ai", type: "text", content: `Mình không đọc được ảnh này 😔\n\nHãy thử:\n• Chụp rõ nét hơn\n• Đủ ánh sáng\n• Chỉ chụp phần đề bài\n\nRồi gửi lại cho mình nhé! 📸` });
    } finally { setThinking(false); }
  };

  const handleSend = () => {
    const t = text.trim(); if (!t || thinking) return;
    setText(""); add({ role: "user", type: "text", content: t });
    setThinking(true);
    setTimeout(() => {
      add({ role: "ai", type: "text", content: `Mình hiểu câu hỏi của bạn rồi! 🧠\n\nĐể giải chính xác nhất, bạn hãy:\n\n📸 Chụp ảnh đề bài → mình OCR + giải chi tiết\n📝 Hoặc gõ rõ đề bài với đầy đủ số liệu\n\nMình sẵn sàng giúp bạn! ✨` });
      setThinking(false);
    }, 1200);
  };

  const handleQuiz = async () => {
    if (!lastSolution) return;
    try {
      const q = await documentService.generateQuizFromSolution(lastSolution);
      if (q?.length) { add({ role: "ai", type: "text", content: `✅ Đã tạo ${q.length} câu Quiz!\nChuyển sang làm Quiz ngay nào... 🚀` }); setTimeout(() => navigate("/quiz", { state: { fromSolution: true, questions: q } }), 1000); }
    } catch { add({ role: "ai", type: "text", content: "Chưa tạo được Quiz, bạn thử lại nhé 😊" }); }
  };

  const chipAction = (a: string) => {
    if (a === "cam") camRef.current?.click();
    else if (a === "gal") galRef.current?.click();
    else { setText(a); inputRef.current?.focus(); }
  };

  const empty = messages.length === 0;

  return (
    <Page className="ch-page" style={{ paddingBottom: 0 }}>
      <input ref={camRef} type="file" accept="image/*" capture="environment" onChange={e => { const f = e.target.files?.[0]; if (f) handleImg(f); e.target.value = ""; }} style={{ display: "none" }} />
      <input ref={galRef} type="file" accept="image/*" onChange={e => { const f = e.target.files?.[0]; if (f) handleImg(f); e.target.value = ""; }} style={{ display: "none" }} />

      <Box style={{ display: "flex", flexDirection: "column", height: "100vh", maxWidth: 480, margin: "0 auto", background: "#F8F7FF" }}>

        {/* ═══ HEADER ═══ */}
        <Box style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 14px", background: "white",
          borderBottom: "1px solid #EDE9FE",
          boxShadow: "0 1px 4px rgba(139,92,246,0.06)",
        }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Box onClick={() => navigate("/ai-learning")} style={{
              width: 36, height: 36, borderRadius: 12, background: "#F5F3FF",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
            }}><IconChevronLeft size={18} color="#7C3AED" /></Box>
            <Box style={{
              width: 40, height: 40, borderRadius: 14,
              background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 4px 14px rgba(139,92,246,0.3)",
            }}><SparkleIcon size={20} color="white" /></Box>
            <Box>
              <Text style={{ fontSize: 16, fontWeight: 900, color: "#1E1B4B", letterSpacing: "-0.01em" }}>Chat Hay AI</Text>
              <Box style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Box style={{ width: 6, height: 6, borderRadius: "50%", background: "#22C55E", animation: "pulseGlow 2s ease-in-out infinite" }} />
                <Text style={{ fontSize: 11, color: "#22C55E", fontWeight: 600 }}>Sẵn sàng giúp bạn</Text>
              </Box>
            </Box>
          </Box>
          <Box onClick={() => { setMessages([]); setLastSolution(null); }} style={{
            width: 36, height: 36, borderRadius: 12, background: "#F5F3FF",
            display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
          }}><IconRefresh size={16} color="#7C3AED" /></Box>
        </Box>

        {/* ═══ CHAT AREA ═══ */}
        <Box style={{ flex: 1, overflowY: "auto", padding: "16px 14px", display: "flex", flexDirection: "column", gap: 16 }}>

          {empty && (
            <Box style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: "0 8px" }}>
              {/* Hero icon */}
              <Box style={{ position: "relative" }}>
                <Box style={{
                  width: 88, height: 88, borderRadius: 28,
                  background: "linear-gradient(135deg, #8B5CF6, #EC4899)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: "0 12px 36px rgba(139,92,246,0.3)",
                  animation: "floatOrb 4s ease-in-out infinite",
                }}>
                  <Text style={{ fontSize: 42 }}>🤖</Text>
                </Box>
                <Box style={{
                  position: "absolute", top: -4, right: -4,
                  width: 28, height: 28, borderRadius: "50%",
                  background: "linear-gradient(135deg, #FBBF24, #F59E0B)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: "0 2px 8px rgba(245,158,11,0.4)",
                  animation: "bounce 2s ease-in-out infinite",
                }}><Text style={{ fontSize: 14 }}>✨</Text></Box>
              </Box>

              <Box style={{ textAlign: "center" }}>
                <Text style={{ fontSize: 22, fontWeight: 900, color: "#1E1B4B", marginBottom: 6 }}>
                  Chào bạn! 👋
                </Text>
                <Text style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.7 }}>
                  Mình là <strong style={{ color: "#7C3AED" }}>Chat Hay</strong> — trợ lý AI học tập
                  <br />Chụp ảnh hoặc gõ câu hỏi, mình giải ngay!
                </Text>
              </Box>

              {/* ─── BIG ACTION BUTTONS ─── */}
              <Box style={{ display: "flex", gap: 10, width: "100%", marginTop: 4 }}>
                <Box onClick={() => camRef.current?.click()} style={{
                  flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
                  padding: "20px 12px", borderRadius: 20,
                  background: "linear-gradient(160deg, #7C3AED, #6366F1)",
                  boxShadow: "0 6px 20px rgba(124,58,237,0.3)",
                  cursor: "pointer", transition: "transform 0.2s",
                }}>
                  <Box style={{
                    width: 48, height: 48, borderRadius: 16,
                    background: "rgba(255,255,255,0.2)", backdropFilter: "blur(8px)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}><Text style={{ fontSize: 26 }}>📸</Text></Box>
                  <Text style={{ fontSize: 13, fontWeight: 700, color: "white", textAlign: "center" }}>
                    Chụp ảnh{"\n"}bài tập
                  </Text>
                </Box>
                <Box onClick={() => galRef.current?.click()} style={{
                  flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
                  padding: "20px 12px", borderRadius: 20,
                  background: "linear-gradient(160deg, #EC4899, #F43F5E)",
                  boxShadow: "0 6px 20px rgba(236,72,153,0.3)",
                  cursor: "pointer", transition: "transform 0.2s",
                }}>
                  <Box style={{
                    width: 48, height: 48, borderRadius: 16,
                    background: "rgba(255,255,255,0.2)", backdropFilter: "blur(8px)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}><Text style={{ fontSize: 26 }}>🖼️</Text></Box>
                  <Text style={{ fontSize: 13, fontWeight: 700, color: "white", textAlign: "center" }}>
                    Chọn ảnh{"\n"}từ máy
                  </Text>
                </Box>
              </Box>

              {/* ─── SUGGESTED PROMPTS ─── */}
              <Box style={{ width: "100%", marginTop: 4 }}>
                <Text style={{ fontSize: 11, fontWeight: 700, color: "#9CA3AF", letterSpacing: "0.06em", marginBottom: 8, paddingLeft: 4 }}>
                  💡 HOẶC THỬ HỎI NGAY
                </Text>
                {suggestedPrompts.map((item, i) => (
                  <Box key={i} onClick={() => chipAction(item.text)} style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "13px 16px", marginBottom: 8, borderRadius: 16,
                    background: "white", border: "1px solid #E5E7EB",
                    cursor: "pointer", boxShadow: "0 1px 4px rgba(0,0,0,0.03)",
                    transition: "all 0.2s", position: "relative", overflow: "hidden",
                  }}>
                    {item.tag && (
                      <Box style={{
                        position: "absolute", top: 0, right: 0,
                        background: `linear-gradient(135deg, ${item.color}, ${item.color}DD)`,
                        padding: "2px 8px", borderRadius: "0 15px 0 10px",
                      }}>
                        <Text style={{ fontSize: 9, fontWeight: 800, color: "white" }}>{item.tag}</Text>
                      </Box>
                    )}
                    <Box style={{
                      width: 36, height: 36, borderRadius: 12,
                      background: `${item.color}12`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 18, flexShrink: 0,
                    }}>{item.emoji}</Box>
                    <Text style={{ fontSize: 13, color: "#374151", fontWeight: 600, lineHeight: 1.4, flex: 1, marginTop: item.tag ? 4 : 0 }}>
                      {item.text}
                    </Text>
                    <Box style={{ color: "#D1D5DB", fontSize: 16 }}>›</Box>
                  </Box>
                ))}
              </Box>

              {/* Tip */}
              <Box style={{
                width: "100%", padding: "12px 16px", borderRadius: 14,
                background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
                border: "1px solid #FCD34D",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <Text style={{ fontSize: 22 }}>💡</Text>
                <Text style={{ fontSize: 12, color: "#92400E", lineHeight: 1.5, fontWeight: 500 }}>
                  <strong>Mẹo:</strong> Chụp rõ đề bài, AI sẽ nhận diện và giải chi tiết trong ~15 giây!
                </Text>
              </Box>
            </Box>
          )}

          {messages.map(m => <Bubble key={m.id} msg={m} onQuiz={handleQuiz} />)}
          {thinking && <TypingDots />}
          <div ref={endRef} />
        </Box>

        {/* ═══ INPUT BAR ═══ */}
        <Box style={{
          padding: "10px 12px", paddingBottom: "max(12px, env(safe-area-inset-bottom))",
          background: "white", borderTop: "1px solid #EDE9FE",
          boxShadow: "0 -2px 8px rgba(139,92,246,0.04)",
        }}>
          {showMenu && (
            <Box style={{ display: "flex", gap: 10, marginBottom: 10, animation: "slideUp 0.2s ease-out" }}>
              {[
                { icon: "📸", label: "Camera", color: "#7C3AED", action: () => camRef.current?.click() },
                { icon: "🖼️", label: "Thư viện", color: "#EC4899", action: () => galRef.current?.click() },
                { icon: "📁", label: "Tài liệu", color: "#F59E0B", action: () => navigate("/file-processing") },
              ].map((item, i) => (
                <Box key={i} onClick={() => { item.action(); setShowMenu(false); }} style={{
                  flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
                  padding: "14px 8px", borderRadius: 16,
                  background: `${item.color}08`, border: `1.5px solid ${item.color}20`,
                  cursor: "pointer",
                }}>
                  <Text style={{ fontSize: 24 }}>{item.icon}</Text>
                  <Text style={{ fontSize: 11, fontWeight: 700, color: item.color }}>{item.label}</Text>
                </Box>
              ))}
            </Box>
          )}

          <Box style={{
            display: "flex", alignItems: "flex-end", gap: 8,
            background: "#F5F3FF", borderRadius: 24,
            padding: "6px 6px 6px 6px",
            border: "1.5px solid #DDD6FE",
          }}>
            <Box onClick={() => setShowMenu(!showMenu)} style={{
              width: 38, height: 38, borderRadius: "50%", flexShrink: 0,
              background: showMenu ? "linear-gradient(135deg, #7C3AED, #6366F1)" : "#EDE9FE",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", transform: showMenu ? "rotate(45deg)" : "none",
              transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
            }}><PlusIcon size={20} color={showMenu ? "white" : "#7C3AED"} /></Box>

            <textarea ref={inputRef} value={text} onChange={e => setText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Gõ câu hỏi hoặc gửi ảnh bài tập..."
              rows={1} style={{
                flex: 1, border: "none", outline: "none", resize: "none",
                background: "transparent", fontSize: 14, lineHeight: 1.5,
                color: "#1E1B4B", padding: "8px 4px",
                fontFamily: "inherit", maxHeight: 100, minHeight: 22,
              }} />

            <Box onClick={thinking ? undefined : handleSend} style={{
              width: 38, height: 38, borderRadius: "50%", flexShrink: 0,
              background: text.trim()
                ? "linear-gradient(135deg, #7C3AED, #EC4899)"
                : "#DDD6FE",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: text.trim() ? "pointer" : "default",
              transition: "all 0.3s",
              boxShadow: text.trim() ? "0 3px 12px rgba(124,58,237,0.3)" : "none",
            }}><SendIcon size={17} color={text.trim() ? "white" : "#A78BFA"} /></Box>
          </Box>
        </Box>
      </Box>
    </Page>
  );
}

export default SolveProblemPage;

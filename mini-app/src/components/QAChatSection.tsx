import { Box, Text } from "zmp-ui";
import { useState, useEffect, useRef, useCallback } from "react";

interface QAChatSectionProps {
  docId: string;
  docName?: string;
  setToast: (toast: { message: string; type: "error" | "success" | "info" }) => void;
}

function QAChatSection({ docId, docName, setToast }: QAChatSectionProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [asking, setAsking] = useState(false);
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);
  const messagesEndRef = useRef<any>(null);
  const containerRef = useRef<any>(null);
  const inputRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages, asking]);

  // Text selection handler
  const handleTextSelect = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      setTooltip(null);
      return;
    }
    const selectedText = sel.toString().trim();
    if (selectedText.length < 5 || selectedText.length > 500) {
      setTooltip(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (!containerRect) return;

    setTooltip({
      text: selectedText,
      x: rect.left - containerRect.left + rect.width / 2,
      y: rect.bottom - containerRect.top + 8,
    });
  }, []);

  useEffect(() => {
    document.addEventListener("selectionchange", handleTextSelect);
    return () => document.removeEventListener("selectionchange", handleTextSelect);
  }, [handleTextSelect]);

  // Ask about selected text
  const askAboutSelection = () => {
    if (!tooltip) return;
    const q = `Giải thích chi tiết đoạn này: "${tooltip.text}"`;
    setQuestion("");
    setTooltip(null);
    window.getSelection()?.removeAllRanges();
    setMessages(prev => [...prev, { role: "user", text: q }]);
    sendQuestion(q);
  };

  const sendQuestion = async (q: string) => {
    setAsking(true);
    try {
      const resp = await fetch("/api/miniapp/chat/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: docId, question: q }),
      });
      const data = await resp.json();
      setMessages(prev => [...prev, { role: "ai", text: data.answer || "Không có phản hồi." }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Xin lỗi, không thể trả lời lúc này." }]);
    }
    setAsking(false);
  };

  const ask = async () => {
    if (!question.trim() || asking) return;
    const q = question.trim();
    setMessages(prev => [...prev, { role: "user", text: q }]);
    setQuestion("");
    if (window.ZMP) window.ZMP.hapticFeedback("medium");
    await sendQuestion(q);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setToast({ message: "📋 Đã sao chép!", type: "success" });
      if (window.ZMP) window.ZMP.hapticFeedback("light");
    } catch {
      setToast({ message: "Không thể sao chép", type: "error" });
    }
  };

  const quickPrompts = ["📌 Tóm tắt chính", "💡 Điểm quan trọng", "🎓 Bài học rút ra"];

  return (
    <Box ref={containerRef} style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative" }}>
      {/* Floating Tooltip */}
      {tooltip && (
        <Box
          onClick={askAboutSelection}
          style={{
            position: "absolute",
            left: Math.max(10, Math.min(tooltip.x - 90, 220)),
            top: tooltip.y,
            zIndex: 100,
            background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
            color: "white",
            padding: "10px 16px",
            borderRadius: 12,
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            boxShadow: "0 8px 24px rgba(99,102,241,0.40)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            animation: "fadeIn 0.2s ease-out",
            whiteSpace: "nowrap",
          }}
        >
          <span style={{ fontSize: 16 }}>💬</span> Hỏi AI về đoạn này
          <Box style={{
            position: "absolute", top: -6, left: "50%", transform: "translateX(-50%)",
            width: 0, height: 0,
            borderLeft: "6px solid transparent", borderRight: "6px solid transparent",
            borderBottom: "6px solid #8B5CF6",
          }} />
        </Box>
      )}

      {/* Scrollable Content */}
      <Box style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 0, paddingBottom: 8 }}>
        {/* Divider */}
        <Box style={{
          display: "flex", alignItems: "center", gap: 12, padding: "8px 0 16px",
        }}>
          <Box style={{ flex: 1, height: 1, background: "var(--color-border)" }} />
          <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-tertiary)", letterSpacing: "0.05em" }}>
            💬 HỎI ĐÁP VỀ TÀI LIỆU
          </Text>
          <Box style={{ flex: 1, height: 1, background: "var(--color-border)" }} />
        </Box>

        {/* Quick Prompts */}
        {messages.length === 0 && (
          <Box style={{ textAlign: "center", padding: "12px 0 16px" }}>
            <Text style={{ fontSize: 14, color: "var(--color-text-tertiary)", marginBottom: 12 }}>
              Hỏi bất kỳ điều gì về tài liệu này 👇
            </Text>
            <Box style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
              {quickPrompts.map(prompt => (
                <Box
                  key={prompt}
                  onClick={() => { setQuestion(prompt); inputRef.current?.focus(); }}
                  style={{
                    padding: "9px 16px", borderRadius: "var(--radius-full)",
                    background: "var(--color-primary-lighter)",
                    border: "1px solid rgba(91,76,219,0.20)",
                    cursor: "pointer", fontSize: 13, fontWeight: 600,
                    color: "var(--color-primary-dark)", transition: "all 0.2s",
                    boxShadow: "0 2px 6px rgba(0,0,0,0.03)",
                  }}
                >
                  {prompt}
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {/* Messages */}
        {messages.map((m, i) => (
          <Box
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "88%",
              padding: "12px 16px",
              borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
              background: m.role === "user" ? "var(--gradient-primary)" : "var(--color-bg-card)",
              color: m.role === "user" ? "white" : "var(--color-text-primary)",
              border: m.role === "ai" ? "1px solid var(--color-border)" : "none",
              fontSize: 15, lineHeight: 1.6, marginBottom: 12,
              boxShadow: m.role === "user" ? "0 4px 12px rgba(59,130,246,0.25)" : "var(--shadow-sm)",
              animation: m.role === "ai" ? "slideIn 0.3s ease-out" : "none",
              position: "relative",
            }}
          >
            {m.text}
            {m.role === "ai" && (
              <Box
                onClick={() => copyToClipboard(m.text)}
                style={{
                  position: "absolute",
                  top: 6, right: 6,
                  width: 28, height: 28,
                  borderRadius: "var(--radius-full)",
                  background: "rgba(0,0,0,0.05)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: "pointer",
                  opacity: 0.7,
                  transition: "opacity 0.2s",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: m.role === "ai" ? "var(--color-text-secondary)" : "white" }}>
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </Box>
            )}
          </Box>
        ))}

        {/* Loading indicator */}
        {asking && (
          <Box style={{ alignSelf: "flex-start", padding: "12px 16px", borderRadius: 18,
            background: "var(--color-bg-card)", border: "1px solid var(--color-border)",
            animation: "fadeIn 0.3s ease-out", boxShadow: "var(--shadow-sm)", marginBottom: 12 }}>
            <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Text style={{ fontSize: 14, color: "var(--color-text-tertiary)" }}>AI đang suy nghĩ</Text>
              <Box style={{ display: "flex", gap: 4 }}>
                <Box style={{ width: 6, height: 6, borderRadius: "50%", background: "#9E9BB8", animation: "bounce 1.4s infinite ease-in-out 0s" }} />
                <Box style={{ width: 6, height: 6, borderRadius: "50%", background: "#9E9BB8", animation: "bounce 1.4s infinite ease-in-out 0.2s" }} />
                <Box style={{ width: 6, height: 6, borderRadius: "50%", background: "#9E9BB8", animation: "bounce 1.4s infinite ease-in-out 0.4s" }} />
              </Box>
            </Box>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box style={{
        display: "flex", gap: 10, paddingTop: 14,
        borderTop: "1px solid var(--color-border)",
        background: "var(--color-bg-page)",
      }}>
        <input
          ref={inputRef}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === "Enter" && ask()}
          placeholder="Hỏi về tài liệu..."
          style={{
            flex: 1, padding: "14px 20px", borderRadius: 24,
            border: "1px solid var(--color-border)", background: "var(--color-bg-subtle)",
            fontSize: 15, fontFamily: "var(--font-family)", outline: "none",
            boxShadow: "inset 0 2px 4px rgba(0,0,0,0.02)",
          }}
        />
        <button onClick={ask} disabled={asking || !question.trim()} style={{
          padding: "0 24px", borderRadius: 24,
          background: "var(--gradient-primary)", color: "white", border: "none",
          fontWeight: 700, fontSize: 15, cursor: "pointer", fontFamily: "var(--font-family)",
          opacity: asking || !question.trim() ? 0.5 : 1,
          transition: "all 0.2s",
          boxShadow: "0 4px 12px rgba(59,130,246,0.3)",
        }}>Gửi</button>
      </Box>
    </Box>
  );
}

export default QAChatSection;

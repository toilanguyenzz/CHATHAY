import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef, useCallback } from "react";
import { documentService } from "../services/documentService";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { getGreeting } from "../utils/greeting";
import { useSharedFile } from "../contexts/SharedFileContext";
import {
  IconDoc, IconUpload, IconChevronLeft, IconChevronRight,
  IconRefresh, IconAlertTriangle, IconInbox, IconSearch,
  IconFolder, IconFlashcard, IconQuiz, IconCamera, IconImage,
} from "../components/icons";

/* ─── Skeleton ─── */
function Skeleton({ w = "100%", h = 20, r = 10, style }: { w?: string | number; h?: number; r?: number; style?: React.CSSProperties }) {
  return <Box className="ch-skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

/* ─── Toast ─── */
function Toast({ message, type, onClose }: { message: string; type: "error" | "success" | "info"; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 4000); return () => clearTimeout(t); }, [onClose]);
  return <Box className={`ch-toast ch-toast--${type}`}>{message}</Box>;
}

/* ─── Unified Summary + Q&A Panel ─── */
function SummaryWithQA({ doc }: { doc: any }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [asking, setAsking] = useState(false);
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => { scrollToBottom(); }, [messages, asking]);

  // ── Text selection handler ──
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
    // Get position relative to container
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (!containerRect) return;

    setTooltip({
      text: selectedText,
      x: rect.left - containerRect.left + rect.width / 2,
      y: rect.bottom - containerRect.top + 8, // Show BELOW selection
    });
  }, []);

  useEffect(() => {
    document.addEventListener("selectionchange", handleTextSelect);
    return () => document.removeEventListener("selectionchange", handleTextSelect);
  }, [handleTextSelect]);

  // ── Ask about selected text ──
  const askAboutSelection = () => {
    if (!tooltip) return;
    const q = `Giải thích chi tiết đoạn này: "${tooltip.text}"`;
    setQuestion("");
    setTooltip(null);
    window.getSelection()?.removeAllRanges();
    // Send immediately
    setMessages(prev => [...prev, { role: "user", text: q }]);
    sendQuestion(q);
  };

  const sendQuestion = async (q: string) => {
    setAsking(true);
    try {
      const resp = await apiClient.post<{ answer: string }>("/api/miniapp/chat/ask", {
        document_id: doc.id, question: q,
      });
      setMessages(prev => [...prev, { role: "ai", text: resp.answer }]);
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
    sendQuestion(q);
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

      {/* ── Floating Tooltip for text selection ── */}
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
          {/* Arrow - point up to selection */}
          <Box style={{
            position: "absolute", top: -6, left: "50%", transform: "translateX(-50%)",
            width: 0, height: 0,
            borderLeft: "6px solid transparent", borderRight: "6px solid transparent",
            borderBottom: "6px solid #8B5CF6",
          }} />
        </Box>
      )}

      {/* ── Scrollable Content: Summary + Chat ── */}
      <Box style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 0, paddingBottom: 8 }}>

        {/* ── Summary Section ── */}
        <Box ref={summaryRef} style={{ padding: "0 0 16px 0" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <Box style={{
              width: 28, height: 28, borderRadius: 8,
              background: "linear-gradient(135deg, #3B82F6, #6366F1)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <IconDoc size={14} color="white" />
            </Box>
            <Text style={{ fontSize: 15, fontWeight: 800, color: "var(--color-text-primary)" }}>
              📋 Tóm tắt nội dung
            </Text>
          </Box>
          <Box style={{
            padding: "16px 18px",
            borderRadius: 16,
            background: "linear-gradient(135deg, #F8FAFF, #EEF2FF)",
            border: "1px solid rgba(99,102,241,0.12)",
            userSelect: "text",
            WebkitUserSelect: "text",
          }}>
            <Text style={{
              fontSize: 15, color: "var(--color-text-primary)", lineHeight: 1.85,
              whiteSpace: "pre-wrap",
            }}>
              {doc.summary || "Chưa có tóm tắt cho tài liệu này."}
            </Text>
          </Box>
          {/* Hint */}
          <Box style={{
            display: "flex", alignItems: "center", gap: 6, marginTop: 10,
            padding: "8px 12px", borderRadius: 10,
            background: "rgba(139,92,246,0.06)", border: "1px dashed rgba(139,92,246,0.20)",
          }}>
            <Text style={{ fontSize: 12, color: "#7C3AED", fontWeight: 600 }}>
              💡 Mẹo: Bôi đen bất kỳ đoạn nào ở trên để AI giải thích chi tiết cho bạn!
            </Text>
          </Box>

          {/* TTS Play Button */}
          <Box style={{
            display: "flex", alignItems: "center", gap: 10, marginTop: 10,
            padding: "10px 16px", borderRadius: "var(--radius-lg)",
            background: "linear-gradient(135deg, #8B5CF6, #6D28D9)",
            border: "none", cursor: "pointer", color: "white",
          }}
            onClick={() => {
              if (!doc.summary) return;
              if (window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
                setToast({ message: "⏹️ Đã dừng đọc", type: "info" });
                return;
              }
              const utterance = new SpeechSynthesisUtterance(doc.summary);
              utterance.lang = "vi-VN";
              utterance.rate = 0.9;
              window.speechSynthesis.speak(utterance);
              setToast({ message: "🔊 Đang đọc tóm tắt...", type: "info" });
            }}
          >
            <Text style={{ fontSize: 18 }}>🔊</Text>
            <Text style={{ fontSize: 13, fontWeight: 700 }}>
              Nghe tóm tắt
            </Text>
          </Box>

          {/* Share Button — Viral Loop */}
          <Box
            onClick={() => {
              const shareText = `📄 Tóm tắt "${doc.name}":\n\n${doc.summary?.substring(0, 200)}${doc.summary && doc.summary.length > 200 ? '...' : ''}\n\n📚 Xem thêm tại Chat Hay — Trợ lý AI đọc tài liệu!`;
              if (window.ZMP) {
                window.ZMP.shareAppMessage({
                  title: `Tóm tắt: ${doc.name}`,
                  desc: shareText,
                  type: "share",
                });
              }
            }}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              marginTop: 12,
              padding: "12px",
              borderRadius: "var(--radius-full)",
              background: "linear-gradient(135deg, #00BFA5, #00C853)",
              color: "white",
              fontSize: 13, fontWeight: 700,
              cursor: "pointer",
              boxShadow: "0 4px 12px rgba(0,191,165,0.30)",
              transition: "all 0.2s",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
              <polyline points="16 6 12 2 8 6" />
              <line x1="12" y1="2" x2="12" y2="15" />
            </svg>
            📤 Chia sẻ tóm tắt cho bạn bè
          </Box>
        </Box>

        {/* ── Divider ── */}
        <Box style={{
          display: "flex", alignItems: "center", gap: 12, padding: "8px 0 16px",
        }}>
          <Box style={{ flex: 1, height: 1, background: "var(--color-border)" }} />
          <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-tertiary)", letterSpacing: "0.05em" }}>
            💬 HỎI ĐÁP VỀ TÀI LIỆU
          </Text>
          <Box style={{ flex: 1, height: 1, background: "var(--color-border)" }} />
        </Box>

        {/* ── Chat Messages ── */}
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

      {/* ── Rename Modal ── */}
      {renameDoc && (
        <Box style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 9999, padding: 20,
        }}>
          <Box style={{
            width: "100%", maxWidth: 320,
            background: "white", borderRadius: "var(--radius-xl)",
            padding: "24px", boxShadow: "var(--shadow-xl)",
            animation: "scaleIn 0.2s var(--ease-spring)",
          }}>
            <Text style={{ fontSize: 16, fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 8 }}>
              ✏️ Đổi tên tài liệu
            </Text>
            <Text style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
              Tên mới cho tài liệu:
            </Text>
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              autoFocus
              style={{
                width: "100%", padding: "12px 16px", borderRadius: "var(--radius-lg)",
                border: "1.5px solid var(--color-border)", background: "var(--color-bg-subtle)",
                fontSize: 15, fontFamily: "var(--font-family)", outline: "none",
                boxSizing: "border-box",
              }}
            />
            <Box style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button
                onClick={() => { setRenameDoc(null); setNewName(""); }}
                style={{
                  flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                  background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
                  color: "var(--color-text-secondary)", fontWeight: 700, fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Hủy
              </button>
              <button
                onClick={handleRename}
                disabled={!newName.trim()}
                style={{
                  flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                  background: newName.trim() ? "var(--gradient-primary)" : "var(--color-bg-subtle)",
                  border: "none",
                  color: newName.trim() ? "white" : "var(--color-text-tertiary)",
                  fontWeight: 700, fontSize: 14,
                  cursor: newName.trim() ? "pointer" : "not-allowed",
                }}
              >
                Lưu
              </button>
            </Box>
          </Box>
        </Box>
      )}

      {/* ── Fixed Input Area ── */}
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

function FileProcessingPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const { sharedFile, clearSharedFile } = useSharedFile();
  const greeting = getGreeting();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" | "info" } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ docId: string; name: string } | null>(null);

  // Active doc for viewing summary/Q&A
  const [activeDoc, setActiveDoc] = useState<any>(null);

  // Solve mode state
  const [solveResult, setSolveResult] = useState<any>(null);
  const [solving, setSolving] = useState(false);

  // Clear activeDoc when navigating away (useEffect cho navigation)
  useEffect(() => {
    return () => {
      // Cleanup khi component unmount (user navigate đi)
      if (activeDoc) {
        setActiveDoc(null);
      }
    };
  }, [activeDoc]);

  const loadData = () => {
    if (!user_id) return;
    apiClient.setUserId(user_id);
    setLoading(true);
    setError(false);
    documentService.getDocuments()
      .then(data => { setDocs(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  };

  useEffect(() => { loadData(); }, [user_id]);

  /* ─── Handle File Upload (from input) ─── */
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadFile(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCameraSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadFile(file, true); // true = isStudentMode (auto-generate quiz)
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const handleGallerySelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadFile(file, false);
    if (galleryInputRef.current) galleryInputRef.current.value = "";
  };

  /* ─── Upload File Logic ─── */
  const uploadFile = async (file: File, studentMode: boolean = false) => {
    const validExts = [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".webp"];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));
    if (!validExts.includes(ext)) {
      setToast({ message: "Chỉ hỗ trợ PDF, Word, hoặc Ảnh", type: "error" });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setToast({ message: "File quá lớn! Tối đa 10MB", type: "error" });
      return;
    }
    setUploading(true);
    setUploadProgress("AI đang đọc & phân tích...");
    try {
      const result = await documentService.uploadAndProcess(file);
      setToast({ message: "✅ Xử lý thành công!", type: "success" });
      setActiveDoc(result);
      // Nếu là student mode (chụp SGK), tự động chuyển sang tab quiz
      if (studentMode) {
        setTimeout(() => {
          navigate("/quiz");
        }, 1000);
      }
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || "Lỗi xử lý file", type: "error" });
    } finally {
      setUploading(false);
      setUploadProgress("");
    }
  };

  /* ─── Giải Bài Tập ─── */
  const solveProblem = async (file: File) => {
    const validExts = [".jpg", ".jpeg", ".png", ".webp"];
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf("."));
    if (!validExts.includes(ext)) {
      setToast({ message: "Chỉ hỗ trợ ảnh (JPG, PNG, WebP)", type: "error" });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setToast({ message: "File quá lớn! Tối đa 10MB", type: "error" });
      return;
    }
    setSolving(true);
    try {
      setUploadProgress("🔍 Đang nhận diện đề bài...");
      const result = await documentService.solveProblem(file);
      setSolveResult(result);
      setToast({ message: "✅ Đã giải xong!", type: "success" });
    } catch (err: any) {
      console.error("Solve error:", err);
      setToast({
        message: err.message || "Lỗi khi giải bài. Vui lòng thử lại.",
        type: "error"
      });
    } finally {
      setSolving(false);
      setUploadProgress("");
    }
  };

  /* ─── Handle Zalo Share Intent ─── */
  useEffect(() => {
    if (!sharedFile || !user_id) return;

    const processSharedFile = async () => {
      setUploading(true);
      setUploadProgress("📥 Đang nhận file từ Zalo...");
      try {
        // Download file từ Zalo file_url
        const response = await fetch(sharedFile.file_url);
        if (!response.ok) throw new Error("Không thể tải file từ Zalo");
        const blob = await response.blob();
        const fileName = sharedFile.file_name || `shared-file-${Date.now()}`;
        const file = new File([blob], fileName, { type: blob.type });
        await uploadFile(file);
      } catch (err: any) {
        setToast({ message: err.message || "Lỗi khi nhận file từ Zalo", type: "error" });
      } finally {
        setUploading(false);
        setUploadProgress("");
        clearSharedFile();
      }
    };

    processSharedFile();
  }, [sharedFile, user_id, clearSharedFile]);

  /* ─── Delete Document ─── */
  const handleDelete = async (docId: string) => {
    try {
      await documentService.deleteDocument(docId);
      setToast({ message: "🗑️ Đã xóa tài liệu", type: "success" });
      if (activeDoc?.id === docId) {
        setActiveDoc(null);
      }
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || "Lỗi khi xóa tài liệu", type: "error" });
    }
  };

  const [renameDoc, setRenameDoc] = useState<{ docId: string; currentName: string } | null>(null);
  const [newName, setNewName] = useState("");
  const [notifEnabled, setNotifEnabled] = useState(() => localStorage.getItem("ch_notif") === "1");
  const [showRanking, setShowRanking] = useState(false);
  const [showGroup, setShowGroup] = useState(false);
  const [showTeacher, setShowTeacher] = useState(false);
  const [groupMode, setGroupMode] = useState(false);
  const [teacherMode, setTeacherMode] = useState(false);
  const solveCameraRef = useRef<HTMLInputElement>(null);
  const solveGalleryRef = useRef<HTMLInputElement>(null);
  const [quizMode, setQuizMode] = useState(false);
  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<number[]>([]);
  const [quizScore, setQuizScore] = useState(0);

  const handleSolveCamera = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await solveProblem(file);
    if (solveCameraRef.current) solveCameraRef.current.value = "";
  };

  const handleSolveGallery = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await solveProblem(file);
    if (solveGalleryRef.current) solveGalleryRef.current.value = "";
  };

  const handleRename = async () => {
    if (!renameDoc || !newName.trim()) return;
    try {
      await documentService.renameDocument(renameDoc.docId, newName.trim());
      setToast({ message: "✏️ Đã đổi tên", type: "success" });
      setRenameDoc(null);
      setNewName("");
      loadData();
      if (activeDoc?.id === renameDoc.docId) {
        setActiveDoc({ ...activeDoc, name: newName.trim() });
      }
    } catch (err: any) {
      setToast({ message: err.message || "Lỗi khi đổi tên", type: "error" });
    }
  };

  return (
    <Page className="ch-page">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCameraSelect}
        style={{ display: "none" }}
      />
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        onChange={handleGallerySelect}
        style={{ display: "none" }}
      />
      <input
        ref={solveCameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleSolveCamera}
        style={{ display: "none" }}
      />
      <input
        ref={solveGalleryRef}
        type="file"
        accept="image/*"
        onChange={handleSolveGallery}
        style={{ display: "none" }}
      />

      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 18 }}>

        {/* ══════ HEADER ══════ */}
        <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Box onClick={() => navigate("/")} style={{
            width: 38, height: 38, borderRadius: "var(--radius-full)",
            background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
            display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
          }}><IconChevronLeft size={18} color="var(--color-text-secondary)" /></Box>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Box style={{
              width: 46, height: 46, borderRadius: 16,
              background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 6px 20px rgba(59,130,246,0.30)",
            }}><IconDoc size={22} color="white" /></Box>
            <Box>
              <Text style={{ fontSize: "var(--font-size-xl)", fontWeight: 900, color: "var(--color-text-primary)", letterSpacing: "-0.02em" }}>
                Trợ Lý AI</Text>
              <Box style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                <Box style={{
                  padding: "4px 10px", borderRadius: "var(--radius-full)",
                  background: "linear-gradient(135deg, #F59E0B, #FBBF24)",
                  color: "white", fontSize: 10, fontWeight: 800,
                }}>📚 DÀNH CHO HỌC SINH</Box>
                <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", fontWeight: 500 }}>
                  {greeting.emoji} {greeting.text}
                </Text>
              </Box>
            </Box>
            {/* Toggle thông báo + Xếp hạng + Group + Teacher */}
            <Box style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
              <Box
                onClick={() => { setShowRanking(!showRanking); }}
                style={{
                  width: 38, height: 38, borderRadius: "var(--radius-full)",
                  background: showRanking ? "linear-gradient(135deg, #F59E0B, #FBBF24)" : "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                  display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
                  transition: "all 0.3s",
                }}
                title="Bảng xếp hạng tuần"
              >🏆</Box>
              <Box
                onClick={() => { setShowGroup(!showGroup); setGroupMode(!groupMode); }}
                style={{
                  width: 38, height: 38, borderRadius: "var(--radius-full)",
                  background: showGroup ? "linear-gradient(135deg, #8B5CF6, #6D28D9)" : "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                  display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
                  transition: "all 0.3s",
                }}
                title="Nhóm học tập"
              >👥</Box>
              <Box
                onClick={() => { setShowTeacher(!showTeacher); setTeacherMode(!teacherMode); }}
                style={{
                  width: 38, height: 38, borderRadius: "var(--radius-full)",
                  background: showTeacher ? "linear-gradient(135deg, #EF4444, #DC2626)" : "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                  display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
                  transition: "all 0.3s",
                }}
                title="Chế độ Giáo viên"
              >👩‍🏫</Box>
              <Box
                onClick={() => {
                  const next = !notifEnabled;
                  setNotifEnabled(next);
                  localStorage.setItem("ch_notif", next ? "1" : "0");
                  setToast({ message: next ? "🔔 Đã bật nhắc ôn bài" : "🔕 Đã tắt nhắc ôn bài", type: next ? "success" : "info" });
                }}
                style={{
                  width: 38, height: 38, borderRadius: "var(--radius-full)",
                  background: notifEnabled ? "linear-gradient(135deg, #10B981, #34D399)" : "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                  display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
                  transition: "all 0.3s",
                }}
                title={notifEnabled ? "Đang bật nhắc ôn bài" : "Tắt nhắc ôn bài"}
              >{notifEnabled ? "🔔" : "🔕"}</Box>
            </Box>
          </Box>
        </Box>

        {/* ══════ QUICK ACTIONS: CAMERA & ALBUM ══════ */}
        <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Box
            className="ch-btn-primary"
            onClick={() => cameraInputRef.current?.click()}
            style={{ padding: "14px", justifyContent: "center", flexDirection: "column", gap: 4 }}
          >
            <IconCamera size={24} color="white" />
            <Text style={{ fontSize: 12, fontWeight: 700 }}>📸 Chụp ảnh</Text>
          </Box>
          <Box
            className="ch-btn-secondary"
            onClick={() => galleryInputRef.current?.click()}
            style={{ padding: "14px", justifyContent: "center", flexDirection: "column", gap: 4 }}
          >
            <IconImage size={24} color="var(--color-primary)" />
            <Text style={{ fontSize: 12, fontWeight: 700 }}>🖼️ Chọn ảnh</Text>
          </Box>
        </Box>

        {/* ═════ Giải Bài Tập ═════ */}
        <Box style={{
          padding: "16px", borderRadius: "var(--radius-xl)",
          background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
          border: "2px solid #F59E0B",
          cursor: "pointer",
          display: "flex", alignItems: "center", gap: 14,
          boxShadow: "0 8px 24px rgba(245,158,11,0.25)",
          transition: "all 0.2s",
        }}
          onClick={() => solveCameraRef.current?.click()}
        >
          <Box style={{
            width: 52, height: 52, borderRadius: "var(--radius-md)",
            background: "white", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(0,0,0,0.10)",
          }}>
            <Text style={{ fontSize: 28 }}>📝</Text>
          </Box>
          <Box style={{ flex: 1 }}>
            <Text style={{ fontSize: 15, fontWeight: 800, color: "#92400E", marginBottom: 4 }}>
              ✨ Giải bài tập AI
            </Text>
            <Text style={{ fontSize: 12, color: "#B45309", lineHeight: 1.4 }}>
              Chụp ảnh bài tập → AI giải từng bước, giải thích "tại sao"
            </Text>
          </Box>
          <Box style={{
            padding: "6px 12px", borderRadius: "var(--radius-full)",
            background: "#F59E0B", color: "white",
            fontSize: 11, fontWeight: 800,
          }}>
            MỚI
          </Box>
        </Box>

        {/* ═══ SOLVE RESULT PANEL ═══ */}
        {solveResult && (
          <Box style={{
            padding: 20, borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #F0FDF4, #DCFCE7)",
            border: "2px solid #10B981",
            animation: "slideIn 0.3s ease-out",
          }}>
            <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#047857" }}>
                ✅ Kết quả giải bài
              </Text>
              <Box onClick={() => setSolveResult(null)} style={{ cursor: "pointer", fontSize: 20 }}>✕</Box>
            </Box>

            <Text style={{ fontSize: 16, fontWeight: 800, color: "#064E3B", marginBottom: 12 }}>
              📝 {solveResult.question}
            </Text>

            <Box style={{
              padding: "14px", marginBottom: 12,
              borderRadius: "var(--radius-lg)", background: "white",
              border: "1px solid #10B981",
            }}>
              <Text style={{ fontWeight: 700, color: "#047857", marginBottom: 8, display: "block" }}>
                📋 Lời giải chi tiết:
              </Text>
              {solveResult.steps.map((step: string, i: number) => (
                <Text key={i} style={{ fontSize: 13, color: "#064E3B", lineHeight: 1.6, display: "block", marginBottom: 6 }}>
                  {i + 1}. {step}
                </Text>
              ))}
            </Box>

            <Box style={{
              padding: "12px 16px", borderRadius: "var(--radius-lg)",
              background: "linear-gradient(135deg, #10B981, #34D399)",
              color: "white", textAlign: "center",
            }}>
              <Text style={{ fontSize: 16, fontWeight: 900 }}>
                🎯 Đáp án: {solveResult.answer}
              </Text>
            </Box>

            <Box style={{
              marginTop: 12, padding: "10px 14px",
              borderRadius: "var(--radius-lg)", background: "rgba(255,255,255,0.8)",
            }}>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "#047857", fontWeight: 600 }}>
                💡 Chưa hiểu? Hỏi AI ngay bên dưới để được giải thích thêm!
              </Text>
            </Box>
          </Box>
        )}

        {/* ═════ WEEKLY RANKING ═════ */}
        {showRanking && (
          <Box style={{
            padding: 20, borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
            border: "2px solid #F59E0B",
            animation: "slideIn 0.3s ease-out",
          }}>
            <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#92400E" }}>
                🏆 Bảng Xếp Hạng Tuần
              </Text>
              <Box onClick={() => setShowRanking(false)} style={{ cursor: "pointer", fontSize: 20 }}>✕</Box>
            </Box>

            {/* Top 3 users mockup - replace with API later */}
            {[
              { rank: 1, name: "Nguyễn Văn A", streak: 7, coins: 1200, avatar: "🥇" },
              { rank: 2, name: "Trần Thị B", streak: 5, coins: 980, avatar: "🥈" },
              { rank: 3, name: "Lê Văn C", streak: 4, coins: 850, avatar: "🥉" },
            ].map((u, i) => (
              <Box key={i} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 16px", marginBottom: 8,
                borderRadius: "var(--radius-lg)",
                background: i === 0 ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.6)",
                border: i === 0 ? "2px solid #F59E0B" : "1px solid rgba(0,0,0,0.05)",
              }}>
                <Text style={{ fontSize: 24 }}>{u.avatar}</Text>
                <Box style={{ flex: 1 }}>
                  <Text style={{ fontWeight: 700, color: "#92400E" }}>{u.name}</Text>
                  <Text style={{ fontSize: "var(--font-size-xs)", color: "#B45309" }}>
                    🔥 {u.streak} ngày | 🪙 {u.coins} coins
                  </Text>
                </Box>
                <Box style={{
                  width: 32, height: 32, borderRadius: "var(--radius-full)",
                  background: "linear-gradient(135deg, #F59E0B, #D97706)",
                  color: "white", fontWeight: 900, fontSize: 14,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>#{u.rank}</Box>
              </Box>
            ))}

            <Box style={{
              marginTop: 12, padding: "12px 16px",
              borderRadius: "var(--radius-lg)",
              background: "rgba(255,255,255,0.8)",
              border: "1px dashed #F59E0B",
            }}>
              <Text style={{ fontSize: "var(--font-size-sm)", color: "#92400E", fontWeight: 600 }}>
                💡 Ôn bài mỗi ngày để thăng hạng! Top 3 nhận thưởng Coin tuần tới.
              </Text>
            </Box>
          </Box>
        )}


        {/* ═══ GROUP STUDY PANEL ═══ */}
        {showGroup && (
          <Box style={{
            padding: 20, borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #EDE9FE, #DDD6FE)",
            border: "2px solid #8B5CF6",
            animation: "slideIn 0.3s ease-out",
          }}>
            <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#5B21B6" }}>
                👥 Nhóm Học Tập
              </Text>
              <Box onClick={() => setShowGroup(false)} style={{ cursor: "pointer", fontSize: 20 }}>✕</Box>
            </Box>
            <Box style={{
              padding: "14px 16px", marginBottom: 12,
              borderRadius: "var(--radius-lg)", background: "white",
              border: "2px dashed #8B5CF6", cursor: "pointer",
            }}
              onClick={() => {
                const name = prompt("Tên nhóm:");
                if (name) setToast({ message: `✅ Đã tạo nhóm ${name}`, type: "success" });
              }}
            >
              <Text style={{ fontWeight: 700, color: "#5B21B6", textAlign: "center" }}>
                ➕ Tạo nhóm mới
              </Text>
            </Box>
            {[{name:"Ôn thi THPT",members:8,active:true},{name:"Tiếng Anh",members:5,active:false}].map((g,i) => (
              <Box key={i} style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 16px", marginBottom: 8,
                borderRadius: "var(--radius-lg)", background: "white",
                border: g.active ? "2px solid #8B5CF6" : "1px solid rgba(0,0,0,0.05)",
              }}>
                <Text style={{ fontSize: 24 }}>📚</Text>
                <Box style={{ flex: 1 }}>
                  <Text style={{ fontWeight: 700, color: "#5B21B6" }}>{g.name}</Text>
                  <Text style={{ fontSize: "var(--font-size-xs)", color: "#7C3AED" }}>
                    👥 {g.members} thành viên
                  </Text>
                </Box>
                <Box style={{
                  padding: "6px 12px", borderRadius: "var(--radius-full)",
                  background: g.active ? "#8B5CF6" : "var(--color-bg-subtle)",
                  color: g.active ? "white" : "var(--color-text-secondary)",
                  fontSize: 12, fontWeight: 600, cursor: "pointer",
                }}>
                  {g.active ? "Đang học" : "Vào nhóm"}
                </Box>
              </Box>
            ))}
          </Box>
        )}

        {/* ═══ TEACHER PANEL ═══ */}
        {showTeacher && (
          <Box style={{
            padding: 20, borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #FEE2E2, #FECACA)",
            border: "2px solid #EF4444",
            animation: "slideIn 0.3s ease-out",
          }}>
            <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#991B1B" }}>
                👩‍🏫 Chế Độ Giáo Viên
              </Text>
              <Box onClick={() => setShowTeacher(false)} style={{ cursor: "pointer", fontSize: 20 }}>✕</Box>
            </Box>
            <Box style={{
              padding: 16, marginBottom: 12,
              borderRadius: "var(--radius-lg)", background: "white",
              border: "1px solid #EF4444", cursor: "pointer",
            }}
              onClick={() => {
                if (!documents.length) { setToast({ message: "❌ Cần tài liệu", type: "error" }); return; }
                setToast({ message: "📝 Đang tạo đề thi...", type: "info" });
              }}
            >
              <Text style={{ fontWeight: 800, color: "#991B1B", marginBottom: 6 }}>
                📝 Tạo đề thi từ tài liệu
              </Text>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "#DC2626" }}>
                AI tự động ra 20 câu trắc nghiệm
              </Text>
            </Box>
            <Box style={{
              padding: 16, marginBottom: 12,
              borderRadius: "var(--radius-lg)", background: "white",
              border: "1px solid #EF4444", cursor: "pointer",
            }}
              onClick={() => {
                const c = prompt("Tên lớp:");
                if (c) setToast({ message: `📤 Đã gửi bài cho ${c}!`, type: "success" });
              }}
            >
              <Text style={{ fontWeight: 800, color: "#991B1B", marginBottom: 6 }}>
                📤 Giao bài tập (Zalo)
              </Text>
              <Text style={{ fontSize: "var(--font-size-xs)", color: "#DC2626" }}>
                Gửi link cho cả lớp qua Zalo
              </Text>
            </Box>
            <Box style={{
              padding: 16, marginBottom: 12,
              borderRadius: "var(--radius-lg)", background: "white",
              border: "1px solid #EF4444",
            }}>
              <Text style={{ fontWeight: 800, color: "#991B1B", marginBottom: 6 }}>
                📊 Thống kê lớp học
              </Text>
              <Box style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {[{label:"HS làm bài",value:"32/40",color:"#10B981"},{label:"Điểm TB",value:"7.8",color:"#3B82F6"},{label:"Chưa làm",value:"8",color:"#EF4444"}].map((s,i) => (
                  <Box key={i} style={{
                    padding: "8px 12px", borderRadius: "var(--radius-md)",
                    background: `${s.color}15`, border: `1px solid ${s.color}30`,
                  }}>
                    <Text style={{ fontSize: 18, fontWeight: 900, color: s.color }}>{s.value}</Text>
                    <Text style={{ fontSize: 10, color: s.color, fontWeight: 600 }}>{s.label}</Text>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        )}

        {/* ═════ STUDENT HACK: CHỤP SGK → QUIZ ═════ */}
        <Box
          onClick={() => cameraInputRef.current?.click()}
          style={{
            padding: "18px",
            borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
            border: "2px solid #F59E0B",
            cursor: "pointer",
            display: "flex", alignItems: "center", gap: 14,
            boxShadow: "0 8px 24px rgba(245,158,11,0.25)",
            transition: "all 0.2s",
          }}
        >
          <Box style={{
            width: 52, height: 52, borderRadius: "var(--radius-md)",
            background: "white", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(0,0,0,0.10)",
          }}>
            <IconCamera size={28} color="#F59E0B" />
          </Box>
          <Box style={{ flex: 1 }}>
            <Text style={{ fontSize: 15, fontWeight: 800, color: "#92400E", marginBottom: 4 }}>
              📚 Chụp SGK → Quiz ngay!
            </Text>
            <Text style={{ fontSize: 12, color: "#B45309", lineHeight: 1.4 }}>
              Chụp 1 trang sách → AI tạo 5 câu hỏi trong 15 giây
            </Text>
          </Box>
          <Box style={{
            padding: "6px 12px", borderRadius: "var(--radius-full)",
            background: "#F59E0B", color: "white",
            fontSize: 11, fontWeight: 800,
          }}>
            HỌC SINH
          </Box>
        </Box>

        {error ? (
          <Box className="ch-error">
            <Box className="ch-error-icon"><IconAlertTriangle size={24} color="#EF4444" /></Box>
            <Text className="ch-error-title">Không thể tải dữ liệu</Text>
            <button className="ch-retry-btn" onClick={loadData}><IconRefresh size={16} /> Thử lại</button>
          </Box>
        ) : (
          <>
            {/* ══════ UPLOAD ZONE ══════ */}
            <Box className="ch-card" style={{
              padding: 28, textAlign: "center",
              border: uploading ? "2px solid #8B5CF6" : "2px dashed #3B82F6",
              borderRadius: "var(--radius-xl)",
              background: uploading ? "linear-gradient(135deg,#F3E8FF,#EDE9FE)" : "linear-gradient(135deg,#EFF6FF,#DBEAFE)",
              cursor: uploading ? "wait" : "pointer",
            }} onClick={() => !uploading && fileInputRef.current?.click()}>
              {uploading ? (
                <>
                  <Box style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid #E9D5FF",
                    borderTopColor: "#8B5CF6", animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
                  <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "#7C3AED" }}>{uploadProgress}</Text>
                  <Text className="ch-caption">Tóm tắt + Flashcard + Quiz trong 30 giây</Text>
                </>
              ) : (
                <>
                  <Box style={{ width: 56, height: 56, borderRadius: "var(--radius-full)",
                    background: "linear-gradient(135deg,#3B82F6,#6366F1)", display: "flex",
                    alignItems: "center", justifyContent: "center", margin: "0 auto 14px",
                    boxShadow: "0 8px 24px rgba(59,130,246,0.30)" }}>
                    <IconUpload size={28} color="white" />
                  </Box>
                  <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#1D4ED8", marginBottom: 4 }}>
                    Tải lên & AI xử lý ngay</Text>
                  <Text style={{ fontSize: 13, color: "var(--color-text-tertiary)", lineHeight: 1.5 }}>
                    PDF, Word, Ảnh → Tóm tắt + Flashcard + Quiz trong 30 giây</Text>
                  <Box style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12 }}>
                    {["PDF", "Word", "Ảnh"].map(t => (
                      <Box key={t} style={{ padding: "4px 12px", borderRadius: "var(--radius-full)",
                        background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)",
                        fontSize: 12, fontWeight: 700, color: "#3B82F6" }}>{t}</Box>
                    ))}
                  </Box>
                </>
              )}
            </Box>

            {/* ══════ ACTIVE DOC — UNIFIED SUMMARY + Q&A ══════ */}
            {activeDoc && (
              <Box className="ch-card" style={{ padding: 0, overflow: "hidden" }}>
                {/* Header */}
                <Box style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "14px 18px",
                  background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)",
                  borderBottom: "1px solid rgba(99,102,241,0.12)",
                }}>
                  <Box style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                    <IconDoc size={18} color="#6366F1" />
                    <Text style={{
                      fontSize: 14, fontWeight: 800, color: "#4338CA",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {activeDoc.name}
                    </Text>
                  </Box>
                  <Box
                    onClick={() => setActiveDoc(null)}
                    style={{
                      width: 28, height: 28, borderRadius: 8, cursor: "pointer",
                      background: "rgba(99,102,241,0.1)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 14, color: "#6366F1", fontWeight: 800,
                    }}
                  >✕</Box>
                </Box>
                {/* Unified Content */}
                <Box style={{ padding: "18px 18px 14px", height: 560, display: "flex", flexDirection: "column" }}>
                  <SummaryWithQA doc={activeDoc} />
                </Box>
              </Box>
            )}

            {/* ══════ DOCUMENT LIST ══════ */}
            <Box>
              <Text className="ch-section-title" style={{ marginBottom: 12 }}>Kết quả xử lý gần nhất</Text>
              {loading ? (
                <Box style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {[1, 2].map(i => <Skeleton key={i} w="100%" h={80} r={16} />)}
                </Box>
              ) : docs.length === 0 ? (
                <Box style={{ textAlign: "center", padding: 24 }}>
                  <IconInbox size={32} color="#9E9BB8" />
                  <Text className="ch-caption" style={{ marginTop: 8 }}>Chưa có tài liệu — tải lên file đầu tiên!</Text>
                </Box>
              ) : (
                <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {docs.map((doc, idx) => {
                    const isP = doc.doc_type === "pdf";
                    const isW = doc.doc_type === "word" || doc.doc_type === "docx";
                    const bgColor = isP ? "#FEE2E2" : isW ? "#DBEAFE" : "#FEF3C7";
                    const iconColor = isP ? "#EF4444" : isW ? "#3B82F6" : "#F59E0B";
                    const isActive = activeDoc?.id === doc.id;
                    return (
                      <Box key={doc.id || idx} className="ch-card" style={{
                        padding: 14, cursor: "pointer",
                        border: isActive ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                      }} onClick={() => setActiveDoc(isActive ? null : doc)}>
                        <Box style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                          <Box className="ch-doc-icon" style={{ background: bgColor }}>
                            <IconDoc size={20} color={iconColor} />
                          </Box>
                          <Box style={{ flex: 1, minWidth: 0 }}>
                            <Text style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)",
                              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {doc.name}</Text>
                            <Text className="ch-caption">{
                              new Date(doc.timestamp * 1000).toLocaleDateString("vi-VN")
                            }</Text>
                          </Box>
                          {/* Edit button */}
                          <Box
                            onClick={(e) => { e.stopPropagation(); setRenameDoc({ docId: doc.id, currentName: doc.name }); }}
                            style={{
                              width: 32, height: 32, borderRadius: 8, cursor: "pointer",
                              background: "rgba(0,0,0,0.04)", display: "flex", alignItems: "center", justifyContent: "center",
                            }}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </Box>
                        </Box>
                        {/* Quick actions */}
                        <Box style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                          {[
                            { label: "Tóm tắt", icon: <IconDoc size={20} color="#3B82F6" />, bg: "#EFF6FF",
                              action: () => { setActiveDoc(doc); } },
                            { label: "Flashcard", icon: <IconFlashcard size={20} color="#F59E0B" />, bg: "#FEF3C7",
                              action: () => navigate("/flashcard") },
                            { label: "Quiz", icon: <IconQuiz size={20} color="#8B5CF6" />, bg: "#F3E8FF",
                              action: () => navigate("/quiz") },
                            { label: "Kho", icon: <IconFolder size={20} color="#22C55E" />, bg: "#DCFCE7",
                              action: () => navigate("/vault") },
                          ].map((a, i) => (
                            <Box key={i} onClick={(e) => { e.stopPropagation(); a.action(); }} style={{
                              textAlign: "center", padding: "12px 8px", borderRadius: "var(--radius-lg)",
                              background: a.bg, cursor: "pointer", transition: "all 0.2s",
                              minHeight: 70, display: "flex", flexDirection: "column", justifyContent: "center",
                              alignItems: "center",
                            }}>
                              <Box style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>{a.icon}</Box>
                              <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-secondary)" }}>{a.label}</Text>
                            </Box>
                          ))}
                          {/* Delete button */}
                          <Box
                            key="delete"
                            onClick={(e) => { e.stopPropagation(); setDeleteConfirm({ docId: doc.id, name: doc.name }); }}
                            style={{
                              textAlign: "center", padding: "12px 8px", borderRadius: "var(--radius-lg)",
                              background: "#FEE2E2", cursor: "pointer", transition: "all 0.2s",
                              minHeight: 70, display: "flex", flexDirection: "column", justifyContent: "center",
                              alignItems: "center",
                            }}
                          >
                            <Box style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                            </Box>
                            <Text style={{ fontSize: 12, fontWeight: 700, color: "#EF4444" }}>Xóa</Text>
                          </Box>
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </Box>

            {/* ══════ Q&A TIP ══════ */}
            <Box style={{
              padding: "16px 18px", borderRadius: "var(--radius-xl)",
              background: "var(--color-primary-lighter)",
              border: "1px solid rgba(91,76,219,0.12)",
              display: "flex", alignItems: "flex-start", gap: 12,
            }}>
              <IconSearch size={20} color="#5B4CDB" style={{ flexShrink: 0, marginTop: 2 }} />
              <Box>
                <Text style={{ fontSize: 13, fontWeight: 700, color: "var(--color-primary-dark)", marginBottom: 4 }}>
                  Mẹo: Hỏi đáp Q&A</Text>
                <Text style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                  Bấm vào tài liệu → chuyển tab "Hỏi đáp Q&A" để hỏi bất kỳ câu gì. AI sẽ tìm câu trả lời chính xác từ nội dung file!</Text>
              </Box>
            </Box>
          </>
        )}
      </Box>

      {/* ── Delete Confirmation Modal ── */}
      {deleteConfirm && (
        <Box style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 9999, padding: 20,
        }}>
          <Box style={{
            width: "100%", maxWidth: 320,
            background: "white", borderRadius: "var(--radius-xl)",
            padding: "24px", boxShadow: "var(--shadow-xl)",
            animation: "scaleIn 0.2s var(--ease-spring)",
          }}>
            <Text style={{ fontSize: 18, fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 8 }}>
              Xóa tài liệu?
            </Text>
            <Text style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.6, marginBottom: 20 }}>
              Bạn có chắc muốn xóa "<Text style={{ fontWeight: 700 }}>{deleteConfirm.name}</Text>"? Hành động này không thể hoàn tác.
            </Text>
            <Box style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => setDeleteConfirm(null)}
                style={{
                  flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                  background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
                  color: "var(--color-text-secondary)", fontWeight: 700, fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Hủy
              </button>
              <button
                onClick={() => { handleDelete(deleteConfirm.docId); setDeleteConfirm(null); }}
                style={{
                  flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                  background: "#EF4444", border: "none",
                  color: "white", fontWeight: 700, fontSize: 14,
                  cursor: "pointer", boxShadow: "0 4px 12px rgba(239,68,68,0.3)",
                }}
              >
                Xóa
              </button>
            </Box>
          </Box>
        </Box>
      )}
    </Page>
  );
}

export default FileProcessingPage;

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
import SummaryPanel from "../components/SummaryPanel";
import QAChatSection from "../components/QAChatSection";
import DocumentList from "../components/DocumentList";

declare global {
  interface Window {
    ZMP?: any;
  }
}

/* ─── Skeleton ─── */
function Skeleton({ w = "100%", h = 20, r = 10, style }: { w?: string | number; h?: number; r?: number; style?: React.CSSProperties }) {
  return <Box className="ch-skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

/* ─── Toast ─── */
function Toast({ message, type, onClose }: { message: string; type: "error" | "success" | "info"; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 4000); return () => clearTimeout(t); }, [onClose]);
  return <Box className={`ch-toast ch-toast--${type}`}>{message}</Box>;
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

  const [solving, setSolving] = useState(false);
  const [shareStatus, setShareStatus] = useState<"idle" | "downloading" | "uploading" | "success" | "error">("idle");
  const [shareError, setShareError] = useState<string | null>(null);
  const [pastedImage, setPastedImage] = useState<string | null>(null);

  // Handle paste image from clipboard
  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let item of items) {
      if (item.type.indexOf("image") !== -1) {
        const file = item.getAsFile();
        if (file) {
          const url = URL.createObjectURL(file);
          setPastedImage(url);
          // Auto upload after 800ms
          setTimeout(async () => {
            await uploadFile(file, true);
            setPastedImage(null);
          }, 800);
        }
        break;
      }
    }
  };

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

  /* ─── Process Zalo Shared File (useCallback) ─── */
  const processSharedFile = useCallback(async () => {
    // Prevent duplicate processing
    if (shareStatus === "downloading" || shareStatus === "uploading") return;

    setShareStatus("downloading");
    setShareError(null);
    setUploadProgress("📥 Đang nhận file từ Zalo...");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

    try {
      // Validate file size if provided (Zalo may send file_size in bytes)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (sharedFile.file_size && sharedFile.file_size > maxSize) {
        throw new Error(`File quá lớn (${(sharedFile.file_size / 1024 / 1024).toFixed(1)}MB). Tối đa 10MB.`);
      }

      // Validate mime type if provided
      const allowedTypes = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/jpeg", "image/png", "image/webp"];
      if (sharedFile.mime_type && !allowedTypes.includes(sharedFile.mime_type)) {
        throw new Error(`Loại file không được hỗ trợ: ${sharedFile.mime_type}`);
      }

      // Download file with timeout
      const response = await fetch(sharedFile.file_url, {
        signal: controller.signal,
        headers: { 'Cache-Control': 'no-cache' },
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(`Không thể tải file từ Zalo (HTTP ${response.status}): ${errorText.substring(0, 100)}`);
      }

      const blob = await response.blob();

      // Validate blob size
      if (blob.size > maxSize) {
        throw new Error(`File quá lớn (${(blob.size / 1024 / 1024).toFixed(1)}MB). Tối đa 10MB.`);
      }

      // Validate blob type
      if (sharedFile.mime_type && !blob.type.includes(sharedFile.mime_type.split('/')[0])) {
        console.warn(`MIME type mismatch: expected ${sharedFile.mime_type}, got ${blob.type}`);
      }

      const fileName = sharedFile.file_name || `shared-file-${Date.now()}`;
      const file = new File([blob], fileName, { type: blob.type || sharedFile.mime_type || 'application/octet-stream' });

      setShareStatus("uploading");
      setUploadProgress("📤 Đang xử lý và phân tích...");

      await uploadFile(file);

      setShareStatus("success");
      setToast({ message: "✅ Đã nhận và xử lý file từ Zalo!", type: "success" });
      clearSharedFile(); // Only clear on success

    } catch (err: any) {
      // Handle abort error separately
      if (err.name === 'AbortError') {
        setShareError("Quá thời gian tải file. Vui lòng thử lại.");
      } else {
        setShareError(err.message || "Lỗi khi nhận file từ Zalo");
      }
      setShareStatus("error");
      setToast({ message: `❌ ${err.message || "Lỗi khi nhận file từ Zalo"}`, type: "error" });
      // Don't clear sharedFile on error so user can retry
    } finally {
      clearTimeout(timeoutId);
      if (shareStatus === "success") {
        // Only reset uploading state, keep success briefly for user to see
        setTimeout(() => {
          setUploading(false);
          setUploadProgress("");
        }, 1000);
      } else {
        setUploading(false);
        setUploadProgress("");
      }
    }
  }, [sharedFile, user_id, clearSharedFile, shareStatus, uploadFile, setToast]);

  /* ─── Handle Zalo Share Intent ─── */
  useEffect(() => {
    if (!sharedFile || !user_id) return;
    processSharedFile();
  }, [sharedFile, user_id, processSharedFile]);

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

      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 18 }} onPaste={handlePaste} tabIndex={0}>

        {/* Paste Image Preview Overlay */}
        {pastedImage && (
          <Box style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            background: "rgba(0,0,0,0.8)", zIndex: 9999,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          }}>
            <Box style={{ textAlign: "center", color: "white", marginBottom: 16 }}>
              <Text style={{ fontSize: 64 }}>🖼️</Text>
              <Text style={{ fontSize: 18, fontWeight: 700 }}>Đang xử lý ảnh...</Text>
            </Box>
            <img src={pastedImage} alt="Pasted" style={{ maxWidth: "80%", maxHeight: "60vh", borderRadius: 16 }} />
          </Box>
        )}

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
                if (!docs.length) { setToast({ message: "❌ Cần tài liệu", type: "error" }); return; }
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
              border: shareStatus === "error" ? "2px solid #EF4444" :
                      uploading ? "2px solid #8B5CF6" : "2px dashed #3B82F6",
              borderRadius: "var(--radius-xl)",
              background: shareStatus === "error" ? "linear-gradient(135deg,#FEF2F2,#FEE2E2)" :
                          uploading ? "linear-gradient(135deg,#F3E8FF,#EDE9FE)" : "linear-gradient(135deg,#EFF6FF,#DBEAFE)",
              cursor: uploading ? "wait" : "pointer",
            }} onClick={() => {
              if (!uploading && shareStatus !== "error") {
                fileInputRef.current?.click();
              } else if (shareStatus === "error" && sharedFile) {
                // Retry processing the shared file
                processSharedFile();
              }
            }}>
              {uploading ? (
                <>
                  <Box style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid #E9D5FF",
                    borderTopColor: "#8B5CF6", animation: "spin 1s linear infinite", margin: "0 auto 12px" }} />
                  <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "#7C3AED" }}>{uploadProgress}</Text>
                  <Text className="ch-caption">Tóm tắt + Flashcard + Quiz trong 30 giây</Text>
                </>
              ) : shareStatus === "error" && shareError ? (
                <>
                  <Box style={{ width: 56, height: 56, borderRadius: "var(--radius-full)",
                    background: "linear-gradient(135deg,#EF4444,#DC2626)", display: "flex",
                    alignItems: "center", justifyContent: "center", margin: "0 auto 14px",
                    boxShadow: "0 8px 24px rgba(239,68,68,0.30)" }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  </Box>
                  <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "#DC2626", marginBottom: 8 }}>
                    ❌ Không thể nhận file
                  </Text>
                  <Text className="ch-caption" style={{ color: "#991B1B", marginBottom: 12 }}>
                    {shareError}
                  </Text>
                  <Box className="ch-btn-primary" style={{ margin: "0 auto", width: "fit-content", padding: "10px 24px" }}>
                    <Text>🔄 Thử lại</Text>
                  </Box>
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

            {/* ══════ ACTIVE DOC — SUMMARY + CHAT ══════ */}
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
                {/* Content */}
                <Box style={{ padding: "18px 18px 14px", height: 560, display: "flex", flexDirection: "column" }}>
                  <SummaryPanel doc={activeDoc} setToast={setToast} />
                  <Box style={{ flex: 1, marginTop: 16 }}>
                    <QAChatSection docId={activeDoc.id} setToast={setToast} />
                  </Box>
                </Box>
              </Box>
            )}

            <DocumentList
              docs={docs}
              loading={loading}
              activeDoc={activeDoc}
              setActiveDoc={setActiveDoc}
              setRenameDoc={setRenameDoc}
              setDeleteConfirm={setDeleteConfirm}
              navigate={navigate}
            />

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
    </Page>
  );
}

export default FileProcessingPage;

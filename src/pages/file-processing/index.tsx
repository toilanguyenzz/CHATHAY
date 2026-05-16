/* ─── File Processing Page - Refactored ─── */
import { Box, Page, Text, useNavigate } from "zmp-ui";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { documentService } from "../services/documentService";
import { apiClient } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { getGreeting } from "../utils/greeting";
import { useSharedFile } from "../contexts/SharedFileContext";

// Components (lazy load sau này, bây giờ import straight)
import { FileUploadSection } from "./FileUploadSection";
import { DocumentList } from "./DocumentList";
import { SummaryPanel } from "./SummaryPanel";
import { QAPanel } from "./QAPanel";
import { SolveResultPanel } from "./SolveResultPanel";

// Simple in-memory cache for processed files
const fileCache = new Map<string, any>();

// Generate file hash for caching
async function generateFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Compress image before upload
async function compressImage(file: File, maxWidth = 1024, maxHeight = 1024, quality = 0.8): Promise<File> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      let { width, height } = img;

      if (width > maxWidth || height > maxHeight) {
        if (width / maxWidth > height / maxHeight) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        } else {
          width = (width * maxHeight) / height;
          height = maxHeight;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(new File([blob], file.name, { type: "image/jpeg" }));
          } else {
            resolve(file);
          }
        },
        "image/jpeg",
        quality
      );
    };
    img.src = URL.createObjectURL(file);
  });
}

// 🔒 DEMO MODE: Lock features except Quiz & Flashcard
const DEMO_MODE = true;

function FileProcessingPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const { sharedFile, clearSharedFile } = useSharedFile();
  const greeting = getGreeting();
  const [showLockModal, setShowLockModal] = useState(false);

  const lockFeature = (featureName: string) => {
    if (DEMO_MODE) {
      setShowLockModal(true);
      return true;
    }
    return false;
  };

  const [docs, setDocs] = useState<any[]>([]);
  const [publicExams, setPublicExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" | "info" } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ docId: string; name: string } | null>(null);
  const [activeDoc, setActiveDoc] = useState<any>(null);
  const [solveResult, setSolveResult] = useState<any>(null);
  const [solving, setSolving] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const solveCameraRef = useRef<HTMLInputElement>(null);
  const solveGalleryRef = useRef<HTMLInputElement>(null);

  const loadData = useCallback(() => {
    if (!user_id) return;
    apiClient.setUserId(user_id);
    setLoading(true);
    setError(false);

    // Load user docs
    documentService
      .getDocuments()
      .then((data) => {
        setDocs(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });

    // Load public exams library
    documentService.getPublicExams()
      .then((data) => setPublicExams(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [user_id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Zalo Share Intent with caching
  useEffect(() => {
    if (!sharedFile || !user_id) return;

    const processSharedFile = async () => {
      setUploading(true);
      setUploadProgress("📥 Đang nhận file từ Zalo...");

      try {
        // Check cache first
        const cacheKey = `zalo_${sharedFile.file_url}`;
        if (fileCache.has(cacheKey)) {
          const cached = fileCache.get(cacheKey);
          setActiveDoc(cached);
          setUploadProgress("✅ Lấy từ cache!");
          setTimeout(() => {
            setUploading(false);
            setUploadProgress("");
            clearSharedFile();
          }, 500);
          return;
        }

        // Download with retry
        let response: Response | null = null;
        for (let i = 0; i < 3; i++) {
          try {
            response = await fetch(sharedFile.file_url);
            if (response.ok) break;
          } catch (e) {
            if (i === 2) throw e;
            await new Promise((r) => setTimeout(r, 1000 * (i + 1)));
          }
        }

        if (!response || !response.ok) throw new Error("Không thể tải file từ Zalo");

        const blob = await response.blob();
        const fileName = sharedFile.file_name || `shared-file-${Date.now()}`;
        const file = new File([blob], fileName, { type: blob.type });

        // Upload and process
        setUploadProgress("⚙️ AI đang xử lý...");
        const result = await documentService.uploadAndProcess(file);

        // Cache result
        fileCache.set(cacheKey, result);
        if (fileCache.size > 100) {
          // LRU: keep cache size manageable
          const firstKey = fileCache.keys().next().value;
          fileCache.delete(firstKey);
        }

        setActiveDoc(result);
        setToast({ message: "✅ Xử lý thành công!", type: "success" });
        loadData();
      } catch (err: any) {
        setToast({ message: err.message || "Lỗi khi nhận file từ Zalo", type: "error" });
      } finally {
        setUploading(false);
        setUploadProgress("");
        clearSharedFile();
      }
    };

    processSharedFile();
  }, [sharedFile, user_id, clearSharedFile, loadData]);

  // Upload file with optimization
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

    // Compress images
    let uploadFileData = file;
    if (file.type.startsWith("image/")) {
      uploadFileData = await compressImage(file);
    }

    setUploading(true);

    if (studentMode) {
      // ⚡ FAST PATH: Skip summarization, go straight to Quiz/Flashcard
      setUploadProgress("⚡ Đang trích xuất nội dung...");
      try {
        const result = await documentService.fastUpload(uploadFileData, "quiz");
        setToast({ message: "✅ Sẵn sàng! Đang tạo Quiz...", type: "success" });
        loadData();
        // Navigate to quiz with the doc_id
        setTimeout(() => navigate(`/quiz?doc_id=${result.id}`), 500);
      } catch (err: any) {
        setToast({ message: err.message || "Lỗi xử lý file", type: "error" });
      } finally {
        setUploading(false);
        setUploadProgress("");
      }
    } else {
      // Normal path: full summarization
      setUploadProgress("🚀 Đang tải lên & AI tóm tắt...");
      try {
        // Check cache
        const fileHash = await generateFileHash(file);
        const cacheKey = `file_${fileHash}`;
        if (fileCache.has(cacheKey)) {
          const cached = fileCache.get(cacheKey);
          setActiveDoc(cached);
          setToast({ message: "✅ Lấy từ cache!", type: "success" });
          loadData();
          setUploading(false);
          setUploadProgress("");
          return;
        }

        const result = await documentService.uploadAndProcess(uploadFileData);
        fileCache.set(cacheKey, result);
        if (fileCache.size > 100) {
          const firstKey = fileCache.keys().next().value;
          fileCache.delete(firstKey);
        }
        setActiveDoc(result);
        setToast({ message: "✅ Xử lý thành công!", type: "success" });
        loadData();
      } catch (err: any) {
        setToast({ message: err.message || "Lỗi xử lý file", type: "error" });
      } finally {
        setUploading(false);
        setUploadProgress("");
      }
    }
  };

  // Solve problem with streaming UI
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
      setToast({
        message: err.message || "Lỗi khi giải bài. Vui lòng thử lại.",
        type: "error",
      });
    } finally {
      setSolving(false);
      setUploadProgress("");
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await documentService.deleteDocument(docId);
      setToast({ message: "🗑️ Đã xóa tài liệu", type: "success" });
      if (activeDoc?.id === docId) setActiveDoc(null);
      loadData();
    } catch (err: any) {
      setToast({ message: err.message || "Lỗi khi xóa tài liệu", type: "error" });
    }
  };

  const [renameDoc, setRenameDoc] = useState<{ docId: string; currentName: string } | null>(null);
  const [newName, setNewName] = useState("");

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

  // Memoize handlers
  const handleFileSelect = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      uploadFile(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [uploadFile, navigate]
  );

  const handleCameraSelect = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      uploadFile(file, true); // studentMode = true → auto redirect to Quiz
      if (cameraInputRef.current) cameraInputRef.current.value = "";
    },
    [uploadFile, navigate]
  );

  const handleSolveCamera = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      solveProblem(file);
      if (solveCameraRef.current) solveCameraRef.current.value = "";
    },
    [solveProblem]
  );

  return (
    <Page className="ch-page">
      {toast && (
        <Box
          style={{
            position: "fixed",
            top: 20,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 9999,
            padding: "12px 24px",
            borderRadius: "var(--radius-full)",
            background: toast.type === "error" ? "#EF4444" : toast.type === "success" ? "#10B981" : "#3B82F6",
            color: "white",
            fontSize: 14,
            fontWeight: 700,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            animation: "slideDown 0.3s ease-out",
          }}
        >
          {toast.message}
        </Box>
      )}

      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 18 }}>

        {/* HEADER */}
        <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Box
            onClick={() => navigate("/")}
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
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </Box>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Box
              style={{
                width: 46,
                height: 46,
                borderRadius: 16,
                background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 6px 20px rgba(59,130,246,0.30)",
              }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </Box>
            <Box>
              <Text style={{ fontSize: "var(--font-size-xl)", fontWeight: 900, color: "var(--color-text-primary)", letterSpacing: "-0.02em" }}>
                Trợ Lý AI
              </Text>
              <Box style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                <Box
                  style={{
                    padding: "4px 10px",
                    borderRadius: "var(--radius-full)",
                    background: "linear-gradient(135deg, #F59E0B, #FBBF24)",
                    color: "white",
                    fontSize: 10,
                    fontWeight: 800,
                  }}
                >
                  📚 DÀNH CHO HỌC SINH
                </Box>
                <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", fontWeight: 500 }}>
                  {greeting.emoji} {greeting.text}
                </Text>
              </Box>
            </Box>
          </Box>
        </Box>

        {/* QUICK ACTIONS — LOCKED IN DEMO */}
        <Box style={{ position: "relative" }}>
          <FileUploadSection
            onFileSelect={uploadFile}
            uploading={uploading}
            uploadProgress={uploadProgress}
          />
          {DEMO_MODE && (
            <Box onClick={() => lockFeature("upload")} style={{
              position: "absolute", inset: 0, borderRadius: "var(--radius-xl)",
              background: "rgba(255,255,255,0.5)", backdropFilter: "blur(2px)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", zIndex: 10,
            }}>
              <Box style={{
                padding: "10px 20px", borderRadius: "var(--radius-full)",
                background: "rgba(0,0,0,0.7)", color: "white",
                fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 6,
              }}>
                🔒 Sắp ra mắt
              </Box>
            </Box>
          )}
        </Box>

        {/* SOLVE PROBLEM SECTION — LOCKED IN DEMO */}
        <Box style={{ position: "relative" }}>
          <Box
            style={{
              padding: "16px",
              borderRadius: "var(--radius-xl)",
              background: "linear-gradient(135deg, #FEF3C7, #FDE68A)",
              border: "2px solid #F59E0B",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 14,
              boxShadow: "0 8px 24px rgba(245,158,11,0.25)",
              transition: "all 0.2s",
            }}
            onClick={() => DEMO_MODE ? lockFeature("solve") : solveCameraRef.current?.click()}
          >
            <Box
              style={{
                width: 52,
                height: 52,
                borderRadius: "var(--radius-md)",
                background: "white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(0,0,0,0.10)",
              }}
            >
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
            <Box style={{ padding: "6px 12px", borderRadius: "var(--radius-full)", background: "#F59E0B", color: "white", fontSize: 11, fontWeight: 800 }}>
              SẮP RA MẮT
            </Box>
          </Box>
        </Box>

        {/* SOLVE RESULT */}
        {solveResult && !DEMO_MODE && (
          <SolveResultPanel
            result={solveResult}
            onClose={() => setSolveResult(null)}
            onCreateQuiz={() => {
              setToast({ message: "🧠 Đang tạo quiz...", type: "info" });
            }}
          />
        )}

        {/* ═══ KHO ĐỀ THI - PUBLIC LIBRARY ═══ */}
        <Box style={{ marginTop: 8 }}>
          <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <Text style={{ fontSize: 17, fontWeight: 900, color: "var(--color-text-primary)" }}>
              📚 Kho Đề Thi
            </Text>
            <Box onClick={() => navigate("/quiz")} style={{
              padding: "6px 14px", borderRadius: "var(--radius-full)",
              background: "var(--color-primary-lighter)",
              cursor: "pointer",
            }}>
              <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-primary)" }}>Xem tất cả →</Text>
            </Box>
          </Box>

          {/* Subject Tags */}
          <Box style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8, marginBottom: 12 }}>
            {["📖 Tất cả", "🇬🇧 Tiếng Anh", "📜 Lịch Sử", "🧮 Toán", "🧪 Hóa", "⚡ Lý", "🌱 Sinh"].map((tag) => (
              <Box key={tag} style={{
                padding: "8px 16px", borderRadius: "var(--radius-full)",
                background: tag.includes("Tất cả") ? "var(--gradient-primary)" : "var(--color-bg-subtle)",
                color: tag.includes("Tất cả") ? "white" : "var(--color-text-secondary)",
                fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", cursor: "pointer",
                border: tag.includes("Tất cả") ? "none" : "1px solid var(--color-border)",
                flexShrink: 0,
              }}>{tag}</Box>
            ))}
          </Box>

          {/* Exam Cards */}
          <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {publicExams.length > 0 ? publicExams.slice(0, 8).map((doc: any) => (
              <Box key={doc.id} style={{
                padding: "14px 16px", borderRadius: 14,
                background: "var(--color-bg-card)", border: "1px solid var(--color-border)",
                display: "flex", alignItems: "center", gap: 12, cursor: "pointer",
                transition: "all 0.15s",
              }} onClick={() => navigate(`/quiz?doc_id=${doc.id}`)}>
                <Box style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0,
                }}>
                  <Text style={{ fontSize: 22 }}>📝</Text>
                </Box>
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{
                    fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>{doc.name || "Đề thi"}</Text>
                  <Text style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 2 }}>
                    Quiz • Flashcard
                  </Text>
                </Box>
                <Box style={{
                  padding: "6px 12px", borderRadius: "var(--radius-full)",
                  background: "linear-gradient(135deg,#8B5CF6,#7C3AED)",
                  color: "white", fontSize: 11, fontWeight: 700,
                }}>Làm bài</Box>
              </Box>
            )) : (
              <Box style={{
                padding: 24, textAlign: "center", borderRadius: 14,
                background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              }}>
                <Text style={{ fontSize: 32, marginBottom: 8 }}>📭</Text>
                <Text style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-secondary)" }}>Chưa có đề thi nào</Text>
                <Text style={{ fontSize: 12, color: "var(--color-text-tertiary)", marginTop: 4 }}>Đề thi sẽ được cập nhật sớm!</Text>
              </Box>
            )}
          </Box>
        </Box>

        {/* DOCUMENT LIST */}
        <DocumentList
          documents={docs}
          loading={loading}
          activeDocId={activeDoc?.id || null}
          onSelectDoc={setActiveDoc}
          onDeleteDoc={handleDelete}
          onRenameDoc={(id, name) => setRenameDoc({ docId: id, currentName: name })}
          onNavigate={(path) => navigate(path)}
        />

        {/* ACTIVE DOC - SUMMARY + Q&A — HIDDEN IN DEMO */}
        {activeDoc && !DEMO_MODE && (
          <Box className="ch-card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Header */}
            <Box
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "14px 18px",
                background: "linear-gradient(135deg, #EEF2FF, #E0E7FF)",
                borderBottom: "1px solid rgba(99,102,241,0.12)",
              }}
            >
              <Box style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <Text
                  style={{
                    fontSize: 14,
                    fontWeight: 800,
                    color: "#4338CA",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {activeDoc.name}
                </Text>
              </Box>
              <Box
                onClick={() => setActiveDoc(null)}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  cursor: "pointer",
                  background: "rgba(99,102,241,0.1)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  color: "#6366F1",
                  fontWeight: 800,
                }}
              >
                ✕
              </Box>
            </Box>

            {/* Content Tabs - Summary | Q&A */}
            <Box style={{ padding: "18px 18px 14px", height: 560, display: "flex", flexDirection: "column" }}>
              <SummaryPanel doc={activeDoc} />
              <Box style={{ height: 16 }} />
              <QAPanel doc={activeDoc} />
            </Box>
          </Box>
        )}

        {/* HIDDEN INPUTS */}
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
      </Box>

      {/* RENAME MODAL */}
      {renameDoc && (
        <Box
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 20,
          }}
        >
          <Box
            style={{
              width: "100%",
              maxWidth: 320,
              background: "white",
              borderRadius: "var(--radius-xl)",
              padding: "24px",
              boxShadow: "var(--shadow-xl)",
              animation: "scaleIn 0.2s var(--ease-spring)",
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: 800, color: "var(--color-text-primary)", marginBottom: 8 }}>
              ✏️ Đổi tên tài liệu
            </Text>
            <Text style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>
              Tên mới cho tài liệu:
            </Text>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
              style={{
                width: "100%",
                padding: "12px 16px",
                borderRadius: "var(--radius-lg)",
                border: "1.5px solid var(--color-border)",
                background: "var(--color-bg-subtle)",
                fontSize: 15,
                fontFamily: "var(--font-family)",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
            <Box style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button
                onClick={() => {
                  setRenameDoc(null);
                  setNewName("");
                }}
                style={{
                  flex: 1,
                  padding: "12px",
                  borderRadius: "var(--radius-full)",
                  background: "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-secondary)",
                  fontWeight: 700,
                  fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Hủy
              </button>
              <button
                onClick={handleRename}
                disabled={!newName.trim()}
                style={{
                  flex: 1,
                  padding: "12px",
                  borderRadius: "var(--radius-full)",
                  background: newName.trim() ? "var(--gradient-primary)" : "var(--color-bg-subtle)",
                  border: "none",
                  color: newName.trim() ? "white" : "var(--color-text-tertiary)",
                  fontWeight: 700,
                  fontSize: 14,
                  cursor: newName.trim() ? "pointer" : "not-allowed",
                }}
              >
                Lưu
              </button>
            </Box>
          </Box>
        </Box>
      )}

      {/* 🔒 LOCK MODAL */}
      {showLockModal && (
        <Box
          onClick={() => setShowLockModal(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 10000, padding: 20, backdropFilter: "blur(4px)",
          }}
        >
          <Box
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "100%", maxWidth: 300, background: "white",
              borderRadius: 20, padding: "32px 24px", textAlign: "center",
              boxShadow: "0 24px 48px rgba(0,0,0,0.2)",
              animation: "scaleIn 0.2s var(--ease-spring)",
            }}
          >
            <Text style={{ fontSize: 48, lineHeight: 1, marginBottom: 12 }}>🔒</Text>
            <Text style={{ fontSize: 18, fontWeight: 900, color: "var(--color-text-primary)", marginBottom: 8 }}>
              Sắp ra mắt!
            </Text>
            <Text style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.6, marginBottom: 20 }}>
              Tính năng này đang được phát triển.
              Hiện tại bạn có thể làm Quiz và Flashcard từ Kho Đề Thi nhé!
            </Text>
            <Box style={{ display: "flex", gap: 10 }}>
              <Box onClick={() => setShowLockModal(false)} style={{
                flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
                cursor: "pointer", fontSize: 14, fontWeight: 700, color: "var(--color-text-secondary)",
                textAlign: "center",
              }}>Đóng</Box>
              <Box onClick={() => { setShowLockModal(false); navigate("/quiz"); }} style={{
                flex: 1, padding: "12px", borderRadius: "var(--radius-full)",
                background: "var(--gradient-primary)", border: "none",
                cursor: "pointer", fontSize: 14, fontWeight: 700, color: "white",
                textAlign: "center",
              }}>🧠 Làm Quiz</Box>
            </Box>
          </Box>
        </Box>
      )}
    </Page>
  );
}

export default FileProcessingPage;

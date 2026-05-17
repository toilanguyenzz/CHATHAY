/* ─── File Upload Section Component ─── */
import { Box, Text } from "zmp-ui";
import { useState, useRef } from "react";
import { IconUpload, IconCamera, IconImage } from "../components/icons";

interface FileUploadSectionProps {
  onFileSelect: (file: File, mode?: "summary" | "quiz" | "flashcard" | "both") => Promise<void>;
  uploading: boolean;
  uploadProgress: string;
}

export function FileUploadSection({ onFileSelect, uploading, uploadProgress }: FileUploadSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const modeRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const mode = modeRef.current?.value || "both";
    onFileSelect(file, mode as any);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCameraSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    onFileSelect(file, "quiz"); // camera → quiz fast path
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const handleGallerySelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    onFileSelect(file, "quiz"); // gallery → quiz fast path
    if (galleryInputRef.current) galleryInputRef.current.value = "";
  };

  return (
    <>
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
      {/* Hidden mode selector */}
      <input ref={modeRef} type="hidden" value="both" />

      {/* Quick Actions: Camera & Album - ONE CLICK TO QUIZ */}
      <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        <Box
          className="ch-btn-primary"
          onClick={() => {
            modeRef.current!.value = "quiz";
            cameraInputRef.current?.click();
          }}
          style={{ padding: "12px", justifyContent: "center", flexDirection: "column", gap: 4, background: "linear-gradient(135deg,#10B981,#059669)", border: "none" }}
        >
          <IconCamera size={22} color="white" />
          <Text style={{ fontSize: 11, fontWeight: 700 }}>📸 Quiz</Text>
        </Box>
        <Box
          className="ch-btn-secondary"
          onClick={() => {
            modeRef.current!.value = "quiz";
            galleryInputRef.current?.click();
          }}
          style={{ padding: "12px", justifyContent: "center", flexDirection: "column", gap: 4, background: "linear-gradient(135deg,#8B5CF6,#7C3AED)", border: "none" }}
        >
          <IconImage size={22} color="white" />
          <Text style={{ fontSize: 11, fontWeight: 700 }}>🖼️ Quiz</Text>
        </Box>
        <Box
          className="ch-btn-secondary"
          onClick={() => {
            modeRef.current!.value = "flashcard";
            fileInputRef.current?.click();
          }}
          style={{ padding: "12px", justifyContent: "center", flexDirection: "column", gap: 4, background: "linear-gradient(135deg,#F59E0B,#D97706)", border: "none" }}
        >
          <span style={{ fontSize: 22 }}>📇</span>
          <Text style={{ fontSize: 11, fontWeight: 700 }}>Flashcard</Text>
        </Box>
      </Box>

      {/* Upload Zone - Full Upload (Summary + Quiz + Flashcard) */}
      <Box
        className="ch-card"
        style={{
          padding: 28,
          textAlign: "center",
          border: uploading ? "2px solid #8B5CF6" : "2px dashed #3B82F6",
          borderRadius: "var(--radius-xl)",
          background: uploading ? "linear-gradient(135deg,#F3E8FF,#EDE9FE)" : "linear-gradient(135deg,#EFF6FF,#DBEAFE)",
          cursor: uploading ? "wait" : "pointer",
        }}
        onClick={() => {
          if (!uploading) {
            modeRef.current!.value = "both";
            fileInputRef.current?.click();
          }
        }}
      >
        {uploading ? (
          <>
            <Box
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                border: "3px solid #E9D5FF",
                borderTopColor: "#8B5CF6",
                animation: "spin 1s linear infinite",
                margin: "0 auto 12px",
              }}
            />
            <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 800, color: "#7C3AED" }}>
              {uploadProgress}
            </Text>
            <Text className="ch-caption">Đang xử lý file...</Text>
          </>
        ) : (
          <>
            <Box
              style={{
                width: 56,
                height: 56,
                borderRadius: "var(--radius-full)",
                background: "linear-gradient(135deg,#3B82F6,#6366F1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 14px",
                boxShadow: "0 8px 24px rgba(59,130,246,0.30)",
              }}
            >
              <IconUpload size={28} color="white" />
            </Box>
            <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 900, color: "#1D4ED8", marginBottom: 4 }}>
              Tải lên & AI xử lý ngay
            </Text>
            <Text style={{ fontSize: 13, color: "var(--color-text-tertiary)", lineHeight: 1.5 }}>
              PDF, Word → Tóm tắt + Flashcard + Quiz
            </Text>
            <Box style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12 }}>
              {["PDF", "Word", "Ảnh"].map((t) => (
                <Box
                  key={t}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "var(--radius-full)",
                    background: "rgba(59,130,246,0.08)",
                    border: "1px solid rgba(59,130,246,0.15)",
                    fontSize: 12,
                    fontWeight: 700,
                    color: "#3B82F6",
                  }}
                >
                  {t}
                </Box>
              ))}
            </Box>
          </>
        )}
      </Box>
    </>
  );
}

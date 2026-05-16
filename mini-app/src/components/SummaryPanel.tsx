import { Box, Text } from "zmp-ui";
import { useRef } from "react";

interface SummaryPanelProps {
  doc: any;
  setToast: (toast: { message: string; type: "error" | "success" | "info" }) => void;
}

function SummaryPanel({ doc, setToast }: SummaryPanelProps) {
  const summaryRef = useRef<any>(null);

  return (
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
  );
}

// Import IconDoc from icons - placeholder since we'll export from parent
import { IconDoc } from "../components/icons";

export default SummaryPanel;

import { Box, Text } from "zmp-ui";
import { useState } from "react";

interface ShareQuizPanelProps {
  quizId: string;
  title: string;
  questionsCount: number;
  onClose: () => void;
}

export function ShareQuizPanel({ quizId, title, questionsCount, onClose }: ShareQuizPanelProps) {
  const [shareCode, setShareCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const generateShareCode = async () => {
    setLoading(true);
    try {
      const userId = (window as any).__USER_ID__ || "";
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/shared-quiz/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": userId,
        },
        body: JSON.stringify({
          user_id: userId,
          doc_id: quizId,
          title: title,
          subject: "tong_hop",
          chapter: "",
        }),
      });

      const data = await response.json();
      if (data.success) {
        setShareCode(data.share_code);
      }
    } catch (err) {
      console.error("Failed to generate share code:", err);
      alert("Không thể tạo link share. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const copyLink = () => {
    const link = `${window.location.origin}/quiz/${shareCode}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const shareToZalo = () => {
    const link = `${window.location.origin}/quiz/${shareCode}`;
    const shareText = `📚 Ôn tập cùng tôi!\n${title}\n${questionsCount} câu hỏi\nThử thách: ${link}`;

    // Zalo share intent
    window.ZMP?.share?.({
      type: "text",
      payload: { text: shareText },
    });
  };

  if (!shareCode) {
    return (
      <Box
        style={{
          padding: "20px",
          borderRadius: "var(--radius-xl)",
          background: "linear-gradient(135deg, #667EEA, #764BA2)",
          color: "white",
          marginTop: 12,
        }}
      >
        <Text style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>📤 Chia sẻ Quiz cho lớp</Text>
        <Text style={{ fontSize: 13, opacity: 0.9, marginBottom: 16 }}>
          Tạo link share để gửi cho học sinh. Học sinh sẽ làm quiz và kết quả tự động gửi về bạn!
        </Text>
        <Box
          onClick={generateShareCode}
          style={{
            padding: "14px 20px",
            borderRadius: "var(--radius-lg)",
            background: "rgba(255,255,255,0.2)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,0.3)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          {loading ? (
            <Text>⏳ Đang tạo link...</Text>
          ) : (
            <>
              <Text style={{ fontSize: 18 }}>🔗</Text>
              <Text style={{ fontSize: 14, fontWeight: 700 }}>Tạo Link Share</Text>
            </>
          )}
        </Box>
      </Box>
    );
  }

  const shareLink = `${window.location.origin}/quiz/${shareCode}`;

  return (
    <Box
      style={{
        padding: "20px",
        borderRadius: "var(--radius-xl)",
        background: "linear-gradient(135deg, #10B981, #059669)",
        color: "white",
        marginTop: 12,
      }}
    >
      <Text style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>✅ Link đã tạo!</Text>
      <Text style={{ fontSize: 13, opacity: 0.9, marginBottom: 12 }}>
        Gửi link này cho học sinh qua Zalo nhóm lớp:
      </Text>

      {/* Link Box */}
      <Box
        style={{
          padding: "12px 16px",
          borderRadius: "var(--radius-lg)",
          background: "rgba(255,255,255,0.15)",
          border: "1px solid rgba(255,255,255,0.25)",
          marginBottom: 12,
          wordBreak: "break-all",
        }}
      >
        <Text style={{ fontSize: 12, fontWeight: 600 }}>{shareLink}</Text>
      </Box>

      {/* Action Buttons */}
      <Box style={{ display: "flex", gap: 8 }}>
        <Box
          onClick={copyLink}
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "var(--radius-lg)",
            background: "rgba(255,255,255,0.2)",
            backdropFilter: "blur(8px)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          <Text style={{ fontSize: 16 }}>{copied ? "✅" : "📋"}</Text>
          <Text style={{ fontSize: 13, fontWeight: 700 }}>{copied ? "Đã copy" : "Copy Link"}</Text>
        </Box>

        <Box
          onClick={shareToZalo}
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "var(--radius-lg)",
            background: "rgba(0,191,255,0.3)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          <Text style={{ fontSize: 16 }}>💬</Text>
          <Text style={{ fontSize: 13, fontWeight: 700 }}>Share Zalo</Text>
        </Box>

        <Box
          onClick={onClose}
          style={{
            padding: "12px 16px",
            borderRadius: "var(--radius-lg)",
            background: "rgba(255,255,255,0.1)",
            cursor: "pointer",
          }}
        >
          <Text style={{ fontSize: 16 }}>✕</Text>
        </Box>
      </Box>
    </Box>
  );
}
/* ─── Document List Component ─── */
import { Box, Text } from "zmp-ui";
import { IconDoc, IconFolder, IconFlashcard, IconQuiz, IconRefresh } from "../components/icons";

interface Document {
  id: string;
  name: string;
  doc_type: "pdf" | "word" | "image";
  timestamp: number;
}

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  activeDocId: string | null;
  onSelectDoc: (doc: Document) => void;
  onDeleteDoc: (docId: string) => void;
  onRenameDoc: (docId: string, currentName: string) => void;
  onNavigate: (path: string) => void;
}

export function DocumentList({
  documents,
  loading,
  activeDocId,
  onSelectDoc,
  onDeleteDoc,
  onRenameDoc,
  onNavigate,
}: DocumentListProps) {
  const getDocIcon = (type: string) => {
    const isPdf = type === "pdf";
    const isWord = type === "word" || type === "docx";
    const bgColor = isPdf ? "#FEE2E2" : isWord ? "#DBEAFE" : "#FEF3C7";
    const color = isPdf ? "#EF4444" : isWord ? "#3B82F6" : "#F59E0B";
    return { bgColor, color };
  };

  const quickActions = [
    { label: "Tóm tắt", icon: <IconDoc size={20} color="#3B82F6" />, bg: "#EFF6FF", action: "summary" },
    { label: "Flashcard", icon: <IconFlashcard size={20} color="#F59E0B" />, bg: "#FEF3C7", action: "flashcard" },
    { label: "Quiz", icon: <IconQuiz size={20} color="#8B5CF6" />, bg: "#F3E8FF", action: "quiz" },
    { label: "Kho", icon: <IconFolder size={20} color="#22C55E" />, bg: "#DCFCE7", action: "vault" },
  ];

  return (
    <Box>
      <Text className="ch-section-title" style={{ marginBottom: 12 }}>
        Kết quả xử lý gần nhất
      </Text>

      {loading ? (
        <Box style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[1, 2].map((i) => (
            <Box key={i} style={{ width: "100%", height: 80, borderRadius: 16, background: "rgba(0,0,0,0.05)" }} />
          ))}
        </Box>
      ) : documents.length === 0 ? (
        <Box style={{ textAlign: "center", padding: 24 }}>
          <IconDoc size={32} color="#9E9BB8" />
          <Text className="ch-caption" style={{ marginTop: 8 }}>
            Chưa có tài liệu — tải lên file đầu tiên!
          </Text>
        </Box>
      ) : (
        <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {documents.map((doc, idx) => {
            const isActive = activeDocId === doc.id;
            const { bgColor, color } = getDocIcon(doc.doc_type);

            return (
              <Box
                key={doc.id || idx}
                className="ch-card"
                style={{
                  padding: 14,
                  cursor: "pointer",
                  border: isActive ? "2px solid var(--color-primary)" : "1px solid var(--color-border)",
                }}
                onClick={() => onSelectDoc(doc)}
              >
                <Box style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                  <Box className="ch-doc-icon" style={{ background: bgColor }}>
                    <IconDoc size={20} color={color} />
                  </Box>
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <Text
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: "var(--color-text-primary)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {doc.name}
                    </Text>
                    <Text className="ch-caption">
                      {new Date(doc.timestamp * 1000).toLocaleDateString("vi-VN")}
                    </Text>
                  </Box>
                  {/* Edit button */}
                  <Box
                    onClick={(e) => {
                      e.stopPropagation();
                      onRenameDoc(doc.id, doc.name);
                    }}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      cursor: "pointer",
                      background: "rgba(0,0,0,0.04)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--color-text-secondary)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                  </Box>
                </Box>

                {/* Quick actions */}
                <Box style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                  {quickActions.map((action, i) => (
                    <Box
                      key={i}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (action.action === "summary") {
                          onSelectDoc(doc); // Open summary
                        } else {
                          onNavigate(`/${action.action}?doc=${doc.id}`);
                        }
                      }}
                      style={{
                        textAlign: "center",
                        padding: "12px 8px",
                        borderRadius: "var(--radius-lg)",
                        background: action.bg,
                        cursor: "pointer",
                        transition: "all 0.2s",
                        minHeight: 70,
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                        alignItems: "center",
                      }}
                    >
                      <Box style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>{action.icon}</Box>
                      <Text style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-secondary)" }}>
                        {action.label}
                      </Text>
                    </Box>
                  ))}
                  {/* Delete button */}
                  <Box
                    key="delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteDoc(doc.id);
                    }}
                    style={{
                      textAlign: "center",
                      padding: "12px 8px",
                      borderRadius: "var(--radius-lg)",
                      background: "#FEE2E2",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      minHeight: 70,
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <Box style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#EF4444"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
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
  );
}

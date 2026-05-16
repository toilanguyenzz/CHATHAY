import { Box, Text } from "zmp-ui";
import { IconDoc, IconFlashcard, IconQuiz, IconFolder, IconInbox } from "./icons";

interface DocumentListProps {
  docs: any[];
  loading: boolean;
  activeDoc: any | null;
  setActiveDoc: (doc: any | null) => void;
  setRenameDoc: (doc: { docId: string; currentName: string } | null) => void;
  setDeleteConfirm: (doc: { docId: string; name: string } | null) => void;
  navigate: (path: string) => void;
}

function Skeleton({ w = "100%", h = 20, r = 10, style }: { w?: string | number; h?: number; r?: number; style?: React.CSSProperties }) {
  return <Box className="ch-skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />;
}

function DocumentList({
  docs, loading, activeDoc, setActiveDoc, setRenameDoc, setDeleteConfirm, navigate
}: DocumentListProps) {
  return (
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
  );
}

export default DocumentList;

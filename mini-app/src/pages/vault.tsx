import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useEffect } from "react";
import { documentService } from "../services/documentService";
import { useAuth } from "../hooks/useAuth";

interface DocItem {
  id: string;
  name: string;
  doc_type: string;
  summary?: string;
  timestamp: number;
}

const typeConfig: Record<string, { emoji: string; color: string; bgColor: string; label: string }> = {
  pdf: { emoji: "📕", color: "#EF4444", bgColor: "#FEE2E2", label: "PDF" },
  word: { emoji: "📘", color: "#3B82F6", bgColor: "#DBEAFE", label: "Word" },
  ppt: { emoji: "📙", color: "#F59E0B", bgColor: "#FEF3C7", label: "PPT" },
  docx: { emoji: "📘", color: "#3B82F6", bgColor: "#DBEAFE", label: "Word" },
  pptx: { emoji: "📙", color: "#F59E0B", bgColor: "#FEF3C7", label: "PPT" },
};

type FilterType = "all" | "pdf" | "word" | "ppt" | "docx" | "pptx";

function formatDate(timestamp: number): string {
  const d = new Date(timestamp * 1000);
  return `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1).toString().padStart(2, "0")}`;
}

function formatSize(summary: string): string {
  if (!summary) return "0 MB";
  const bytes = summary.length;
  const mb = (bytes / (1024 * 1024)).toFixed(1);
  return `${mb} MB`;
}

function VaultPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!user_id) return;
    setLoading(true);
    documentService.getDocuments()
      .then(data => {
        setDocs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [user_id]);

  const filteredDocs = docs.filter(d => {
    const matchFilter = filter === "all" || d.doc_type === filter;
    const matchSearch = d.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchFilter && matchSearch;
  });

  const totalSize = filteredDocs.reduce((acc, d) => acc + (d.summary ? d.summary.length : 0), 0);
  const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(1);

  const handleDelete = async (docId: string) => {
    if (!confirm("Xóa tài liệu này?")) return;
    try {
      await documentService.deleteDocument(docId);
      setDocs(prev => prev.filter(d => d.id !== docId));
    } catch (e) {
      alert("Lỗi xóa tài liệu");
    }
  };

  return (
    <Page className="ch-page">
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {/* Header */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Box onClick={() => navigate("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", flexShrink: 0,
            }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 18, color: "var(--color-text-secondary)" }} />
            </Box>
            <Box>
              <Text className="ch-heading-lg">Kho Tài Liệu</Text>
              <Text className="ch-caption" style={{ marginTop: 4 }}>
                {docs.length} tài liệu · {totalSizeMB} MB
              </Text>
            </Box>
          </Box>
          <Box className="ch-fab" style={{
            width: 44, height: 44,
            background: "var(--gradient-primary)", color: "white",
            boxShadow: "0 4px 16px rgba(91, 76, 219, 0.30)",
          }}>
            <Icon icon="zi-plus" style={{ fontSize: 20 }} />
          </Box>
        </Box>

        {/* Search Bar */}
        <Box className="ch-search">
          <Icon icon="zi-search" style={{ fontSize: 18, color: "var(--color-text-tertiary)" }} />
          <input
            type="text"
            placeholder="Tìm tài liệu..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              border: "none", outline: "none", background: "transparent",
              flex: 1, fontSize: "var(--font-size-sm)", fontFamily: "var(--font-family)",
              color: "var(--color-text-primary)", fontWeight: 500,
            }}
          />
          {searchQuery && (
            <Box onClick={() => setSearchQuery("")} style={{ cursor: "pointer", display: "flex" }}>
              <Icon icon="zi-close" style={{ fontSize: 16, color: "var(--color-text-tertiary)" }} />
            </Box>
          )}
        </Box>

        {/* Filter Chips */}
        <Box style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 2 }}>
          {([
            { key: "all" as FilterType, label: "Tất cả", count: docs.length },
            { key: "pdf" as FilterType, label: "PDF", count: docs.filter(d => d.doc_type === "pdf").length },
            { key: "word" as FilterType, label: "Word", count: docs.filter(d => d.doc_type === "word" || d.doc_type === "docx").length },
            { key: "ppt" as FilterType, label: "PPT", count: docs.filter(d => d.doc_type === "ppt" || d.doc_type === "pptx").length },
          ]).map(f => (
            <Box
              key={f.key}
              onClick={() => setFilter(f.key)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: "var(--radius-full)",
                background: filter === f.key ? "var(--color-primary)" : "var(--color-bg-card)",
                color: filter === f.key ? "white" : "var(--color-text-secondary)",
                border: filter === f.key ? "none" : "1px solid var(--color-border)",
                cursor: "pointer", whiteSpace: "nowrap",
                fontWeight: 700, fontSize: 13,
                transition: "all 0.2s",
                boxShadow: filter === f.key ? "0 3px 12px rgba(91, 76, 219, 0.25)" : "none",
              }}
            >
              <span>{f.label}</span>
              <span style={{
                fontSize: 11, fontWeight: 800,
                padding: "1px 6px", borderRadius: "var(--radius-full)",
                background: filter === f.key ? "rgba(255,255,255,0.25)" : "var(--color-bg-subtle)",
              }}>{f.count}</span>
            </Box>
          ))}
        </Box>

        {/* Document List */}
        {loading ? (
          <Box style={{ display: "flex", justifyContent: "center", padding: 40 }}>
            <Text className="ch-caption">Đang tải...</Text>
          </Box>
        ) : (
          <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filteredDocs.length === 0 ? (
              <Box className="ch-empty">
                <Text style={{ fontSize: 48, marginBottom: 12 }}>📭</Text>
                <Text className="ch-body-sm">Không tìm thấy tài liệu</Text>
              </Box>
            ) : (
              filteredDocs.map((doc, idx) => {
                const cfg = typeConfig[doc.doc_type] || typeConfig["pdf"];
                return (
                  <Box key={doc.id} className="ch-doc-item" style={{ animationDelay: `${idx * 50}ms` }}>
                    <Box className="ch-doc-icon" style={{ background: cfg.bgColor }}>
                      <Text style={{ fontSize: 22 }}>{cfg.emoji}</Text>
                    </Box>
                    <Box style={{ flex: 1, minWidth: 0 }}>
                      <Text style={{
                        fontSize: "var(--font-size-sm)", fontWeight: 700,
                        color: "var(--color-text-primary)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>{doc.name}</Text>
                      <Box style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                        <Text className="ch-caption">{formatSize(doc.summary || "")}</Text>
                        <Box style={{ width: 3, height: 3, borderRadius: "50%", background: "var(--color-text-tertiary)" }} />
                        <Text className="ch-caption">{formatDate(doc.timestamp)}</Text>
                      </Box>
                    </Box>
                    <Box style={{
                      padding: "4px 10px", borderRadius: "var(--radius-full)",
                      background: cfg.bgColor, fontSize: 10, fontWeight: 800,
                      color: cfg.color, letterSpacing: "0.02em",
                    }}>{cfg.label}</Box>
                    <Box
                      onClick={() => handleDelete(doc.id)}
                      style={{ cursor: "pointer", padding: 4 }}
                    >
                      <Icon icon="zi-close" style={{ fontSize: 14, color: "var(--color-text-tertiary)" }} />
                    </Box>
                  </Box>
                );
              })
            )}
          </Box>
        )}
      </Box>
    </Page>
  );
}

export default VaultPage;

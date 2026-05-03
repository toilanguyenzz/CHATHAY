import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState } from "react";

/* ─── Greeting ─── */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return { text: "Chào buổi sáng", emoji: "☀️" };
  if (h < 18) return { text: "Chào buổi chiều", emoji: "🌤️" };
  return { text: "Chào buổi tối", emoji: "🌙" };
}

function FileProcessingPage() {
  const navigate = useNavigate();
  const greeting = getGreeting();

  const [stats] = useState({ docs: 12, totalSize: "13.3 MB" });

  return (
    <Page className="ch-page">
      <Box className="ch-container ch-stagger" style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* ══════════════ HEADER ══════════════ */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Box style={{
              width: 46, height: 46, borderRadius: 16,
              background: "linear-gradient(135deg, #3B82F6, #1D4ED8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "white", fontWeight: 900, fontSize: 20,
              boxShadow: "0 6px 20px rgba(59, 130, 246, 0.30)",
            }}>📄</Box>
            <Box>
              <Text style={{
                fontSize: "var(--font-size-xl)", fontWeight: 900,
                color: "var(--color-text-primary)", letterSpacing: "-0.02em",
              }}>XỬ LÝ FILE</Text>
              <Text style={{
                fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)",
                fontWeight: 500, marginTop: 1,
              }}>{greeting.emoji} {greeting.text}</Text>
            </Box>
          </Box>
        </Box>

        {/* ══════════════ UPLOAD ZONE ══════════════ */}
        <Box
          className="ch-card"
          style={{
            padding: 24, textAlign: "center",
            border: "2px dashed #3B82F6",
            borderRadius: "var(--radius-xl)",
            background: "linear-gradient(135deg, #EFF6FF, #DBEAFE)",
            cursor: "pointer",
          }}
          onClick={() => alert("Chọn file để upload...")}
        >
          <Text style={{ fontSize: 48, lineHeight: 1, marginBottom: 12 }}>📤</Text>
          <Text style={{
            fontSize: "var(--font-size-base)", fontWeight: 800,
            color: "#1D4ED8", marginBottom: 6,
          }}>Tải lên tài liệu</Text>
          <Text className="ch-caption">Hỗ trợ PDF, Word, PowerPoint</Text>
        </Box>

        {/* ══════════════ THỐNG KÊ FILE ══════════════ */}
        <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Box className="ch-stat-pill ch-stat-pill--blue" style={{ textAlign: "center" }}>
            <Text style={{ fontSize: 22, marginBottom: 4 }}>📄</Text>
            <Text style={{
              fontSize: 26, fontWeight: 900, color: "#3B82F6",
              letterSpacing: "-0.02em", lineHeight: 1,
            }}>{stats.docs}</Text>
            <Text style={{
              fontSize: 12, fontWeight: 600, color: "var(--color-text-tertiary)", marginTop: 4,
            }}>Tài liệu</Text>
          </Box>
          <Box className="ch-stat-pill ch-stat-pill--green" style={{ textAlign: "center" }}>
            <Text style={{ fontSize: 22, marginBottom: 4 }}>💾</Text>
            <Text style={{
              fontSize: 26, fontWeight: 900, color: "#22C55E",
              letterSpacing: "-0.02em", lineHeight: 1,
            }}>{stats.totalSize}</Text>
            <Text style={{
              fontSize: 12, fontWeight: 600, color: "var(--color-text-tertiary)", marginTop: 4,
            }}>Dung lượng</Text>
          </Box>
        </Box>

        {/* ══════════════ TÀI LIỆU GẦN ĐÂY ══════════════ */}
        <Box>
          <Box style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 14,
          }}>
            <Text className="ch-section-title" style={{ marginBottom: 0 }}>📂 Tài liệu gần đây</Text>
            <Box
              onClick={() => navigate("/vault")}
              style={{
                display: "flex", alignItems: "center", gap: 4,
                cursor: "pointer", padding: "4px 10px",
                borderRadius: "var(--radius-full)",
                background: "var(--color-bg-subtle)",
              }}
            >
              <Text style={{
                fontSize: 12, fontWeight: 700, color: "#3B82F6",
              }}>Xem tất cả</Text>
              <Icon icon="zi-chevron-right" style={{ fontSize: 12, color: "#3B82F6" }} />
            </Box>
          </Box>

          <Box style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { name: "Tài liệu ôn thi THPT QG.pdf", emoji: "📕", size: "2.4 MB", date: "28/04" },
              { name: "Giáo trình React cơ bản.docx", emoji: "📘", size: "1.1 MB", date: "25/04" },
              { name: "Slide Toán cao cấp.pptx", emoji: "📙", size: "3.8 MB", date: "20/04" },
            ].map((doc, idx) => (
              <Box key={idx} className="ch-doc-item" onClick={() => navigate("/vault")}>
                <Box className="ch-doc-icon" style={{
                  background: idx === 0 ? "#FEE2E2" : idx === 1 ? "#DBEAFE" : "#FEF3C7",
                }}>
                  <Text style={{ fontSize: 20 }}>{doc.emoji}</Text>
                </Box>
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{
                    fontSize: "var(--font-size-sm)", fontWeight: 700,
                    color: "var(--color-text-primary)",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>{doc.name}</Text>
                  <Text className="ch-caption" style={{ marginTop: 3 }}>{doc.size} · {doc.date}</Text>
                </Box>
                <Icon icon="zi-chevron-right" style={{ fontSize: 14, color: "var(--color-text-tertiary)" }} />
              </Box>
            ))}
          </Box>
        </Box>

        {/* ══════════════ TÍNH NĂNG XỬ LÝ ══════════════ */}
        <Box>
          <Text className="ch-section-title">⚙️ Công cụ xử lý</Text>
          <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              { title: "Nén PDF", desc: "Giảm dung lượng file", icon: "🗜️", color: "#3B82F6" },
              { title: "Gộp file", desc: "Ghép nhiều PDF lại", icon: "📎", color: "#8B5CF6" },
              { title: "Chuyển đổi", desc: "PDF sang Word/Excel", icon: "🔄", color: "#F59E0B" },
              { title: "Trích xuất", desc: "Lấy text từ ảnh/PDF", icon: "📝", color: "#22C55E" },
            ].map((tool, idx) => (
              <Box key={idx} className="ch-card ch-card-interactive" style={{ padding: 16, cursor: "pointer" }}>
                <Box style={{
                  width: 44, height: 44, borderRadius: "var(--radius-md)",
                  background: `${tool.color}15`, display: "flex",
                  alignItems: "center", justifyContent: "center", marginBottom: 10,
                }}>
                  <Text style={{ fontSize: 22 }}>{tool.icon}</Text>
                </Box>
                <Text style={{
                  fontSize: "var(--font-size-sm)", fontWeight: 800,
                  color: "var(--color-text-primary)", marginBottom: 2,
                }}>{tool.title}</Text>
                <Text className="ch-caption">{tool.desc}</Text>
              </Box>
            ))}
          </Box>
        </Box>

      </Box>
    </Page>
  );
}

export default FileProcessingPage;

import { Box, Page, Text, Icon, useNavigate } from "zmp-ui";
import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { studyService } from "../services/studyService";
import { documentService } from "../services/documentService";
import { useAuth } from "../hooks/useAuth";
import { EmptyState } from "../components/EmptyState";

const diffConfig: Record<string, { label: string; color: string; bg: string; emoji: string }> = {
  easy: { label: "Dễ", color: "#16A34A", bg: "#DCFCE7", emoji: "🟢" },
  medium: { label: "Trung bình", color: "#D97706", bg: "#FEF3C7", emoji: "🟡" },
  hard: { label: "Khó", color: "#DC2626", bg: "#FEE2E2", emoji: "🔴" },
};

function FlashcardPage() {
  const navigate = useNavigate();
  const { user_id } = useAuth();
  const { docId } = useParams<{ docId?: string }>();
  const [cards, setCards] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<any>(null);
  const [isShuffled, setIsShuffled] = useState(false);
  const touchStartX = useRef(0);

  // Shuffle cards
  const shuffleCards = () => {
    setCards(prev => {
      const shuffled = [...prev];
      for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      return shuffled;
    });
    setCurrentIndex(0);
    setIsFlipped(false);
    setIsShuffled(true);
  };

  useEffect(() => {
    if (!user_id) return;
    setLoading(true);
    const id = docId || new URLSearchParams(window.location.search).get("doc");
    if (!id) {
      // Load from active doc
      fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/miniapp/documents`, {
        headers: { "Authorization": `Bearer ${(window as any).__CHAT_HAY_TOKEN__ || ""}` },
      })
        .then(r => r.json())
        .then(docs => {
          if (docs?.length > 0) {
            return documentService.getFlashcards(docs[0].id);
          }
          return [];
        })
        .then(data => { setCards(data || []); setLoading(false); })
        .catch(() => setLoading(false));
    } else {
      documentService.getFlashcards(id)
        .then(data => { setCards(data || []); setLoading(false); })
        .catch(() => setLoading(false));
    }
  }, [user_id, docId]);

  if (loading) {
    return (
      <Page className="ch-page">
        <EmptyState
          emoji="⏳️"
          title="Đang tải flashcard..."
          description="Vui lòng chờ trong giây lát"
        />
      </Page>
    );
  }

  if (cards.length === 0) {
    return (
      <Page className="ch-page">
        <EmptyState
          emoji="📭"
          title="Chưa có Flashcard"
          description="Tải tài liệu để tự động tạo flashcard nhé!"
          actionLabel="Tải tài liệu"
          onAction={() => navigate("/file-processing")}
          secondaryActionLabel="Về trang chủ"
          onSecondaryAction={() => navigate("/")}
        />
      </Page>
    );
  }

  const card = cards[currentIndex];
  const total = cards.length;
  const progress = ((currentIndex + 1) / total) * 100;
  const diff = diffConfig[card?.difficulty || "medium"] || diffConfig["medium"];

  const goTo = (dir: "next" | "prev") => {
    setIsFlipped(false);
    setTimeout(() => {
      setCurrentIndex(i => dir === "next" ? Math.min(i + 1, total - 1) : Math.max(i - 1, 0));
    }, 150);
  };

  const handleTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX; };
  const handleTouchEnd = (e: React.TouchEvent) => {
    const diffX = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diffX) > 60) diffX > 0 ? goTo("next") : goTo("prev");
  };

  return (
    <Page className="ch-page">
      <Box className="ch-container" style={{ display: "flex", flexDirection: "column", minHeight: "calc(100vh - 80px)", gap: 0 }}>
        {/* Header */}
        <Box style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Box onClick={() => navigate("/")} style={{
              width: 38, height: 38, borderRadius: "var(--radius-full)",
              background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0,
            }}>
              <Icon icon="zi-chevron-left" style={{ fontSize: 18, color: "var(--color-text-secondary)" }} />
            </Box>
            <Box>
              <Text className="ch-caption" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>FLASHCARD</Text>
              <Text className="ch-heading-lg" style={{ marginTop: 2 }}>{card?.category || "Học tập"}</Text>
            </Box>
          </Box>
          <Box className="ch-badge" style={{ background: diff.bg, color: diff.color }}>
            {diff.emoji} {diff.label}
          </Box>
        </Box>

        {/* Progress */}
        <Box style={{ marginBottom: 6 }}>
          <Box className="ch-progress">
            <Box className="ch-progress-bar" style={{ width: `${progress}%` }} />
          </Box>
          <Box style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
            <Text className="ch-caption">{currentIndex + 1} / {total}</Text>
            {reviewResult?.next_review_label && (
              <Text className="ch-caption" style={{ color: "var(--color-primary)" }}>
                📅 {reviewResult.next_review_label}
              </Text>
            )}
          </Box>
        </Box>

        {/* Card Area */}
        <Box className="ch-flashcard-scene" style={{ flex: 1, padding: "16px 0" }}
          onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}
        >
          <Box className={`ch-flashcard${isFlipped ? " flipped" : ""}`}
            onClick={() => setIsFlipped(!isFlipped)} style={{ maxHeight: 420 }}
          >
            {/* Front */}
            <Box className="ch-flashcard-face ch-flashcard-front">
              <Text style={{ fontSize: 48, marginBottom: 20, lineHeight: 1 }}>📖</Text>
              <Text style={{ fontSize: "var(--font-size-lg)", fontWeight: 700, color: "var(--color-text-primary)", lineHeight: 1.5 }}>{card?.front}</Text>
              <Box style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 24, padding: "8px 16px", borderRadius: "var(--radius-full)", background: "var(--color-bg-subtle)" }}>
                <Text style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-tertiary)", fontWeight: 600 }}>👆 Chạm để xem đáp án</Text>
              </Box>
            </Box>
            {/* Back */}
            <Box className="ch-flashcard-face ch-flashcard-back">
              <Text style={{ fontSize: 40, marginBottom: 16, lineHeight: 1 }}>💡</Text>
              <Text style={{ fontSize: "var(--font-size-base)", fontWeight: 500, color: "white", lineHeight: 1.7, maxWidth: 300 }}>{card?.back}</Text>
              <Box style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 24, padding: "8px 16px", borderRadius: "var(--radius-full)", background: "rgba(255,255,255,0.15)" }}>
                <Text style={{ fontSize: "var(--font-size-xs)", color: "rgba(255,255,255,0.6)", fontWeight: 600 }}>👆 Chạm để lật lại</Text>
              </Box>
            </Box>
          </Box>
        </Box>

        {/* Dot Indicators */}
        <Box className="ch-dots" style={{ marginBottom: 16 }}>
          {cards.map((_, idx) => (
            <Box key={idx} className={`ch-dot${idx === currentIndex ? " active" : ""}`}
              onClick={() => { setIsFlipped(false); setCurrentIndex(idx); }}
              style={{ cursor: "pointer" }}
            />
          ))}
        </Box>

        {/* SM-2 Rating Controls (shown when card is flipped) */}
        {isFlipped && (
          <Box style={{ display: "flex", flexDirection: "column", gap: 10, paddingBottom: 8 }}>
            <Text style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--color-text-tertiary)", textAlign: "center", textTransform: "uppercase", letterSpacing: "0.05em" }}>Đánh giá độ nhớ của bạn:</Text>
            <Box style={{ display: "flex", justifyContent: "center", gap: 8, flexWrap: "wrap" }}>
              {[
                { rating: 'again', label: 'Again', time: '1m', color: '#DC2626', bg: '#FEE2E2', emoji: '🔴' },
                { rating: 'hard', label: 'Hard', time: '10m', color: '#D97706', bg: '#FEF3C7', emoji: '🟡' },
                { rating: 'good', label: 'Good', time: '1d', color: '#16A34A', bg: '#DCFCE7', emoji: '🟢' },
                { rating: 'easy', label: 'Easy', time: '4d', color: '#2563EB', bg: '#DBEAFE', emoji: '🔵' },
              ].map(btn => (
                <Box
                  key={btn.rating}
                  onClick={async () => {
                    if (!sessionId) return;
                    const result = await studyService.reviewFlashcard(sessionId, btn.rating as any);
                    setReviewResult(result);
                    setTimeout(() => {
                      setIsFlipped(false);
                      if (!result.is_done) {
                        setCurrentIndex(i => Math.min(i + 1, total - 1));
                      }
                    }, 600);
                  }}
                  style={{
                    display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
                    padding: "12px 16px", borderRadius: "var(--radius-lg)",
                    background: btn.bg, color: btn.color,
                    border: `2px solid ${btn.color}`,
                    cursor: "pointer", minWidth: 70, flex: 1,
                    transition: "all 0.2s",
                  }}
                >
                  <Text style={{ fontSize: 20, lineHeight: 1 }}>{btn.emoji}</Text>
                  <Text style={{ fontSize: "var(--font-size-sm)", fontWeight: 800 }}>{btn.label}</Text>
                  <Text style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, opacity: 0.8 }}>{btn.time}</Text>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {/* Navigation Controls */}
        <Box style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 16, paddingBottom: 8 }}>
          <Box className="ch-fab ch-fab--secondary" style={{ width: 50, height: 50 }} onClick={() => goTo("prev")}>
            <Icon icon="zi-chevron-left" style={{ fontSize: 22, color: "var(--color-text-secondary)" }} />
          </Box>
          <Box className="ch-fab ch-fab--primary" style={{ width: 58, height: 58 }} onClick={() => setIsFlipped(!isFlipped)}>
            <Text style={{ fontSize: 24, lineHeight: 1 }}>🔄</Text>
          </Box>
          <Box className="ch-fab" style={{ width: 50, height: 50, background: "var(--color-bg-subtle)", border: "1px solid var(--color-border)" }}
            onClick={shuffleCards}
            title="Xáo trộn thẻ"
          >
            <Text style={{ fontSize: 20, lineHeight: 1 }}>🔀</Text>
          </Box>
          <Box className="ch-fab ch-fab--secondary" style={{ width: 50, height: 50 }} onClick={() => goTo("next")}>
            <Icon icon="zi-chevron-right" style={{ fontSize: 22, color: "var(--color-text-secondary)" }} />
          </Box>
        </Box>
      </Box>
    </Page>
  );
}

export default FlashcardPage;

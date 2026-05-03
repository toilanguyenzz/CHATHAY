import { App, AnimationRoutes, Route, SnackbarProvider, ZMPRouter, BottomNavigation, useNavigate } from "zmp-ui";
import { useLocation, Navigate } from "react-router-dom";
import { useEffect } from "react";

import HomePage from "../pages/index";
import FileProcessingPage from "../pages/file-processing";
import AILearningPage from "../pages/ai-learning";
import FlashcardPage from "../pages/flashcard";
import QuizPage from "../pages/quiz";
import VaultPage from "../pages/vault";
import { useAuth } from "../hooks/useAuth";
import { setApiBase } from "../hooks/useAuth";
import { apiClient } from "../services/api";

/* ─── Bottom Navigation: 2 TAB TÁCH BIỆT RÕ RÀNG ───
   Tab 1: 📄 Xử lý File — Upload, quản lý, công cụ xử lý tài liệu
   Tab 2: 🤖 AI Learning — Flashcard, Quiz, ví Coin, học tập với AI
   ─── */
function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  // Flashcard/Quiz thuộc AI Learning, Vault thuộc File Processing
  const getActiveKey = () => {
    if (["/ai-learning", "/flashcard", "/quiz"].includes(path)) return "/ai-learning";
    return "/file-processing";
  };

  return (
    <BottomNavigation
      fixed
      activeKey={getActiveKey()}
      onChange={(key) => navigate(key)}
    >
      <BottomNavigation.Item
        key="/file-processing"
        label="Xử lý File"
        icon={<span style={{ fontSize: 22, lineHeight: 1 }}>📄</span>}
        activeIcon={<span style={{ fontSize: 24, lineHeight: 1 }}>📂</span>}
      />
      <BottomNavigation.Item
        key="/ai-learning"
        label="AI Learning"
        icon={<span style={{ fontSize: 22, lineHeight: 1 }}>🤖</span>}
        activeIcon={<span style={{ fontSize: 24, lineHeight: 1 }}>🧠</span>}
      />
    </BottomNavigation>
  );
}

const Layout = () => {
  const { loading } = useAuth();

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
    setApiBase(base);
    apiClient.setBaseUrl(base);
  }, []);

  if (loading) {
    return (
      <App theme="light">
        <SnackbarProvider>
          <Box style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
            <Text className="ch-caption">Đang tải...</Text>
          </Box>
        </SnackbarProvider>
      </App>
    );
  }

  return (
    <App theme="light">
      <SnackbarProvider>
        <ZMPRouter>
          <BottomNav />
          <AnimationRoutes>
            {/* TAB 1: XỬ LÝ FILE */}
            <Route path="/" element={<HomePage />} />
            <Route path="/file-processing" element={<FileProcessingPage />} />
            <Route path="/vault" element={<VaultPage />} />

            {/* TAB 2: AI LEARNING */}
            <Route path="/ai-learning" element={<AILearningPage />} />
            <Route path="/flashcard" element={<FlashcardPage />} />
            <Route path="/quiz" element={<QuizPage />} />

            {/* Catch-all: redirect unknown paths (incl /src/index.html) to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </AnimationRoutes>
        </ZMPRouter>
      </SnackbarProvider>
    </App>
  );
};
export default Layout;

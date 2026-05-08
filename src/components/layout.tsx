import { App, AnimationRoutes, Route, SnackbarProvider, ZMPRouter } from "zmp-ui";
import { Navigate } from "react-router-dom";
import { useEffect } from "react";

import HubPage from "../pages/index";
import FileProcessingPage from "../pages/file-processing";
import AILearningPage from "../pages/ai-learning";
import FlashcardPage from "../pages/flashcard";
import QuizPage from "../pages/quiz";
import VaultPage from "../pages/vault";
import { useAuth } from "../hooks/useAuth";
import { setApiBase } from "../hooks/useAuth";
import { apiClient } from "../services/api";
import { useShow } from "zmp-sdk";
import { SharedFileProvider, useSharedFile } from "../contexts/SharedFileContext";

/* ─── Layout: No Bottom Nav — Hub → Sub-pages ─── */
const LayoutContent = () => {
  const { loading, user_id } = useAuth();
  const { setSharedFile } = useSharedFile();

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
    setApiBase(base);
    apiClient.setBaseUrl(base);
  }, []);

  // Set userId on apiClient whenever auth changes
  useEffect(() => {
    if (user_id) {
      apiClient.setUserId(user_id);
    }
  }, [user_id]);

  // Zalo Share Intent: Bắt sự kiện khi user share file từ Zalo chat
  useEffect(() => {
    const handleShow = async () => {
      try {
        // getLaunchOptions() trả về thông tin khi app được mở từ share intent
        const launchOptions = await window.ZMP?.getLaunchOptions?.();
        if (launchOptions?.type === 'open_file' && launchOptions.payload?.file_url) {
          setSharedFile(launchOptions.payload);
        }
      } catch (e) {
        console.log("Zalo share intent not available", e);
      }
    };

    handleShow();
  }, [setSharedFile]);

  if (loading) {
    return (
      <App theme="light">
        <SnackbarProvider>
          <div style={{
            display: "flex", flexDirection: "column",
            justifyContent: "center", alignItems: "center",
            minHeight: "100vh", gap: 16,
            background: "var(--color-bg, #FAF9F7)",
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: 18,
              background: "linear-gradient(135deg, #5B4CDB, #8B5CF6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "white", fontSize: 24, fontWeight: 900,
              animation: "pulseGlow 2s ease-in-out infinite",
            }}>C</div>
            <span style={{
              fontFamily: "Inter, sans-serif",
              fontSize: 13, fontWeight: 600,
              color: "#9E9BB8",
            }}>Đang tải...</span>
          </div>
        </SnackbarProvider>
      </App>
    );
  }

  return (
    <App theme="light">
      <SnackbarProvider>
        <ZMPRouter>
          <AnimationRoutes>
            {/* HUB: Trang điều hướng chính */}
            <Route path="/" element={<HubPage />} />

            {/* KHU VỰC XỬ LÝ FILE */}
            <Route path="/file-processing" element={<FileProcessingPage />} />
            <Route path="/vault" element={<VaultPage />} />

            {/* KHU VỰC AI LEARNING */}
            <Route path="/ai-learning" element={<AILearningPage />} />
            <Route path="/flashcard" element={<FlashcardPage />} />
            <Route path="/quiz" element={<QuizPage />} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </AnimationRoutes>
        </ZMPRouter>
      </SnackbarProvider>
    </App>
  );
};

const Layout = () => {
  return (
    <SharedFileProvider>
      <LayoutContent />
    </SharedFileProvider>
  );
};

export default Layout;

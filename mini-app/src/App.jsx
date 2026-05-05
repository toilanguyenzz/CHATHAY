import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import VaultPage from './pages/VaultPage';
import StudyPage from './pages/StudyPage';
import PremiumPage from './pages/PremiumPage';
import LoginScreen from './components/auth/LoginScreen';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Đang tải...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginScreen />;
  }

  return children;
}

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Layout>
            <HomePage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/upload" element={
        <ProtectedRoute>
          <Layout>
            <UploadPage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/vault" element={
        <ProtectedRoute>
          <Layout>
            <VaultPage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/study" element={
        <ProtectedRoute>
          <Layout>
            <StudyPage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/premium" element={
        <ProtectedRoute>
          <Layout>
            <PremiumPage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
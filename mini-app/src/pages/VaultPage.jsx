import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VaultPage() {
  const navigate = useNavigate();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocs();
  }, []);

  async function loadDocs() {
    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        setLoading(false);
        return;
      }
      const user = JSON.parse(userStr);

      const headers = { 'X-User-Id': user.id };
      const response = await fetch(`${API_BASE_URL}/api/miniapp/documents`, { headers });

      if (response.ok) {
        const data = await response.json();
        setDocs(data);
      }
    } catch (err) {
      console.error('Load docs error:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(docId, docName) {
    if (!confirm(`Xóa "${docName}"? Hành động không thể hoàn tác.`)) return;

    try {
      const userStr = localStorage.getItem('user');
      const user = JSON.parse(userStr);

      const response = await fetch(`${API_BASE_URL}/api/miniapp/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': user.id },
      });

      if (response.ok) {
        setDocs(docs.filter(d => d.id !== docId));
      } else {
        alert('Xóa thất bại 😅');
      }
    } catch (err) {
      alert('Lỗi kết nối');
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="loading-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6 fade-in-up pb-safe">
      {/* Header */}
      <div className="pt-2">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black text-gray-800 mb-1">📚 Kho tài liệu</h1>
            <p className="text-gray-600 font-medium">{docs.length} tài liệu đã lưu</p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="btn btn-primary text-sm py-3 px-5"
          >
            ➕ Tải mới
          </button>
        </div>
      </div>

      {/* Stats */}
      {docs.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="stat-card">
            <div className="text-3xl font-black text-blue-500">{docs.length}</div>
            <div className="text-xs font-medium text-gray-600 mt-1">Tổng cộng</div>
          </div>
          <div className="stat-card">
            <div className="text-3xl font-black text-green-500">
              {docs.reduce((sum, d) => sum + (d.quiz_questions?.length || 0), 0)}
            </div>
            <div className="text-xs font-medium text-gray-600 mt-1">Câu Quiz</div>
          </div>
          <div className="stat-card">
            <div className="text-3xl font-black text-purple-500">
              {docs.reduce((sum, d) => sum + (d.flashcards?.length || 0), 0)}
            </div>
            <div className="text-xs font-medium text-gray-600 mt-1">Flashcards</div>
          </div>
        </div>
      )}

      {/* Documents List */}
      {docs.length === 0 ? (
        <div className="card text-center py-20">
          <div className="text-8xl mb-6">📭</div>
          <h3 className="text-2xl font-bold text-gray-700 mb-3">Kho trống!</h3>
          <p className="text-gray-500 mb-6 font-medium">Hãy tải lên tài liệu đầu tiên</p>
          <button
            onClick={() => navigate('/upload')}
            className="btn btn-primary text-lg py-4 px-8"
          >
            🚀 Tải lên ngay
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {docs.map((doc, idx) => (
            <div
              key={doc.id}
              className="list-item"
              style={{animationDelay: `${idx * 0.1}s`}}
            >
              <div className="flex items-start gap-4 flex-1">
                <div className="text-5xl">
                  {doc.doc_type === 'pdf' ? '📕' :
                   doc.doc_type === 'word' ? '📘' :
                   doc.doc_type === 'image' ? '🖼️' : '📄'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-xl truncate">{doc.filename || doc.name}</div>
                  <div className="text-sm text-gray-500 mt-2 flex flex-wrap gap-2">
                    <span className="bg-gray-100 px-2 py-1 rounded-full text-xs font-medium">
                      {new Date(doc.timestamp || doc.created_at).toLocaleDateString('vi-VN')}
                    </span>
                    <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium">
                      📖 {doc.quiz_questions?.length || 0} Quiz
                    </span>
                    <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded-full text-xs font-medium">
                      🃏 {doc.flashcards?.length || 0} Flashcards
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500 font-medium">Tiến độ học</span>
                      <span className="font-bold text-blue-600">0%</span>
                    </div>
                    <div className="progress-bar h-2">
                      <div className="progress-fill" style={{width: '0%'}}></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 ml-2">
                <button
                  onClick={() => navigate('/study', { state: { docId: doc.id } })}
                  className="btn btn-primary text-sm py-3 px-5"
                >
                  🎯 Học ngay
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(doc.id, doc.filename || doc.name);
                  }}
                  className="w-12 h-12 bg-red-100 text-red-500 rounded-xl hover:bg-red-200 transition-colors flex items-center justify-center text-xl"
                  title="Xóa"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State Hint */}
      {docs.length === 0 && (
        <div className="card bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
          <div className="text-center py-4">
            <p className="text-blue-900 font-medium mb-2">💡 Mẹo:</p>
            <p className="text-sm text-blue-800">
              Upload PDF/DOCX → AI tự động tạo Quiz & Flashcard cho bạn!
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

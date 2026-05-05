import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [docs, setDocs] = useState([]);
  const [coinBalance, setCoinBalance] = useState(0);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        setLoading(false);
        return;
      }
      const userData = JSON.parse(userStr);

      const headers = { 'X-User-Id': userData.id };

      const [docsRes, coinRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/miniapp/documents`, { headers }),
        fetch(`${API_BASE_URL}/api/miniapp/coin/balance`, { headers }),
      ]);

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setDocs(docsData.slice(0, 5));
      }
      if (coinRes.ok) {
        const coinData = await coinRes.json();
        setCoinBalance(coinData.balance || 0);
      }
      // Mock streak for demo
      setStreak(Math.floor(Math.random() * 15) + 1);
    } catch (err) {
      console.error('Load data error:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <p className="mt-4 text-gray-600 font-medium">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6 fade-in-up pb-safe">
      {/* Header với gradient background */}
      <div className="text-center pt-4 pb-6 rounded-b-3xl" style={{
        background: 'linear-gradient(135deg, #58cc02 0%, #1cb0f6 100%)',
        margin: '-1rem -1rem 0 -1rem',
        padding: '2rem 1rem 3rem 1rem'
      }}>
        <h1 className="text-5xl font-black text-white mb-2 bounce-in" style={{
          textShadow: '0 4px 0 rgba(0,0,0,0.2)'
        }}>CHAT HAY</h1>
        <p className="text-white font-bold text-lg" style={{opacity: 0.95}}>Đọc hiểu tài liệu thông minh ✨</p>
      </div>

      {/* Streak Fire - hiệu ứng mạnh */}
      <div className="card text-center py-6 lift-on-hover streak-fire" style={{
        background: 'linear-gradient(135deg, #fff7ed 0%, #fed7aa 50%, #ffedd5 100%)',
        borderColor: '#fb923c',
        borderWidth: '3px'
      }}>
        <div className="text-6xl mb-2" style={{animation: 'streak-fire 1s ease-in-out infinite'}}>🔥</div>
        <div className="text-6xl font-black text-orange-500" style={{
          textShadow: '0 3px 0 #c2410c'
        }}>{streak}</div>
        <div className="text-sm font-black text-orange-600 uppercase tracking-wider mt-1">Ngày streak</div>
        <div className="mt-3 text-xs text-orange-500 font-bold">🔥 Giữ streak để nhận thưởng!</div>
        {/* Streak progress bar */}
        <div className="mt-3 px-4">
          <div className="progress-bar h-3" style={{background: '#fed7aa'}}>
            <div className="progress-fill bg-gradient-to-r" style={{
              width: `${Math.min(streak * 7, 100)}%`,
              background: 'linear-gradient(90deg, #fb923c, #f97316, #ea580c)'
            }}></div>
          </div>
        </div>
      </div>

      {/* Coin Balance - gradient vàng */}
      <div className="card flex justify-between items-center py-4 px-6 lift-on-hover coin-bounce" style={{
        background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fbbf24 100%)',
        borderColor: '#f59e0b',
        borderWidth: '3px'
      }}>
        <div className="flex items-center gap-4">
          <div className="text-3xl" style={{animation: 'coin-bounce 1s ease-in-out infinite'}}>
            💰 <span className="font-black text-yellow-700 text-2xl">{coinBalance}</span>
          </div>
          <div>
            <div className="text-sm font-black text-yellow-800">Số dư ví</div>
            <div className="text-xs text-yellow-600 font-bold">💎 Tích lũy để unlock</div>
          </div>
        </div>
        <button
          onClick={() => navigate('/premium')}
          className="btn text-sm py-2 px-5 bounce-in"
          style={{
            background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
            color: 'white',
            border: 'none',
            boxShadow: '0 4px 0 #9a3412',
            fontWeight: 900
          }}
        >
          ⭐ Nạp thêm
        </button>
      </div>

      {/* Quick Actions - 2 nút to đẹp */}
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={() => navigate('/upload')}
          className="card flex flex-col items-center gap-3 py-8 hover:scale-110 transition-all lift-on-hover bounce-in"
          style={{
            background: 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%)',
            borderColor: '#3b82f6',
            borderWidth: '3px'
          }}
        >
          <span className="text-6xl">📄</span>
          <span className="font-black text-xl text-blue-700">Tải lên</span>
          <span className="text-xs text-blue-600 font-bold">PDF/DOCX/Ảnh</span>
        </button>
        <button
          onClick={() => navigate('/vault')}
          className="card flex flex-col items-center gap-3 py-8 hover:scale-110 transition-all lift-on-hover bounce-in"
          style={{
            background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
            borderColor: '#8b5cf6',
            borderWidth: '3px'
          }}
        >
          <span className="text-6xl">📚</span>
          <span className="font-bold text-xl text-purple-700">Kho tài liệu</span>
          <span className="text-xs text-purple-600 font-bold">{docs.length} tài liệu</span>
        </button>
      </div>

      {/* Progress Today - shimmer effect */}
      <div className="card shimmer" style={{
        background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
        borderColor: '#10b981',
        borderWidth: '3px'
      }}>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-black text-lg text-green-800">📈 Tiến độ hôm nay</h3>
          <span className="text-sm font-black text-green-600 bg-green-200 px-3 py-1 rounded-full">Đang active 🟢</span>
        </div>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-bold text-green-700">📄 Tài liệu đã xử lý</span>
              <span className="font-black text-blue-600">{docs.length} / 5</span>
            </div>
            <div className="progress-bar h-4" style={{background: '#a7f3d0'}}>
              <div className="progress-fill" style={{
                width: `${Math.min(docs.length * 20, 100)}%`,
                background: 'linear-gradient(90deg, #58cc02, #1cb0f6)'
              }}></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-bold text-green-700">💰 Coin đã kiếm được</span>
              <span className="font-black text-yellow-600">{coinBalance} / 100</span>
            </div>
            <div className="progress-bar h-4" style={{background: '#fde68a'}}>
              <div className="progress-fill" style={{
                width: `${Math.min(coinBalance, 100)}%`,
                background: 'linear-gradient(90deg, #fbbf24, #f97316)'
              }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Documents */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-black text-gray-800">📑 Tài liệu gần đây</h2>
          {docs.length > 0 && (
            <button
              onClick={() => navigate('/vault')}
              className="text-sm font-black text-blue-500 hover:text-blue-600 bg-blue-50 px-3 py-1 rounded-full"
            >
              Xem tất cả →
            </button>
          )}
        </div>

        {docs.length === 0 ? (
          <div className="card text-center py-16 lift-on-hover" style={{
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
            borderColor: '#fbbf24',
            borderWidth: '3px'
          }}>
            <div className="text-8xl mb-4 wiggle">📭</div>
            <p className="text-gray-700 font-bold mb-2 text-lg">Chưa có tài liệu nào</p>
            <p className="text-gray-600 text-sm mb-6">Hãy tải lên tài liệu đầu tiên nào! 🚀</p>
            <button
              onClick={() => navigate('/upload')}
              className="btn text-lg py-4 px-8 bounce-in"
              style={{
                background: 'linear-gradient(135deg, #58cc02 0%, #46a703 100%)',
                color: 'white',
                border: 'none',
                boxShadow: '0 6px 0 #3d8b02, 0 8px 20px rgba(88, 204, 2, 0.3)',
                fontWeight: 900
              }}
            >
              🚀 Tải lên ngay
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {docs.map((doc, idx) => (
              <div
                key={doc.id || idx}
                onClick={() => navigate('/study', { state: { docId: doc.id } })}
                className="list-item flex justify-between items-center lift-on-hover bounce-in"
                style={{
                  animationDelay: `${idx * 0.1}s`,
                  borderColor: '#1cb0f6',
                  borderWidth: '3px',
                  background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)'
                }}
              >
                <div className="flex-1">
                  <div className="font-black text-lg truncate text-blue-900">{doc.filename || doc.name}</div>
                  <div className="text-xs text-gray-500 mt-1 flex gap-2">
                    <span className="badge badge-general">{doc.doc_type || 'FILE'}</span>
                    <span className="bg-gray-100 px-2 py-1 rounded-full font-medium">{new Date(doc.timestamp || doc.created_at).toLocaleDateString('vi-VN')}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-center bg-blue-50 px-3 py-2 rounded-xl">
                    <div className="text-sm font-black text-blue-600">Quiz</div>
                    <div className="text-xs text-blue-500">Ready ✓</div>
                  </div>
                  <span className="text-4xl">📖</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Stats - 3 card gradient */}
      <div className="grid grid-cols-3 gap-3">
        <div className="stat-card bounce-in">
          <div className="text-4xl font-black text-blue-600">{docs.length}</div>
          <div className="text-xs font-black text-blue-500 mt-1 uppercase">Tài liệu</div>
        </div>
        <div className="stat-card bounce-in" style={{animationDelay: '0.1s'}}>
          <div className="text-4xl font-black text-orange-500">{streak}</div>
          <div className="text-xs font-black text-orange-500 mt-1 uppercase">Streak</div>
        </div>
        <div className="stat-card bounce-in" style={{animationDelay: '0.2s'}}>
          <div className="text-4xl font-black text-yellow-500">{coinBalance}</div>
          <div className="text-xs font-black text-yellow-500 mt-1 uppercase">Coin</div>
        </div>
      </div>
    </div>
  );
}

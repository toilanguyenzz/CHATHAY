import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function PremiumPage() {
  const navigate = useNavigate();
  const [coinBalance, setCoinBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadBalance();
  }, []);

  async function loadBalance() {
    try {
      const token = localStorage.getItem('mini_app_token');
      const response = await fetch(`${API_BASE_URL}/api/miniapp/coin/balance`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setCoinBalance(data.balance || 0);
      }
    } catch (err) {
      console.error('Load balance error:', err);
    }
  }

  const handleTopup = async (packageId) => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('mini_app_token');
      const response = await fetch(`${API_BASE_URL}/api/miniapp/zalopay/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ package_id: packageId }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Tạo đơn hàng thất bại');
      }

      const data = await response.json();

      // Redirect to ZaloPay payment page
      if (data.payment_url) {
        window.location.href = data.payment_url;
      } else if (data.zp_trans_token) {
        // Use ZaloPay SDK if available
        alert('Chuyển đến ZaloPay...');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const coinPackages = [
    { id: 'trial', name: 'Gói Thử', price: 5000, coins: 50, bonus: 0, desc: '5 lần xử lý file' },
    { id: 'save', name: 'Gói Tiết Kiệm', price: 15000, coins: 180, bonus: 20, desc: '1 ly trà sữa' },
    { id: 'vip_week', name: 'Gói VIP Tuần', price: 35000, coins: 500, bonus: 40, desc: '1 bữa cơm trưa' },
  ];

  const proPackages = [
    { id: 'student', name: 'Student', price: 29000, period: '/tháng', features: ['20 file/ngày', 'Quiz không giới hạn', 'PDF Viewer'] },
    { id: 'pro', name: 'Pro', price: 69000, period: '/tháng', features: ['Unlimited', 'Export Anki', 'Thi thử', 'Quản lý thư mục'] },
  ];

  return (
    <div className="p-4 space-y-6 fade-in-up pb-safe">
      {/* Header gradient */}
      <div className="pt-2 pb-4">
        <button onClick={() => navigate('/')} className="text-yellow-600 font-black text-sm hover:scale-105 transition-transform mb-2">
          ← Quay lại
        </button>
        <h1 className="text-4xl font-black mb-2 bounce-in" style={{
          background: 'linear-gradient(135deg, #fbbf24 0%, #f97316 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>💎 Nạp Coin & Gói Pro</h1>
        <p className="text-gray-700 font-bold text-lg">Sử dụng Coin để mở khóa tính năng</p>
      </div>

      {/* Current Balance - gradient vàng */}
      <div className="card lift-on-hover coin-bounce" style={{
        background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fbbf24 100%)',
        borderColor: '#f59e0b',
        borderWidth: '3px'
      }}>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="text-4xl">💰</div>
            <div>
              <div className="font-black text-2xl text-yellow-800">{coinBalance}</div>
              <div className="text-sm text-yellow-700 font-bold">Số dư hiện tại</div>
            </div>
          </div>
          <div className="text-right bg-yellow-200 px-3 py-2 rounded-xl">
            <div className="text-xs text-yellow-700 font-bold">Đã dùng</div>
            <div className="font-black text-yellow-800">0 Coin</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="card fade-in-up" style={{
          background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
          borderColor: '#ef4444',
          borderWidth: '3px'
        }}>
          <div className="flex items-center gap-3 text-red-700 font-black">
            <span className="text-3xl">❌</span>
            <span>{error}</span>
          </div>
        </div>
      )}
      {success && (
        <div className="card fade-in-up shimmer" style={{
          background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
          borderColor: '#22c55e',
          borderWidth: '3px'
        }}>
          <div className="flex items-center gap-3 text-green-700 font-black">
            <span className="text-3xl">✅</span>
            <span>{success}</span>
          </div>
        </div>
      )}

      {/* Coin Packages - gradient đẹp */}
      <div>
        <h2 className="text-2xl font-black mb-4 flex items-center gap-2">
          <span className="text-3xl">💰</span>
          <span className="bg-gradient-to-r from-yellow-600 to-orange-600 bg-clip-text text-transparent">Nạp Coin</span>
        </h2>
        <div className="space-y-4">
          {coinPackages.map((pkg, idx) => (
            <div key={pkg.id} className="card lift-on-hover bounce-in" style={{
              background: pkg.id === 'save'
                ? 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%)'
                : pkg.id === 'vip_week'
                ? 'linear-gradient(135deg, #faf5ff 0%, #e9d5ff 100%)'
                : 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              borderColor: pkg.id === 'save'
                ? '#3b82f6'
                : pkg.id === 'vip_week'
                ? '#a855f7'
                : '#fbbf24',
              borderWidth: '3px',
              animationDelay: `${idx * 0.1}s`
            }}>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="font-black text-xl text-gray-800">{pkg.name}</div>
                  <div className="text-sm text-gray-600 font-bold mt-1">{pkg.desc}</div>
                </div>
                <div className="text-right bg-white bg-opacity-70 px-3 py-2 rounded-xl">
                  <div className="text-3xl font-black text-yellow-600">{pkg.coins + pkg.bonus}</div>
                  <div className="text-xs text-gray-500 font-bold">Coin (bonus)</div>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-2xl font-black text-gray-800">{pkg.price.toLocaleString()}đ</span>
                  {pkg.bonus > 0 && (
                    <span className="ml-2 bg-green-500 text-white text-xs px-3 py-1 rounded-full font-black">
                      +{pkg.bonus} bonus 🎉
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleTopup(pkg.id)}
                  disabled={loading}
                  className="px-6 py-3 rounded-2xl font-black text-white text-lg hover:scale-105 transition-transform disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                    border: 'none',
                    boxShadow: '0 4px 0 #9a3412',
                    fontWeight: 900
                  }}
                >
                  {loading ? 'Đang xử lý...' : '🛒 Nạp ngay'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pro Packages - gradient tím xanh */}
      <div>
        <h2 className="text-2xl font-black mb-4 flex items-center gap-2">
          <span className="text-3xl">💎</span>
          <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Gói Pro</span>
        </h2>
        <div className="space-y-4">
          {proPackages.map((pkg, idx) => (
            <div key={pkg.id} className="card lift-on-hover bounce-in" style={{
              background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
              borderColor: '#7c3aed',
              borderWidth: '3px',
              animationDelay: `${idx * 0.1}s`
            }}>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="font-black text-2xl text-white">{pkg.name}</div>
                  <div className="text-4xl font-black text-white mt-2">
                    {pkg.price.toLocaleString()}đ<span className="text-lg font-normal text-purple-200">{pkg.period}</span>
                  </div>
                </div>
                <div className="bg-white bg-opacity-20 px-4 py-2 rounded-full text-sm text-white font-black">
                  Phổ biến 🔥
                </div>
              </div>
              <div className="space-y-3 mb-4">
                {pkg.features.map((feature, fidx) => (
                  <div key={fidx} className="flex items-center gap-3 text-white font-bold">
                    <span className="text-green-300 text-xl">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => alert('Chuyển đến trang thanh toán Web App chathay.vn')}
                className="w-full py-4 rounded-2xl font-black text-lg hover:scale-105 transition-transform"
                style={{
                  background: 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
                  color: '#7c3aed',
                  border: 'none',
                  boxShadow: '0 4px 0 #e0e7ff',
                  fontWeight: 900
                }}
              >
                🚀 Nâng cấp ngay
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Info Box - gradient xanh */}
      <div className="card lift-on-hover" style={{
        background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
        borderColor: '#3b82f6',
        borderWidth: '3px'
      }}>
        <h3 className="font-black text-blue-900 mb-3 text-lg flex items-center gap-2">
          <span className="text-2xl">💡</span>
          Tại sao chọn Coin?
        </h3>
        <ul className="text-sm text-blue-800 space-y-2 font-bold">
          <li className="flex items-start gap-2">
            <span className="text-green-600">✓</span>
            <span>Sinh viên không có nhiều tiền → 5,000đ ai cũng sẵn sàng</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600">✓</span>
            <span>ZaloPay 1 chạm → Thanh toán trong 3 giây</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600">✓</span>
            <span>Hiệu ứng "chỉ bằng 1 ly trà sữa"</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function LoginScreen() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleZaloLogin = () => {
    setLoading(true);
    // Simulate login with mock user data (no real SDK dependency)
    setTimeout(() => {
      localStorage.setItem('user', JSON.stringify({
        id: 'zalo_' + Date.now(),
        name: 'User Test',
        avatar: '',
      }));
      setLoading(false);
      navigate('/');
    }, 1000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-sm w-full text-center">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">CHAT HAY</h1>
          <p className="text-gray-600">Đọc hiểu tài liệu thông minh</p>
        </div>

        <button
          onClick={handleZaloLogin}
          disabled={loading}
          className="btn btn-primary min-w-full"
        >
          {loading ? 'Đang đăng nhập...' : 'Đăng nhập với Zalo'}
        </button>

        <p className="mt-4 text-sm text-gray-500">
          Bằng việc đăng nhập, bạn đồng ý với điều khoản sử dụng
        </p>
      </div>
    </div>
  );
}

export default LoginScreen;
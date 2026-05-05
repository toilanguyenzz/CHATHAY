import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    const allowed = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/png',
      'image/jpeg'
    ];
    if (!allowed.includes(selected.type)) {
      setError('Chỉ hỗ trợ PDF, DOCX, PNG, JPG 😅');
      return;
    }

    if (selected.size > 20 * 1024 * 1024) {
      setError('File quá lớn! Tối đa 20MB 📦');
      return;
    }

    setFile(selected);
    setError('');
    setProgress(0);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      const event = { target: { files: [dropped] } };
      handleFileChange(event);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Vui lòng chọn file trước 📎');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');
    setProgress(0);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + 10, 90));
    }, 300);

    try {
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        throw new Error('Vui lòng đăng nhập trước khi tải tài liệu 👤');
      }
      const user = JSON.parse(userStr);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/api/miniapp/documents`, {
        method: 'POST',
        headers: {
          'X-User-Id': user.id,
        },
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload thất bại ❌');
      }

      const data = await response.json();
      setSuccess('Tải lên thành công! 🎉 AI đang xử lý...');

      setTimeout(() => {
        navigate('/study', { state: { docId: data.id } });
      }, 1500);
    } catch (err) {
      clearInterval(progressInterval);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-4 space-y-6 fade-in-up pb-safe">
      {/* Header gradient */}
      <div className="text-center pt-2 pb-4">
        <h1 className="text-4xl font-black mb-2 bounce-in" style={{
          background: 'linear-gradient(135deg, #1cb0f6 0%, #58cc02 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>📄 Tải tài liệu</h1>
        <p className="text-gray-700 font-bold text-lg">PDF, DOCX, PNG, JPG (≤20MB)</p>
      </div>

      {/* Upload Area - gradient đẹp */}
      <div
        className={`upload-area bounce-in ${isDragging ? 'dragging' : ''}`}
        style={{
          background: isDragging
            ? 'linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%)'
            : 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)',
          borderColor: isDragging ? '#3b82f6' : '#cbd5e1',
          borderWidth: isDragging ? '4px' : '4px',
          transform: isDragging ? 'scale(1.02)' : 'scale(1)',
          transition: 'all 300ms'
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.png,.jpg,.jpeg"
          onChange={handleFileChange}
          disabled={uploading}
        />
        <div className="text-8xl mb-4" style={{animation: isDragging ? 'wiggle 0.5s ease-in-out' : 'none'}}>📁</div>
        <p className="text-2xl font-black text-gray-700 mb-2">
          {isDragging ? '🎯 Thả file vào đây!' : '📂 Nhấn để chọn file'}
        </p>
        <p className="text-sm text-gray-500 font-bold">hoặc kéo thả file vào đây</p>
      </div>

      {/* Progress Bar - gradient xanh */}
      {uploading && (
        <div className="card fade-in-up" style={{
          background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
          borderColor: '#3b82f6',
          borderWidth: '3px'
        }}>
          <div className="flex justify-between text-sm mb-2">
            <span className="font-black text-blue-800">🤖 AI đang xử lý...</span>
            <span className="font-black text-blue-600">{progress}%</span>
          </div>
          <div className="progress-bar h-4" style={{background: '#93c5fd'}}>
            <div className="progress-fill" style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #1cb0f6, #58cc02)',
              boxShadow: '0 0 10px rgba(28, 176, 246, 0.5)'
            }}></div>
          </div>
          <p className="text-xs text-blue-700 mt-2 text-center font-bold">
            ✨ AI đang tóm tắt và tạo Quiz/Flashcard...
          </p>
        </div>
      )}

      {/* File Preview - gradient theo loại file */}
      {file && !uploading && (
        <div className="card lift-on-hover bounce-in" style={{
          background: file.type.includes('pdf')
            ? 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)'
            : file.type.includes('word') || file.name.endsWith('.docx')
            ? 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)'
            : 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)',
          borderColor: file.type.includes('pdf')
            ? '#ef4444'
            : file.type.includes('word') || file.name.endsWith('.docx')
            ? '#3b82f6'
            : '#10b981',
          borderWidth: '3px'
        }}>
          <div className="flex items-center gap-4">
            <div className="text-6xl">
              {file.type.includes('pdf') ? '📕' :
               file.type.includes('word') || file.name.endsWith('.docx') ? '📘' :
               '🖼️'}
            </div>
            <div className="flex-1">
              <div className="font-black text-lg truncate text-gray-800">{file.name}</div>
              <div className="text-sm text-gray-600 font-bold mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB • Ready!
              </div>
              <div className="mt-2">
                <span className="badge badge-education text-sm">✓ Sẵn sàng</span>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="w-12 h-12 bg-red-100 text-red-500 rounded-xl hover:bg-red-200 transition-colors flex items-center justify-center text-2xl font-black"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Error/Success */}
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

      {/* Upload Button - gradient xanh lá */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="btn text-lg py-5 bounce-in disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          background: 'linear-gradient(135deg, #58cc02 0%, #46a703 100%)',
          color: 'white',
          border: 'none',
          boxShadow: '0 6px 0 #3d8b02, 0 8px 20px rgba(88, 204, 2, 0.3)',
          fontWeight: 900,
          fontSize: '1.25rem'
        }}
      >
        {uploading ? (
          <>
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
            Đang xử lý...
          </>
        ) : (
          <>
            <span className="text-2xl">🚀</span>
            Tải lên & Xử lý ngay
          </>
        )}
      </button>

      {/* Info Box - gradient tím */}
      <div className="card lift-on-hover bounce-in" style={{
        background: 'linear-gradient(135deg, #faf5ff 0%, #e9d5ff 100%)',
        borderColor: '#a855f7',
        borderWidth: '3px'
      }}>
        <h3 className="font-black text-purple-900 mb-3 flex items-center gap-2 text-lg">
          <span className="text-3xl">💡</span>
          Bạn biết chưa?
        </h3>
        <ul className="space-y-2 text-sm text-purple-800 font-bold">
          <li className="flex items-start gap-2">
            <span className="text-green-600 text-lg">✓</span>
            <span>AI sẽ tóm tắt nội dung trong 15 giây ⚡</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 text-lg">✓</span>
            <span>Tự động tạo 10 câu Quiz trắc nghiệm 📝</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 text-lg">✓</span>
            <span>Tạo Flashcard để ôn tập hiệu quả 🃏</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 text-lg">✓</span>
            <span>Hoàn thành Quiz/Flashcard nhận Coin 💰</span>
          </li>
        </ul>
      </div>

      {/* Tips - gradient vàng */}
      <div className="card shimmer text-center bounce-in" style={{
        background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fbbf24 100%)',
        borderColor: '#f59e0b',
        borderWidth: '3px'
      }}>
        <div className="text-4xl font-black text-yellow-700 mb-2">🎯</div>
        <h4 className="font-black text-yellow-900 mb-2 text-lg">Mẹo hay</h4>
        <p className="text-sm text-yellow-800 font-bold">
          File chất lượng cao → AI xử lý nhanh hơn và Quiz chất lượng tốt hơn! 🚀
        </p>
      </div>
    </div>
  );
}

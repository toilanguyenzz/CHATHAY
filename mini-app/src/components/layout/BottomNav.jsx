import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Trang chủ', icon: '🏠' },
  { path: '/vault', label: 'Tài liệu', icon: '📚' },
  { path: '/upload', label: 'Tải lên', icon: '⬆️' },
  { path: '/premium', label: 'Premium', icon: '⭐' },
];

function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 pb-safe-bottom">
      <div className="max-w-lg mx-auto flex justify-around items-center h-16">
        {navItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center flex-1 h-full text-xs ${
                isActive ? 'text-blue-600 font-semibold' : 'text-gray-500'
              }`
            }
          >
            <span className="text-xl mb-1">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export default BottomNav;

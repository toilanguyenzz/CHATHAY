import { Outlet } from 'react-router-dom';
import BottomNav from './BottomNav';

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <main className="max-w-lg mx-auto px-4 py-6">
        {children || <Outlet />}
      </main>
      <BottomNav />
    </div>
  );
}

export default Layout;

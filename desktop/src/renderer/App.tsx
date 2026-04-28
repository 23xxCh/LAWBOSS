import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './components/MainLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import CheckPage from './pages/CheckPage';
import BatchCheckPage from './pages/BatchCheckPage';
import ReportsPage from './pages/ReportsPage';
import ReportDetailPage from './pages/ReportDetailPage';
import RulesPage from './pages/RulesPage';
import DashboardPage from './pages/DashboardPage';
import { useAuth } from './api/auth';
import { Spin } from 'antd';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth();
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
        <HashRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<Navigate to="/check" replace />} />
          <Route path="/check" element={<ProtectedRoute><MainLayout><CheckPage /></MainLayout></ProtectedRoute>} />
          <Route path="/batch" element={<ProtectedRoute><MainLayout><BatchCheckPage /></MainLayout></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><MainLayout><ReportsPage /></MainLayout></ProtectedRoute>} />
          <Route path="/reports/:id" element={<ProtectedRoute><MainLayout><ReportDetailPage /></MainLayout></ProtectedRoute>} />
          <Route path="/rules" element={<ProtectedRoute><MainLayout><RulesPage /></MainLayout></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><MainLayout><DashboardPage /></MainLayout></ProtectedRoute>} />
        </Routes>
      </HashRouter>
    </ConfigProvider>
  );
}

export default App;

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import CompetitorsPage from './pages/CompetitorsPage';
import AdminRulesPage from './pages/AdminRulesPage';
import PricingPage from './pages/PricingPage';
import BillingPage from './pages/BillingPage';
import { useAuth } from './api/auth';
import { Spin } from 'antd';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth();
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn, user } = useAuth();
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
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
          <Route path="/competitors" element={<ProtectedRoute><MainLayout><CompetitorsPage /></MainLayout></ProtectedRoute>} />
          <Route path="/pricing" element={<ProtectedRoute><MainLayout><PricingPage /></MainLayout></ProtectedRoute>} />
          <Route path="/billing" element={<ProtectedRoute><MainLayout><BillingPage /></MainLayout></ProtectedRoute>} />
          <Route path="/admin/rules" element={<AdminRoute><MainLayout><AdminRulesPage /></MainLayout></AdminRoute>} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

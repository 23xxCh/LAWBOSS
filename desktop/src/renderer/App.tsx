import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import MainLayout from './components/MainLayout';
import ErrorBoundary from './components/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HomePage from './pages/HomePage';
import CheckPage from './pages/CheckPage';
import BatchCheckPage from './pages/BatchCheckPage';
import ReportsPage from './pages/ReportsPage';
import ReportDetailPage from './pages/ReportDetailPage';
import RulesPage from './pages/RulesPage';
import DashboardPage from './pages/DashboardPage';
import PreferencesPage from './pages/PreferencesPage';
import CompetitorsPage from './pages/CompetitorsPage';
import { useAuth } from './api/auth';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth();
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <HashRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<MainLayout><HomePage /></MainLayout>} />
          <Route path="/check" element={<ProtectedRoute><MainLayout><ErrorBoundary><CheckPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/batch" element={<ProtectedRoute><MainLayout><ErrorBoundary><BatchCheckPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><MainLayout><ErrorBoundary><ReportsPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/reports/:id" element={<ProtectedRoute><MainLayout><ErrorBoundary><ReportDetailPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/rules" element={<ProtectedRoute><MainLayout><ErrorBoundary><RulesPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><MainLayout><ErrorBoundary><DashboardPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/preferences" element={<ProtectedRoute><MainLayout><ErrorBoundary><PreferencesPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
          <Route path="/competitors" element={<ProtectedRoute><MainLayout><ErrorBoundary><CompetitorsPage /></ErrorBoundary></MainLayout></ProtectedRoute>} />
        </Routes>
      </HashRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;

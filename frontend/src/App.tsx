import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import ColdStartLoader from './components/loading/ColdStartLoader';
import AppShell from './components/layout/AppShell';
import AlertBanner from './components/ui/AlertBanner';
import Button from './components/ui/Button';
import LoginPage from './pages/Login';
import HomePage from './pages/Home';
import DashboardPage from './pages/Dashboard';
import ChecklistPage from './pages/Checklist';
import SettingsPage from './pages/Settings';
import CategoriesPage from './pages/Categories';

export default function App() {
  const auth = useAuth();

  if (auth.isLoading) return <ColdStartLoader />;

  if (auth.error) {
    return (
      <div className="page">
        <AlertBanner kind="error">Could not reach the server. It may still be waking up.</AlertBanner>
        <Button onClick={() => auth.refetch()}>Try again</Button>
      </div>
    );
  }

  if (!auth.isAuthenticated || !auth.player || !auth.premium) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter>
      <AppShell player={auth.player} premium={auth.premium}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/checklist" element={<ChecklistPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

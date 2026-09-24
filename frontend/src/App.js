import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider, useAuth } from './lib/auth';
import Shell from './components/Shell';
import Landing from './pages/Landing';
import Access from './pages/Access';
import CreateSociety from './pages/CreateSociety';
import Dashboard from './pages/Dashboard';
import ProblemDetail from './pages/ProblemDetail';
import ReportProblem from './pages/ReportProblem';
import Community from './pages/Community';
import Settings from './pages/Settings';
import AdminManagement from './pages/AdminManagement';
import Profile from './pages/Profile';
import Notifications from './pages/Notifications';
import Analytics from './pages/Analytics';
import MapPage from './pages/MapPage';
import './App.css';
import './readability.css';

function Protected({ roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot-screen" data-testid="app-loading"><span className="pulse-logo">C</span><p>Connecting to your community…</p></div>;
  if (!user) return <Navigate to="/enter" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/app" replace />;
  return <Outlet />;
}
export default function App() {
  return <BrowserRouter><AuthProvider><Toaster richColors position="top-right" closeButton /><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/enter" element={<Access />} /><Route path="/register" element={<Access register />} />
    <Route path="/create" element={<CreateSociety />} />
    <Route element={<Protected />}><Route path="/app" element={<Shell />}>
      <Route index element={<Dashboard />} /><Route path="problems" element={<Dashboard mode="problems" />} />
      <Route path="my-reports" element={<Dashboard mode="mine" />} /><Route path="following" element={<Dashboard mode="following" />} />
      <Route path="report" element={<ReportProblem />} /><Route path="problems/:id" element={<ProblemDetail />} />
      <Route path="community" element={<Community />} /><Route path="profile" element={<Profile />} />
      <Route path="notifications" element={<Notifications />} /><Route path="map" element={<MapPage />} />
      <Route element={<Protected roles={['admin','initial_admin']} />}><Route path="requests" element={<Dashboard mode="requests" />} /><Route path="analytics" element={<Analytics />} /></Route>
      <Route element={<Protected roles={['initial_admin']} />}><Route path="settings" element={<Settings />} /><Route path="admins" element={<AdminManagement />} /></Route>
    </Route></Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AuthProvider></BrowserRouter>;
}
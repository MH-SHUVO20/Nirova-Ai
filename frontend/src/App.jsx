import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import GlobalChatWidget from './components/GlobalChatWidget'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import SymptomsPage from './pages/SymptomsPage'
import DenguePage from './pages/DenguePage'
import ChatPage from './pages/ChatPage'
import SkinPage from './pages/SkinPage'
import LabReportPage from './pages/LabReportPage'
import PrescriptionPage from './pages/PrescriptionPage'
import TimelinePage from './pages/TimelinePage'

// Protect routes - redirect to login if not authenticated
function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  return children
}

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-2 border-primary-500/30 border-t-primary-500 animate-spin" />
        <p className="text-slate-400 font-body">Loading NirovaAI...</p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes - inside the dashboard layout */}
        <Route
          path="/app"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="symptoms" element={<SymptomsPage />} />
          <Route path="dengue" element={<DenguePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="skin" element={<SkinPage />} />
          <Route path="lab-report" element={<LabReportPage />} />
          <Route path="prescription" element={<PrescriptionPage />} />
          <Route path="timeline" element={<TimelinePage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <GlobalChatWidget />
    </>
  )
}

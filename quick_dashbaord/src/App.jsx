import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import ProtectedRoute from '@/components/ui/ProtectedRoute'
import Dashboard from '@/pages/Dashboard'
import FilesList from '@/pages/FilesList'
import DocHistory from '@/pages/DocHistory'
import LinkSharing from '@/pages/LinkSharing'
import Activity from '@/pages/Activity'
import Settings from '@/pages/Settings'
import Login from '@/pages/Login'
import ResetPassword from '@/pages/ResetPassword'
import OfflineBanner from '@/components/ui/OfflineBanner'

export default function App() {
  return (
    <>
      <OfflineBanner />
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/files" element={<FilesList />} />
                  <Route path="/doc-history" element={<DocHistory />} />
                  <Route path="/link-sharing" element={<LinkSharing />} />
                  <Route path="/activity" element={<Activity />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  )
}

import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import ProtectedRoute from '@/components/ui/ProtectedRoute'
import LoginToken from '@/pages/LoginToken'
import TicketList from '@/pages/TicketList'
import TicketDetail from '@/pages/TicketDetail'
import TicketCreate from '@/pages/TicketCreate'
import Settings from '@/pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginToken />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Navigate to="/tickets" replace />} />
                <Route path="/tickets" element={<TicketList />} />
                <Route path="/tickets/new" element={<TicketCreate />} />
                <Route path="/tickets/:id" element={<TicketDetail />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

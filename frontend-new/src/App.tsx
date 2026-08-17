import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from '@/pages/landing/Landing'
import PositionList from '@/pages/public/PositionList'
import PositionDetail from '@/pages/public/PositionDetail'
import Chat from '@/pages/public/Chat'
import Apply from '@/pages/public/Apply'
import AdminLogin from '@/pages/admin/Login'
import AdminPositions from '@/pages/admin/Positions'
import AdminApplicants from '@/pages/admin/Applicants'
import AdminApplicantDetail from '@/pages/admin/ApplicantDetail'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('admin_token')
  if (!token) return <Navigate to="/admin/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />

        <Route path="/:slug" element={<PositionList />} />
        <Route path="/:slug/:positionId" element={<PositionDetail />} />
        <Route path="/:slug/:positionId/chat" element={<Chat />} />
        <Route path="/:slug/:positionId/apply" element={<Apply />} />

        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/positions" element={<RequireAuth><AdminPositions /></RequireAuth>} />
        <Route path="/admin/applicants" element={<RequireAuth><AdminApplicants /></RequireAuth>} />
        <Route path="/admin/applicants/:id" element={<RequireAuth><AdminApplicantDetail /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  )
}

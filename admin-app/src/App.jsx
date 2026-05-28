import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import AdminLayout from './components/layout/AdminLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Contacts from './pages/Contacts'
import Campaigns from './pages/Campaigns'
import ContentStudio from './pages/ContentStudio'
import Approvals from './pages/Approvals'
import Leads from './pages/Leads'
import AgentLogs from './pages/AgentLogs'
import Settings from './pages/Settings'

function Protected({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><AdminLayout /></Protected>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"     element={<Dashboard />} />
        <Route path="leads"         element={<Leads />} />
        <Route path="contacts"      element={<Contacts />} />
        <Route path="campaigns"     element={<Campaigns />} />
        <Route path="products"      element={<Products />} />
        <Route path="content"       element={<ContentStudio />} />
        <Route path="approvals"     element={<Approvals />} />
        <Route path="agent"         element={<AgentLogs />} />
        <Route path="settings"      element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

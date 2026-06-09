import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  LayoutDashboard, Users, FileText, Megaphone,
  Package, Sparkles, CheckSquare, Bot,
  Settings, LogOut, Bell, TrendingUp, Home as HomeIcon, BadgeDollarSign,
  Send, PhoneCall, BarChart3, QrCode,
} from 'lucide-react'

const NAV = [
  { path: '/dashboard',    label: 'Dashboard',      icon: LayoutDashboard },
  { path: '/leads',        label: 'Leads',          icon: Bell },
  { path: '/call-queue',   label: 'Call Queue',     icon: PhoneCall },
  { path: '/outreach',     label: 'Outreach',       icon: Send },
  { path: '/analytics',   label: 'Performance',    icon: BarChart3 },
  { path: '/rates',        label: 'Rate Snapshot',  icon: TrendingUp },
  { path: '/hub-listings', label: 'Listings',       icon: HomeIcon },
  { path: '/dpa-programs', label: 'DPA Programs',   icon: BadgeDollarSign },
  { path: '/contacts',     label: 'Contacts',       icon: Users },
  { path: '/campaigns',    label: 'Campaigns',      icon: Megaphone },
  { path: '/products',     label: 'Products',       icon: Package },
  { path: '/content',      label: 'Content Studio', icon: Sparkles },
  { path: '/approvals',    label: 'Approvals',      icon: CheckSquare },
  { path: '/qr-codes',     label: 'QR Codes',       icon: QrCode },
  { path: '/agent',        label: 'Agent Logs',     icon: Bot },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="sidebar">
      {/* Electron titlebar spacer */}
      {window.electron?.isElectron && <div style={{ height: '28px', flexShrink: 0 }} />}

      {/* Logo */}
      <div style={{ padding: '20px 20px 12px', borderBottom: '1px solid var(--color-carbon-border)' }}>
        <span style={{ fontWeight: 900, fontSize: '1.05rem', letterSpacing: '-0.3px', color: 'var(--color-paper)' }}>
          Mortgage<span style={{ color: 'var(--color-warm)' }}>Sesame</span>
        </span>
        <p style={{ margin: '4px 0 0', fontSize: '0.7rem', color: '#555' }}>Command Center</p>
      </div>

      {/* Nav links */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
        {NAV.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
          >
            <Icon size={15} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>

      {/* Bottom */}
      <div style={{ borderTop: '1px solid var(--color-carbon-border)', padding: '10px 0 8px' }}>
        <NavLink to="/settings" className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}>
          <Settings size={15} />
          <span>Settings</span>
        </NavLink>
        <div style={{ padding: '6px 16px 4px' }}>
          <div style={{ fontSize: '0.7rem', color: '#555', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.full_name || user?.email}
          </div>
        </div>
        <button onClick={handleLogout} className="sidebar-item" style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', color: '#666' }}>
          <LogOut size={14} />
          <span>Sign Out</span>
        </button>
      </div>
    </nav>
  )
}

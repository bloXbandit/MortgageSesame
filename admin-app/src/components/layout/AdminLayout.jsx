import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AdminLayout() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{
        flex: 1, overflow: 'auto',
        background: 'var(--color-carbon)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* macOS Electron titlebar spacer */}
        {window.electron?.isElectron && (
          <div className="titlebar-drag" style={{ flexShrink: 0 }} />
        )}
        <div style={{ flex: 1, padding: '28px 32px', overflow: 'auto' }}>
          <Outlet />
        </div>
      </main>
    </div>
  )
}

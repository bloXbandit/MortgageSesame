import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api, setApiUrl, getApiUrl } from '../utils/api'
import { Wifi, Server, User, Smartphone, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Settings() {
  const { user } = useAuth()
  const [serverUrl, setServerUrlState] = useState(getApiUrl())
  const [testStatus, setTestStatus] = useState(null)
  const [profile, setProfile] = useState({
    full_name: user?.full_name || '',
    nmls_id: user?.nmls_id || '',
    company_name: user?.company_name || '',
    calendly_link: user?.calendly_link || '',
    brand_voice: user?.brand_voice || '',
  })

  const testConnection = async () => {
    setTestStatus('testing')
    try {
      const baseUrl = serverUrl.replace('/api/v1', '')
      const res = await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        setTestStatus('ok')
        toast.success('Backend connected!')
      } else {
        setTestStatus('error')
        toast.error('Backend responded but returned an error')
      }
    } catch {
      setTestStatus('error')
      toast.error('Cannot reach backend. Check IP and port.')
    }
  }

  const saveServerUrl = () => {
    setApiUrl(serverUrl)
    toast.success('Server URL saved')
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px', maxWidth: '640px' }}>
      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Settings</h1>
        <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>Configure your backend connection and profile.</p>
      </div>

      {/* iOS / Server connection — most important for sideloaded app */}
      <section className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Smartphone size={16} color="var(--color-warm)" />
          <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>Backend Server (iOS / WiFi)</h3>
        </div>
        <p style={{ color: '#888', fontSize: '0.8125rem', margin: '0 0 16px', lineHeight: 1.6 }}>
          When running on iPhone/iPad via AltStore, set this to your Mac's local IP address.
          Find it in Mac → System Settings → Wi-Fi → Details → IP Address.
        </p>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Server size={13} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#555' }} />
            <input
              className="input"
              placeholder="http://192.168.1.100:8000/api/v1"
              value={serverUrl}
              onChange={e => setServerUrlState(e.target.value)}
              style={{ paddingLeft: '32px' }}
            />
          </div>
          <button className="btn btn-ghost" onClick={testConnection}>
            <Wifi size={13} />
            {testStatus === 'testing' ? 'Testing...' : 'Test'}
          </button>
        </div>
        {testStatus === 'ok' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#4ade80', fontSize: '0.8rem' }}>
            <CheckCircle size={13} /> Connected
          </div>
        )}
        {testStatus === 'error' && (
          <p style={{ color: '#f87171', fontSize: '0.8rem', margin: 0 }}>
            ✗ Cannot connect. Make sure the Mac backend is running and you're on the same WiFi network.
          </p>
        )}
        <button className="btn btn-primary btn-sm" onClick={saveServerUrl} style={{ marginTop: '12px' }}>
          Save URL
        </button>
      </section>

      {/* Profile */}
      <section className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <User size={16} color="var(--color-warm)" />
          <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>Profile & Brand</h3>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <Field label="Full Name" value={profile.full_name} onChange={v => setProfile(p => ({ ...p, full_name: v }))} />
            <Field label="NMLS ID" value={profile.nmls_id} onChange={v => setProfile(p => ({ ...p, nmls_id: v }))} placeholder="123456" />
          </div>
          <Field label="Company Name" value={profile.company_name} onChange={v => setProfile(p => ({ ...p, company_name: v }))} />
          <Field label="Calendly / Booking Link" value={profile.calendly_link} onChange={v => setProfile(p => ({ ...p, calendly_link: v }))} placeholder="https://calendly.com/you" />
          <div>
            <label style={labelStyle}>Brand Voice / Tone (used by AI for content & outreach)</label>
            <textarea className="input" rows={3} value={profile.brand_voice}
              onChange={e => setProfile(p => ({ ...p, brand_voice: e.target.value }))}
              placeholder="e.g. Approachable, local market expert, educates buyers without jargon, references Houston area, no hype" />
          </div>
          <button className="btn btn-primary btn-sm" style={{ width: 'fit-content' }}
            onClick={() => toast.success('Profile saved (API PATCH /auth/me — wire up when ready)')}>
            Save Profile
          </button>
        </div>
      </section>

      {/* AltStore instructions */}
      <section className="card">
        <h3 style={{ margin: '0 0 12px', fontSize: '0.9rem', fontWeight: 600 }}>AltStore Sideload Instructions</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {[
            '1. Install AltStore on your iPhone from altstore.io',
            '2. Run: cd admin-app && npm run build && npx cap sync ios',
            '3. Open ios/App/App.xcworkspace in Xcode',
            '4. Set your Apple ID in Signing & Capabilities',
            '5. Product → Archive → Distribute App → Development → Export IPA',
            '6. In AltStore on your phone → + → Install .ipa from Finder',
            '7. App auto-refreshes via AltStore when on same WiFi (free tier: 7-day cert)',
            '8. On first launch → Settings → set Backend URL to your Mac\'s local IP',
          ].map(step => (
            <p key={step} style={{ margin: 0, fontSize: '0.8125rem', color: '#aaa', lineHeight: 1.5 }}>{step}</p>
          ))}
        </div>
      </section>
    </div>
  )
}

function Field({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input className="input" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px' }

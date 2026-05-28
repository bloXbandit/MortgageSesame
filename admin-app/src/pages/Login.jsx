import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react'

export default function Login() {
  const { login, loading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Invalid credentials')
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--color-carbon)' }}>
      {/* LEFT — warm branding panel */}
      <div style={{
        width: '45%', background: 'var(--color-buttermilk)',
        padding: '64px 56px',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      }}>
        <div>
          <span style={{ fontWeight: 900, fontSize: '1.25rem', color: 'var(--color-inkwell)' }}>
            Mortgage<span style={{ color: '#b36b00' }}>Sesame</span>
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <span style={{
              display: 'inline-block', background: 'white', border: '1px solid var(--color-chrome)',
              borderRadius: '99px', padding: '3px 12px', fontSize: '0.75rem', fontWeight: 600,
              color: '#b36b00', marginBottom: '16px',
            }}>Command Center</span>
            <h1 style={{ fontWeight: 900, fontSize: '2.5rem', lineHeight: 1.1, margin: '0 0 16px', color: 'var(--color-inkwell)' }}>
              Your mortgage<br />growth OS.
            </h1>
            <p style={{ color: '#666', fontSize: '0.9375rem', lineHeight: 1.6, margin: 0, maxWidth: '320px' }}>
              Manage leads, campaigns, products, content, and your AI agent — all from one place.
            </p>
          </div>

          {/* Feature list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
            {[
              'AI lead scoring & intake',
              'Approval queue for all outreach',
              'Content Studio for social posts',
              'Agent API for Clawdbot / Hermes',
              'ElevenLabs voice integration',
            ].map(f => (
              <div key={f} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#b36b00', flexShrink: 0 }} />
                <span style={{ fontSize: '0.875rem', color: '#555' }}>{f}</span>
              </div>
            ))}
          </div>
        </div>

        <p style={{ fontSize: '0.7rem', color: '#aaa', margin: 0 }}>
          Private admin access. Authorized users only.
        </p>
      </div>

      {/* RIGHT — dark login panel */}
      <div style={{
        flex: 1, background: 'var(--color-carbon)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '48px',
      }}>
        <div style={{ width: '100%', maxWidth: '360px' }}>
          <h2 style={{ fontWeight: 900, fontSize: '1.75rem', margin: '0 0 8px', color: 'var(--color-paper)', letterSpacing: '0.32px' }}>
            SIGN IN
          </h2>
          <p style={{ color: '#666', fontSize: '0.875rem', margin: '0 0 32px' }}>
            Enter your credentials to access the dashboard.
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={labelStyle}>Email</label>
              <div style={{ position: 'relative' }}>
                <Mail size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#555' }} />
                <input
                  className="input"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  style={{ paddingLeft: '36px' }}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label style={labelStyle}>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#555' }} />
                <input
                  className="input"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  style={{ paddingLeft: '36px' }}
                  required
                />
              </div>
            </div>

            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                borderRadius: '6px', padding: '10px 12px',
              }}>
                <AlertCircle size={14} color="#f87171" />
                <span style={{ color: '#f87171', fontSize: '0.8125rem' }}>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', padding: '10px 16px', marginTop: '4px', fontSize: '0.9375rem' }}
            >
              {loading ? 'Signing in...' : <>Sign In <ArrowRight size={14} /></>}
            </button>
          </form>

          <p style={{ marginTop: '24px', fontSize: '0.7rem', color: '#444', textAlign: 'center' }}>
            First time? Run <code style={{ background: '#2a2a2a', padding: '1px 5px', borderRadius: '3px' }}>POST /api/v1/auth/register</code> to create your account.
          </p>
        </div>
      </div>
    </div>
  )
}

const labelStyle = {
  display: 'block', fontSize: '0.75rem', fontWeight: 600,
  color: '#888', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px',
}

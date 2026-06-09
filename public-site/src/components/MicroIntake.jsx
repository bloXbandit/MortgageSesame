/**
 * MicroIntake — contextual micro lead capture modal.
 * Used on listings ("Want numbers for this house?") and DPA hub.
 * Collects name + phone + optional context note. Submits to /api/v1/leads/intake.
 */
import { useState } from 'react'

import { API, CALCOM, BANKER_NMLS } from '../config'

export default function MicroIntake({ trigger, contextNote = '', onClose }) {
  const [step, setStep] = useState('form') // form | success
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !phone.trim()) { setError('Name and phone are required.'); return }
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/v1/leads/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: name,
          phone,
          email: email || undefined,
          source: 'hub_micro_intake',
          notes: contextNote || trigger || '',
        }),
      })
      if (!res.ok) throw new Error('Failed')
      setStep('success')
    } catch {
      setError('Something went wrong — try again or call us directly.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      onClick={e => e.target === e.currentTarget && onClose?.()}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000, padding: 20,
      }}
    >
      <div style={{
        background: '#1f1f1f',
        borderRadius: 12,
        padding: 32,
        maxWidth: 400,
        width: '100%',
        position: 'relative',
        animation: 'fadeUp 0.25s ease both',
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 16, right: 16,
            background: 'none', border: 'none', cursor: 'pointer', color: '#666',
            padding: 4,
          }}
          aria-label="Close"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 4L14 14M14 4L4 14" stroke="#888" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>

        {step === 'form' ? (
          <>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
                Quick Question
              </div>
              <h3 style={{ margin: 0, color: '#fff', fontSize: '1.25rem', fontWeight: 700, lineHeight: 1.3 }}>
                {trigger || 'Want numbers for this home?'}
              </h3>
              {contextNote && (
                <p style={{ margin: '8px 0 0', color: '#888', fontSize: '0.875rem' }}>{contextNote}</p>
              )}
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ display: 'block', color: '#888', fontSize: '0.75rem', marginBottom: 5, fontWeight: 500 }}>
                  Your name *
                </label>
                <input
                  className="input-field"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="First & last name"
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', color: '#888', fontSize: '0.75rem', marginBottom: 5, fontWeight: 500 }}>
                  Phone *
                </label>
                <input
                  className="input-field"
                  type="tel"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="(443) 555-0100"
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', color: '#888', fontSize: '0.75rem', marginBottom: 5, fontWeight: 500 }}>
                  Email (optional)
                </label>
                <input
                  className="input-field"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@email.com"
                />
              </div>

              {error && (
                <p style={{ margin: 0, color: '#f87171', fontSize: '0.8125rem' }}>{error}</p>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  marginTop: 4,
                  padding: '12px 20px',
                  background: submitting ? '#444' : '#f5c87a',
                  color: '#1f1f1f',
                  border: 'none',
                  borderRadius: 6,
                  fontWeight: 700,
                  fontSize: '0.9375rem',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {submitting ? 'Sending…' : 'Send My Numbers →'}
              </button>

              <p style={{ margin: 0, color: '#555', fontSize: '0.7rem', textAlign: 'center', lineHeight: 1.4 }}>
                No spam. No pressure. NMLS #{BANKER_NMLS}.
              </p>
            </form>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '12px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🏡</div>
            <h3 style={{ margin: '0 0 8px', color: '#fff', fontSize: '1.25rem', fontWeight: 700 }}>
              You're on the list!
            </h3>
            <p style={{ margin: '0 0 20px', color: '#888', fontSize: '0.9rem', lineHeight: 1.5 }}>
              I'll reach out with your numbers shortly. Or skip the wait and book a call now.
            </p>
            <a
              href={CALCOM}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block', width: '100%', textAlign: 'center',
                padding: '12px 20px', background: '#f5c87a', color: '#1f1f1f',
                borderRadius: 6, fontWeight: 700, fontSize: '0.9375rem',
                textDecoration: 'none', marginBottom: 10, boxSizing: 'border-box',
              }}
            >
              📅 Book a Free Call Now
            </a>
            <button
              onClick={onClose}
              style={{
                width: '100%', padding: '10px 20px',
                background: 'transparent', color: '#666',
                border: '1px solid #333', borderRadius: 6,
                fontWeight: 500, fontSize: '0.875rem', cursor: 'pointer',
              }}
            >
              I'll wait for your message
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

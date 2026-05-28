import { useLocation, Link } from 'react-router-dom'
import { CheckCircle, Calendar, ArrowRight } from 'lucide-react'

export default function ThankYou() {
  const { state } = useLocation()
  const message = state?.message || "Thank you! We'll be in touch shortly."
  const cta = state?.cta

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      {/* Left warm */}
      <div className="split-left" style={{
        width: '50%', padding: '64px 67px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '32px',
      }}>
        <a href="/" style={{ textDecoration: 'none', fontWeight: 900, fontSize: '1.2rem', color: 'var(--color-inkwell)' }}>
          Mortgage<span style={{ color: '#b36b00' }}>Sesame</span>
        </a>

        <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '50%',
            background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <CheckCircle size={28} color="#f5c87a" />
          </div>
          <h1 className="font-display-heavy" style={{ margin: 0 }}>You're in!</h1>
          <p className="font-body-lg" style={{ margin: 0, color: '#555', maxWidth: '360px' }}>
            {message}
          </p>
          {cta && (
            <p style={{ color: '#777', fontSize: '0.875rem', fontStyle: 'italic' }}>Next step: {cta}</p>
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <a href="https://calendly.com/[YOUR_LINK]" target="_blank" rel="noopener noreferrer" className="btn-dark">
            <Calendar size={14} /> Book a Call Now
          </a>
          <Link to="/" className="btn-primary">
            Back to Home <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* Right dark */}
      <div className="split-right" style={{
        flex: 1, padding: '64px 56px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '28px',
      }}>
        <h2 className="font-display-heavy" style={{ margin: 0, color: 'var(--color-paper)', fontSize: '1.5rem' }}>
          WHAT HAPPENS NEXT
        </h2>
        {[
          { n: '01', title: 'We review your answers', sub: 'Our AI matches you with the best available programs for your situation.' },
          { n: '02', title: 'We reach out', sub: 'Expect a message via the contact methods you approved — usually within 1 business day.' },
          { n: '03', title: 'Quick 15-min call', sub: 'We run a soft pull (if ready) and walk through your options — no pressure, no hard sell.' },
          { n: '04', title: 'Your roadmap', sub: 'Even if you\'re not ready today, you\'ll leave with a clear plan and timeline.' },
        ].map(({ n, title, sub }) => (
          <div key={n} style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <span style={{
              minWidth: '32px', height: '32px', borderRadius: '50%',
              background: '#2a2a2a', border: '1px solid #444',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.7rem', color: '#f5c87a', fontWeight: 700,
            }}>{n}</span>
            <div>
              <p style={{ margin: '0 0 4px', color: 'var(--color-paper)', fontWeight: 600, fontSize: '0.9rem' }}>{title}</p>
              <p style={{ margin: 0, color: '#888', fontSize: '0.8rem', lineHeight: 1.5 }}>{sub}</p>
            </div>
          </div>
        ))}

        <div style={{ marginTop: '16px', paddingTop: '24px', borderTop: '1px solid #2a2a2a' }}>
          <p style={{ fontSize: '0.7rem', color: '#555', lineHeight: 1.6, margin: 0 }}>
            This is not a credit decision or commitment to lend. All inquiries are subject to verification
            and underwriting review. Equal Housing Opportunity. NMLS# [YOUR_NMLS].
          </p>
        </div>
      </div>
    </div>
  )
}

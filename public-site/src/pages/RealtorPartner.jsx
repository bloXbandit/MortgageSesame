import { useState, useRef } from 'react'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

import { CALCOM, ZILLOW, BANKER_NMLS, SERVICE_STATES } from '../config'

// ── Value prop cards ────────────────────────────────────────────────────────
const VALUE_PROPS = [
  {
    icon: '⚡',
    title: 'Close in 10 Business Days',
    body: 'When your client needs speed — before another offer drops — I deliver. As fast as 10 business days to close.',
  },
  {
    icon: '✅',
    title: 'Same-Day Pre-Approvals',
    body: 'Your clients won\'t lose a home waiting on a pre-approval letter. I turn them around the same day.',
  },
  {
    icon: '💰',
    title: 'Down Payment Assistance',
    body: 'I know MD & DC DPA programs cold. Grants, forgivable loans, second liens. Most buyers qualify and don\'t know it — I find them the money.',
  },
  {
    icon: '🏦',
    title: 'Wholesale Lender Access',
    body: 'I work with UWM, Rocket, NewRez, and more. That means rate competition and more loan options — not just one bank\'s product sheet.',
  },
  {
    icon: '📲',
    title: 'I Generate Buyer Leads',
    body: 'MortgageSesame is my own platform. I run lead gen, book consultations, and build a buyer pipeline. Those buyers need a realtor — that\'s you.',
  },
  {
    icon: '🤝',
    title: 'I Invest in Your Business',
    body: 'Open houses, co-branded marketing, flyers, social content. I show up for my partners because your production growth is my growth.',
  },
]

// ── Lender logos (text-based since we don't have images) ────────────────────
const LENDERS = ['UWM', 'Rocket', 'NewRez', '+ More']

// ── Star row ────────────────────────────────────────────────────────────────
function StarRow({ count = 5, size = 18, color = '#f5c87a' }) {
  return (
    <span style={{ display: 'inline-flex', gap: 2 }}>
      {Array.from({ length: count }).map((_, i) => (
        <svg key={i} width={size} height={size} viewBox="0 0 20 20" fill={color}>
          <path d="M10 1l2.39 4.84 5.34.78-3.87 3.77.91 5.32L10 13.27l-4.77 2.44.91-5.32L2.27 6.62l5.34-.78L10 1z"/>
        </svg>
      ))}
    </span>
  )
}

// ── Partner form ─────────────────────────────────────────────────────────────
const BLANK = {
  first_name: '', last_name: '', email: '', phone: '', brokerage: '', message: '',
}

function PartnerForm() {
  const [form, setForm] = useState(BLANK)
  const [status, setStatus] = useState('idle') // idle | sending | done | error
  const [err, setErr]     = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    if (!form.first_name || !form.email || !form.phone) {
      setErr('Name, email, and phone are required.')
      return
    }
    setErr('')
    setStatus('sending')
    try {
      const notes = [
        form.brokerage ? `Brokerage: ${form.brokerage}` : '',
        form.message   ? `Message: ${form.message}`     : '',
      ].filter(Boolean).join('\n')

      const res = await fetch(`${API}/api/v1/leads/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name:        form.first_name,
          last_name:         form.last_name,
          email:             form.email,
          phone:             form.phone,
          notes,
          utm_source:        'realtor_partner',
          consent_email:     true,
          consent_call:      true,
          consent_sms:       false,
          loan_interest_type:'other',
          timeline:          'flexible',
          credit_score_range:'excellent',
        }),
      })
      if (!res.ok) throw new Error('Submit failed')
      setStatus('done')
      setForm(BLANK)
    } catch {
      setStatus('error')
      setErr('Something went wrong — please try again or call/text me directly.')
    }
  }

  if (status === 'done') {
    return (
      <div style={{
        textAlign: 'center', padding: '48px 24px',
        background: '#2a2a2a', borderRadius: 14, border: '1px solid #3a3a3a',
      }}>
        <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>🤝</div>
        <h3 style={{ margin: '0 0 10px', color: '#fff', fontWeight: 800, fontSize: '1.4rem' }}>
          You're in. Let's talk.
        </h3>
        <p style={{ color: '#888', margin: '0 0 24px', lineHeight: 1.6 }}>
          I got your info and I'll reach out within the hour.<br />
          If you want to skip the wait, book a call directly.
        </p>
        <a
          href={CALCOM}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: '11px 24px', background: '#f5c87a', color: '#1f1f1f',
            borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
            textDecoration: 'none', display: 'inline-block',
          }}
        >
          📅 Book a Call Now
        </a>
      </div>
    )
  }

  const inputStyle = {
    width: '100%', boxSizing: 'border-box',
    padding: '11px 14px',
    background: '#2a2a2a', border: '1px solid #3a3a3a',
    borderRadius: 7, color: '#fff', fontSize: '0.9375rem',
    outline: 'none', transition: 'border-color 0.15s',
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="form-row">
        <input
          placeholder="First name *"
          value={form.first_name}
          onChange={e => set('first_name', e.target.value)}
          style={inputStyle}
          onFocus={e  => e.target.style.borderColor = '#f5c87a'}
          onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
        />
        <input
          placeholder="Last name"
          value={form.last_name}
          onChange={e => set('last_name', e.target.value)}
          style={inputStyle}
          onFocus={e  => e.target.style.borderColor = '#f5c87a'}
          onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
        />
      </div>
      <input
        placeholder="Email *"
        type="email"
        value={form.email}
        onChange={e => set('email', e.target.value)}
        style={inputStyle}
        onFocus={e  => e.target.style.borderColor = '#f5c87a'}
        onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
      />
      <input
        placeholder="Phone *"
        type="tel"
        value={form.phone}
        onChange={e => set('phone', e.target.value)}
        style={inputStyle}
        onFocus={e  => e.target.style.borderColor = '#f5c87a'}
        onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
      />
      <input
        placeholder="Brokerage / Agency"
        value={form.brokerage}
        onChange={e => set('brokerage', e.target.value)}
        style={inputStyle}
        onFocus={e  => e.target.style.borderColor = '#f5c87a'}
        onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
      />
      <textarea
        placeholder="Anything you want me to know? (optional)"
        value={form.message}
        onChange={e => set('message', e.target.value)}
        rows={3}
        style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
        onFocus={e  => e.target.style.borderColor = '#f5c87a'}
        onBlur={e   => e.target.style.borderColor = '#3a3a3a'}
      />
      {err && (
        <p style={{ margin: 0, color: '#f87171', fontSize: '0.8125rem' }}>{err}</p>
      )}
      <button
        type="submit"
        disabled={status === 'sending'}
        style={{
          padding: '13px 0', background: status === 'sending' ? '#aaa' : '#f5c87a',
          color: '#1f1f1f', border: 'none', borderRadius: 7,
          fontWeight: 700, fontSize: '1rem', cursor: status === 'sending' ? 'not-allowed' : 'pointer',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => { if (status !== 'sending') e.currentTarget.style.background = '#e8a84c' }}
        onMouseLeave={e => { if (status !== 'sending') e.currentTarget.style.background = '#f5c87a' }}
      >
        {status === 'sending' ? 'Sending…' : "Let's Partner Up →"}
      </button>
      <p style={{ margin: 0, fontSize: '0.7rem', color: '#555', textAlign: 'center', lineHeight: 1.5 }}>
        I'll reach out within the hour. NMLS #{BANKER_NMLS} · No spam, ever.
      </p>
    </form>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function RealtorPartner() {
  const formRef = useRef(null)
  const scrollToForm = () => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section style={{
        background: '#1f1f1f',
        padding: 'clamp(64px, 10vw, 100px) 24px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle warm glow */}
        <div style={{
          position: 'absolute', top: '-80px', left: '50%', transform: 'translateX(-50%)',
          width: 600, height: 300,
          background: 'radial-gradient(ellipse, rgba(245,200,122,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', maxWidth: 760, margin: '0 auto' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 20,
            background: 'rgba(245,200,122,0.12)', color: '#f5c87a',
            padding: '5px 14px', borderRadius: 99, fontSize: '0.75rem', fontWeight: 600,
            border: '1px solid rgba(245,200,122,0.2)',
          }}>
            <span style={{ width: 6, height: 6, background: '#f5c87a', borderRadius: '50%' }} />
            For Licensed Realtors · {SERVICE_STATES} · NMLS #{BANKER_NMLS}
          </span>

          <h1 style={{
            fontSize: 'clamp(2.4rem, 6vw, 4rem)',
            fontWeight: 900, color: '#fff',
            lineHeight: 1.06, letterSpacing: '-0.03em',
            margin: '0 0 20px',
          }}>
            My goal is to increase<br />
            <span style={{ color: '#f5c87a' }}>your production.</span>
          </h1>

          <p style={{
            fontSize: 'clamp(1rem, 2vw, 1.175rem)',
            color: '#999', lineHeight: 1.65,
            margin: '0 auto 36px', maxWidth: 560,
          }}>
            10+ years of experience. Same-day pre-approvals. Close in as fast as 10 business days.
            I invest in your open houses, your marketing, and your reputation —
            because when your clients win, we both win.
          </p>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 40 }}>
            <button
              onClick={scrollToForm}
              style={{
                padding: '14px 32px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '1rem',
                cursor: 'pointer', transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#e8a84c'}
              onMouseLeave={e => e.currentTarget.style.background = '#f5c87a'}
            >
              Partner With Me →
            </button>
            <a
              href={CALCOM}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '14px 28px', background: 'transparent', color: '#ccc',
                border: '1px solid #3a3a3a', borderRadius: 7, fontWeight: 500,
                fontSize: '1rem', textDecoration: 'none', transition: 'border-color 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = '#f5c87a'}
              onMouseLeave={e => e.currentTarget.style.borderColor = '#3a3a3a'}
            >
              Book a Call First
            </a>
          </div>

          {/* Quick stats */}
          <div style={{
            display: 'flex', justifyContent: 'center', gap: 'clamp(20px, 4vw, 48px)',
            flexWrap: 'wrap',
          }}>
            {[
              ['10 Days',   'Fastest close'],
              ['Same Day',  'Pre-approvals'],
              ['10+ Years', 'Industry experience'],
              ['5 ★',       'Zillow rating'],
            ].map(([val, sub]) => (
              <div key={val} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 'clamp(1.2rem, 2.5vw, 1.6rem)', fontWeight: 800, color: '#f5c87a' }}>{val}</div>
                <div style={{ fontSize: '0.72rem', color: '#666', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Why Partner — value props grid ────────────────────────────────── */}
      <section style={{ padding: '80px 24px', background: '#fffbf5' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 52 }}>
            <div style={{ fontSize: '0.7rem', color: '#92520b', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
              Why Partner With Me
            </div>
            <h2 style={{ margin: '0 0 10px', fontSize: 'clamp(1.7rem, 3.5vw, 2.4rem)', fontWeight: 900, color: '#1f1f1f', letterSpacing: '-0.02em' }}>
              I make you look good to your clients.
            </h2>
            <p style={{ margin: 0, color: '#666', fontSize: '1rem', maxWidth: 480, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6 }}>
              Every tool, every turn-time, every dollar I invest — it protects your reputation and grows your GCI.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: 20,
          }}>
            {VALUE_PROPS.map(({ icon, title, body }) => (
              <div
                key={title}
                style={{
                  background: '#fff', border: '1px solid #ede8e0', borderRadius: 12,
                  padding: '28px 26px', transition: 'box-shadow 0.18s, transform 0.18s',
                }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 8px 28px rgba(0,0,0,0.07)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.transform = '' }}
              >
                <div style={{ fontSize: '1.75rem', marginBottom: 14 }}>{icon}</div>
                <div style={{ fontWeight: 800, color: '#1f1f1f', fontSize: '1rem', marginBottom: 8 }}>{title}</div>
                <div style={{ color: '#666', fontSize: '0.875rem', lineHeight: 1.6 }}>{body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Lender stack banner ────────────────────────────────────────────── */}
      <section style={{ background: '#1f1f1f', padding: '40px 24px', borderTop: '1px solid #2a2a2a' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
          <span style={{ fontSize: '0.72rem', color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, flexShrink: 0 }}>
            Lender Access
          </span>
          <div style={{ width: 1, height: 24, background: '#333', flexShrink: 0 }} />
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
            {LENDERS.map(l => (
              <span key={l} style={{
                padding: '6px 16px',
                background: '#2a2a2a', border: '1px solid #333',
                borderRadius: 6, color: '#ccc',
                fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.02em',
              }}>
                {l}
              </span>
            ))}
          </div>
          <div style={{ marginLeft: 'auto', color: '#666', fontSize: '0.8125rem' }}>
            Rate competition means better deals for your clients.
          </div>
        </div>
      </section>

      {/* ── Lead gen angle ────────────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px', background: '#ffedd2' }}>
        <div style={{
          maxWidth: 1100, margin: '0 auto',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 60, alignItems: 'center',
        }} className="lead-gen-grid">
          <div>
            <div style={{ fontSize: '0.7rem', color: '#92520b', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 10 }}>
              The MortgageSesame Platform
            </div>
            <h2 style={{ margin: '0 0 16px', fontSize: 'clamp(1.6rem, 3vw, 2.2rem)', fontWeight: 900, color: '#1f1f1f', lineHeight: 1.12, letterSpacing: '-0.02em' }}>
              I bring the buyers.<br />You bring the homes.
            </h2>
            <p style={{ color: '#555', lineHeight: 1.7, margin: '0 0 20px', fontSize: '0.9375rem' }}>
              MortgageSesame is my own lead generation platform. I run digital campaigns,
              capture buyer leads, and qualify them — so by the time they talk to me,
              they're ready to move.
            </p>
            <p style={{ color: '#555', lineHeight: 1.7, margin: '0 0 28px', fontSize: '0.9375rem' }}>
              Those buyers need a realtor. As my partner, you're my first call.
              That's a warm introduction to a pre-qualified buyer — not a cold lead list.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                'Pre-qualified buyers ready to tour homes',
                'Same-day pre-approval letter when you need it',
                'Co-branded materials for your open houses',
                'Social content I help create for both of us',
              ].map(item => (
                <div key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#e8a84c', fontWeight: 700, flexShrink: 0, marginTop: 1 }}>✓</span>
                  <span style={{ color: '#444', fontSize: '0.9rem', lineHeight: 1.5 }}>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { label: 'Buyer Lead Captured', sub: 'Via MortgageSesame platform', icon: '📲', color: '#fff3dc' },
              { label: 'Same-Day Pre-Approval', sub: 'Ready to make an offer', icon: '✅', color: '#dcfce7' },
              { label: 'Warm Intro to You', sub: 'Pre-qualified, motivated buyer', icon: '🤝', color: '#e0f2fe' },
              { label: 'Close in 10 Business Days', sub: 'Your commission. Your reputation.', icon: '🏡', color: '#fff3dc' },
            ].map(({ label, sub, icon, color }) => (
              <div key={label} style={{
                background: '#fff', border: '1px solid #ede8e0', borderRadius: 10,
                padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14,
              }}>
                <div style={{
                  width: 42, height: 42, background: color, borderRadius: 8,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '1.25rem', flexShrink: 0,
                }}>
                  {icon}
                </div>
                <div>
                  <div style={{ fontWeight: 700, color: '#1f1f1f', fontSize: '0.9rem' }}>{label}</div>
                  <div style={{ color: '#888', fontSize: '0.78rem', marginTop: 1 }}>{sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Zillow social proof ────────────────────────────────────────────── */}
      <section style={{ padding: '72px 24px', background: '#1f1f1f' }}>
        <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 20 }}>
            Verified Reviews
          </div>

          <div style={{
            background: '#2a2a2a', border: '1px solid #333', borderRadius: 14,
            padding: '40px 36px',
          }}>
            <StarRow count={5} size={28} color="#f5c87a" />
            <div style={{ marginTop: 16, marginBottom: 10 }}>
              <span style={{ fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 900, color: '#fff' }}>5.0</span>
              <span style={{ color: '#888', fontSize: '1rem', marginLeft: 6 }}>/ 5 on Zillow</span>
            </div>
            <p style={{ color: '#999', fontSize: '1rem', lineHeight: 1.65, margin: '0 0 28px', fontStyle: 'italic' }}>
              "Honest. Responsive. He actually explains what's happening at every step.
              My clients trust him — and that reflects on me."
            </p>
            <div style={{ marginBottom: 6, color: '#777', fontSize: '0.8125rem' }}>
              Senior Mortgage Advisor · 10+ Years · MD & DC Licensed
            </div>
            <a
              href={ZILLOW}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '10px 22px', marginTop: 20,
                background: 'transparent', border: '1px solid #444', borderRadius: 7,
                color: '#ccc', fontSize: '0.875rem', fontWeight: 600,
                textDecoration: 'none', transition: 'border-color 0.15s, color 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#f5c87a'; e.currentTarget.style.color = '#f5c87a' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#444'; e.currentTarget.style.color = '#ccc' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L1.5 8.4V22h7v-7h7v7h7V8.4z"/>
              </svg>
              See My Zillow Profile
            </a>
          </div>
        </div>
      </section>

      {/* ── Partner Form ──────────────────────────────────────────────────── */}
      <section
        ref={formRef}
        style={{ padding: '80px 24px', background: '#141414' }}
      >
        <div style={{
          maxWidth: 1060, margin: '0 auto',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start',
        }} className="form-grid">

          {/* Left — pitch */}
          <div>
            <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 12 }}>
              Let's Connect
            </div>
            <h2 style={{ margin: '0 0 16px', fontSize: 'clamp(1.7rem, 3vw, 2.3rem)', fontWeight: 900, color: '#fff', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
              Ready to close more deals together?
            </h2>
            <p style={{ color: '#888', lineHeight: 1.7, margin: '0 0 32px', fontSize: '0.9375rem' }}>
              Drop your info below and I'll reach out within the hour.
              No pitch, no pressure — just a real conversation about how we can build something together.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {[
                { icon: '📞', label: 'Call or text me', sub: 'I pick up. Always.' },
                { icon: '📅', label: 'Book a 15-min call', sub: CALCOM, link: CALCOM },
                { icon: '⭐', label: 'Check my Zillow reviews', sub: 'See what clients say', link: ZILLOW },
              ].map(({ icon, label, sub, link }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  <div style={{
                    width: 38, height: 38, background: '#2a2a2a', borderRadius: 8,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.1rem', flexShrink: 0,
                  }}>
                    {icon}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.875rem' }}>{label}</div>
                    {link ? (
                      <a href={link} target="_blank" rel="noopener noreferrer"
                        style={{ color: '#f5c87a', fontSize: '0.78rem', textDecoration: 'none' }}>
                        {sub}
                      </a>
                    ) : (
                      <div style={{ color: '#666', fontSize: '0.78rem' }}>{sub}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — form */}
          <PartnerForm />
        </div>
      </section>

      {/* ── Final NMLS bar ─────────────────────────────────────────────────── */}
      <div style={{
        background: '#0f0f0f', padding: '16px 24px', textAlign: 'center',
        fontSize: '0.7rem', color: '#444', lineHeight: 1.6,
      }}>
        NMLS #{BANKER_NMLS} · Licensed in {SERVICE_STATES} · Equal Housing Opportunity ·
        Not a commitment to lend. Rates and terms subject to change. All loans subject to credit approval.
      </div>

      <Footer />

      <style>{`
        @media (max-width: 768px) {
          .lead-gen-grid { grid-template-columns: 1fr !important; gap: 40px !important; }
          .form-grid     { grid-template-columns: 1fr !important; gap: 40px !important; }
        }
        @media (max-width: 520px) {
          .form-row { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { ArrowRight, Home as HomeIcon, TrendingUp, Users, DollarSign, Shield, Zap } from 'lucide-react'

const LOAN_TYPES = [
  { icon: HomeIcon, label: 'First-Time Buyer', desc: 'FHA, conventional & DPA programs', path: '/get-started?type=purchase' },
  { icon: DollarSign, label: 'Down Payment Help', desc: 'Assistance programs up to $25K+', path: '/get-started?type=dpa' },
  { icon: TrendingUp, label: 'Investor / DSCR', desc: 'Qualify on rental income, not W2', path: '/get-started?type=dscr_investor' },
  { icon: Zap, label: 'HELOC / Cash-Out', desc: 'Tap your equity for any goal', path: '/get-started?type=heloc' },
  { icon: TrendingUp, label: 'Refinance Review', desc: 'Find out if now is the right time', path: '/get-started?type=refinance' },
  { icon: Users, label: 'Realtor Partner', desc: 'Tools & support for your buyers', path: '/get-started?type=realtor' },
]

export default function Home() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ── Navbar ── */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 40px', background: 'var(--color-buttermilk)',
        borderBottom: '1px solid var(--color-chrome)',
      }}>
        <span style={{ fontWeight: 900, fontSize: '1.25rem', letterSpacing: '-0.5px', color: 'var(--color-inkwell)' }}>
          Mortgage<span style={{ color: '#b36b00' }}>Sesame</span>
        </span>
        <Link to="/get-started" className="btn-dark" style={{ fontSize: '0.875rem', padding: '8px 16px' }}>
          Get Pre-Qualified <ArrowRight size={14} />
        </Link>
      </nav>

      {/* ── Hero Split ── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'row', minHeight: 'calc(100vh - 57px)' }}>

        {/* LEFT — Buttermilk warm panel (67%) */}
        <section className="split-left" style={{
          width: '67%', padding: '64px 67px',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          gap: '56px',
        }}>
          {/* Hero block */}
          <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <span className="badge badge-warm" style={{ width: 'fit-content' }}>
              AI-Powered Mortgage Guidance
            </span>
            <h1 className="font-display-heavy" style={{ margin: 0, maxWidth: '560px', fontSize: '2.75rem' }}>
              Open the door to<br />your next move.
            </h1>
            <p className="font-body-lg" style={{ margin: 0, maxWidth: '480px', color: '#555' }}>
              Find the right loan program in minutes. No hard pull. No spam.
              Just an honest look at what you qualify for — DPA, FHA, DSCR, HELOC, refinance, and more.
            </p>
            <div style={{ display: 'flex', gap: '12px', marginTop: '8px', flexWrap: 'wrap' }}>
              <Link to="/get-started" className="btn-warm">
                Check My Options <ArrowRight size={16} />
              </Link>
              <Link to="/get-started?type=realtor" className="btn-primary">
                I'm a Realtor
              </Link>
            </div>
          </div>

          {/* Hero image — housing visual */}
          <div className="fade-up" style={{ animationDelay: '0.1s' }}>
            <HeroHouseVisual />
          </div>

          {/* Loan type cards */}
          <div className="fade-up" style={{ animationDelay: '0.2s' }}>
            <p className="font-body-sm" style={{ color: '#777', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              What are you looking for?
            </p>
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px',
            }}>
              {LOAN_TYPES.map(({ icon: Icon, label, desc, path }) => (
                <Link key={label} to={path} style={{ textDecoration: 'none' }}>
                  <div style={{
                    background: 'white', border: '1px solid var(--color-chrome)',
                    borderRadius: '10px', padding: '16px', cursor: 'pointer',
                    transition: 'border-color 0.15s, transform 0.15s',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = '#f5c87a'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-chrome)'; e.currentTarget.style.transform = 'translateY(0)' }}
                  >
                    <Icon size={20} color="#b36b00" />
                    <p style={{ margin: '8px 0 4px', fontWeight: 500, fontSize: '0.875rem', color: 'var(--color-inkwell)' }}>{label}</p>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: '#777', lineHeight: 1.4 }}>{desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* RIGHT — Carbon dark panel (33%) */}
        <section className="split-right" style={{
          width: '33%', padding: '64px 40px',
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center', gap: '32px',
          position: 'sticky', top: 0, height: '100vh',
        }}>
          <div>
            <h2 className="font-display-heavy" style={{ margin: '0 0 12px', color: 'var(--color-paper)', fontSize: '1.75rem' }}>
              GET STARTED<br />IN 2 MINUTES
            </h2>
            <p className="font-body-sm" style={{ color: '#888', margin: 0 }}>
              Answer a few quick questions. No credit check. No commitment.
              We'll match you with the right programs and reach out.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              { emoji: '🏠', title: 'Buy a Home', sub: 'FHA, conventional, VA, USDA' },
              { emoji: '💰', title: 'Down Payment Help', sub: 'DPA programs, grants, 2nd liens' },
              { emoji: '📈', title: 'Invest in Property', sub: 'DSCR, bank statement, investor' },
              { emoji: '🔄', title: 'Refinance or HELOC', sub: 'Cash-out, rate/term, equity line' },
              { emoji: '🤝', title: 'Partner with Me', sub: 'Realtors, title, referral partners' },
            ].map(({ emoji, title, sub }) => (
              <Link key={title} to={`/get-started?label=${encodeURIComponent(title)}`} style={{ textDecoration: 'none' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '14px',
                  background: 'var(--color-carbon-light)', border: '1px solid #333',
                  borderRadius: '8px', padding: '14px 16px', cursor: 'pointer',
                  transition: 'border-color 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = '#f5c87a'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = '#333'}
                >
                  <span style={{ fontSize: '1.25rem' }}>{emoji}</span>
                  <div>
                    <p style={{ margin: 0, fontWeight: 500, fontSize: '0.875rem', color: 'var(--color-paper)' }}>{title}</p>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: '#888' }}>{sub}</p>
                  </div>
                  <ArrowRight size={14} color="#555" style={{ marginLeft: 'auto' }} />
                </div>
              </Link>
            ))}
          </div>

          <div style={{ borderTop: '1px solid #2a2a2a', paddingTop: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Shield size={14} color="#f5c87a" />
              <span className="font-body-sm" style={{ color: '#888' }}>Your info is private. No hard credit pull.</span>
            </div>
            <p style={{ fontSize: '0.7rem', color: '#555', lineHeight: 1.5, margin: 0 }}>
              Educational estimates only. Not a commitment to lend. Subject to credit approval.
              Results may vary. Equal Housing Opportunity. NMLS# [YOUR_NMLS].
            </p>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer style={{
        background: 'var(--color-buttermilk)',
        borderTop: '1px solid var(--color-chrome)',
        padding: '20px 40px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: '8px',
      }}>
        <span className="font-body-sm" style={{ color: '#999' }}>
          © 2025 MortgageSesame · Equal Housing Opportunity · NMLS# [YOUR_NMLS]
        </span>
        <div style={{ display: 'flex', gap: '20px' }}>
          {['Privacy', 'Terms', 'Licenses', 'Contact'].map(l => (
            <a key={l} href="#" className="font-body-sm" style={{ color: '#777', textDecoration: 'none' }}>{l}</a>
          ))}
        </div>
      </footer>
    </div>
  )
}

/* ── Hero house SVG visual ───────────────────────────────────────────── */
function HeroHouseVisual() {
  return (
    <div style={{
      width: '100%', maxWidth: '600px',
      borderRadius: '10px', overflow: 'hidden',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%)',
      position: 'relative', aspectRatio: '16/9',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
    }}>
      {/* Stars */}
      {[...Array(20)].map((_, i) => (
        <div key={i} style={{
          position: 'absolute',
          width: i % 3 === 0 ? '3px' : '2px',
          height: i % 3 === 0 ? '3px' : '2px',
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.7)',
          left: `${(i * 47 + 13) % 95}%`,
          top: `${(i * 31 + 7) % 55}%`,
          animation: 'pulse-warm 3s ease-in-out infinite',
          animationDelay: `${i * 0.15}s`,
        }} />
      ))}
      {/* Moon */}
      <div style={{
        position: 'absolute', top: '14%', right: '12%',
        width: '44px', height: '44px', borderRadius: '50%',
        background: '#f5c87a', boxShadow: '0 0 30px rgba(245,200,122,0.5)',
      }} />
      {/* Ground */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: '30%', background: 'linear-gradient(180deg, #0d3b1f 0%, #0a2e16 100%)',
      }} />
      {/* Street */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: '12%', background: '#111',
      }}>
        <div style={{ position: 'absolute', top: '50%', left: '10%', right: '10%', height: '2px', background: '#f5c87a', opacity: 0.4, transform: 'translateY(-50%)' }} />
      </div>
      {/* House */}
      <svg viewBox="0 0 240 180" style={{ width: '55%', position: 'relative', zIndex: 2 }}>
        {/* Roof */}
        <polygon points="120,20 20,90 220,90" fill="#1a3c5e" stroke="#2a5f8f" strokeWidth="2" />
        {/* Chimney */}
        <rect x="155" y="38" width="16" height="35" fill="#152d45" />
        {/* Walls */}
        <rect x="35" y="90" width="170" height="90" fill="#1e4976" stroke="#2a6ba3" strokeWidth="1.5" />
        {/* Door */}
        <rect x="100" y="130" width="40" height="50" rx="4" fill="#0d2137" stroke="#2a5f8f" strokeWidth="1.5" />
        <circle cx="136" cy="156" r="3" fill="#f5c87a" />
        {/* Windows */}
        <rect x="52" y="105" width="36" height="30" rx="3" fill="#f5c87a" opacity="0.9" />
        <rect x="152" y="105" width="36" height="30" rx="3" fill="#f5c87a" opacity="0.9" />
        {/* Window cross */}
        <line x1="70" y1="105" x2="70" y2="135" stroke="#b36b00" strokeWidth="1.5" />
        <line x1="52" y1="120" x2="88" y2="120" stroke="#b36b00" strokeWidth="1.5" />
        <line x1="170" y1="105" x2="170" y2="135" stroke="#b36b00" strokeWidth="1.5" />
        <line x1="152" y1="120" x2="188" y2="120" stroke="#b36b00" strokeWidth="1.5" />
        {/* Path */}
        <rect x="110" y="165" width="20" height="15" fill="#f5c87a" opacity="0.3" />
      </svg>
      {/* Label overlay */}
      <div style={{
        position: 'absolute', bottom: '22%', left: '50%', transform: 'translateX(-50%)',
        background: 'rgba(245,200,122,0.15)', border: '1px solid rgba(245,200,122,0.3)',
        borderRadius: '6px', padding: '6px 16px', backdropFilter: 'blur(4px)',
      }}>
        <span style={{ color: '#f5c87a', fontSize: '0.75rem', fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase' }}>
          Find Your Program
        </span>
      </div>
    </div>
  )
}

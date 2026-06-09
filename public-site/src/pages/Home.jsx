import { CALCOM, APP_1003, BANKER_NMLS, SERVICE_STATES } from '../config'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import RateTicker from '../components/RateTicker'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import ListingCard from '../components/ListingCard'
import MicroIntake from '../components/MicroIntake'
import { useCurrentRates } from '../hooks/useRates'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const LOAN_TYPES = [
  { slug: 'fha',            label: 'FHA',              desc: '3.5% down · Flexible credit · First-time friendly',            icon: '🏡' },
  { slug: 'conventional',   label: 'Conventional',     desc: '5–20% down · No upfront MIP · Best rates with strong credit',  icon: '🏦' },
  { slug: 'va',             label: 'VA',               desc: '$0 down · No PMI · Veterans & active duty only',               icon: '🎖️' },
  { slug: 'dpa',            label: 'Down Payment Help', desc: 'Grants & deferred loans · MD & DC programs available',        icon: '💰' },
  { slug: 'dscr',           label: 'DSCR Investor',    desc: '25% down · Qualify on rent income · No W2 required',          icon: '📊' },
  { slug: 'heloc',          label: 'HELOC',            desc: 'Tap your equity · Flexible draw · Rates track Prime',          icon: '🔑' },
  { slug: 'rate-reduction', label: 'Rate Reduction',   desc: 'Lower your rate · FHA Streamline or Conv Rate & Term',        icon: '📉' },
  { slug: 'cash-out-refi',  label: 'Cash-Out Refi',    desc: 'Turn equity into cash · Improvements, payoff, or invest',     icon: '💵' },
]

function RateChip({ label, rate, highlight }) {
  if (!rate) return null
  return (
    <div style={{
      background: highlight ? '#1f1f1f' : '#2a2a2a',
      border: `1px solid ${highlight ? '#f5c87a44' : '#333'}`,
      borderRadius: 8,
      padding: '12px 16px',
      minWidth: 110,
    }}>
      <div style={{ fontSize: '0.67rem', color: '#888', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: '1.35rem', fontWeight: 800, color: highlight ? '#f5c87a' : '#fff', fontVariantNumeric: 'tabular-nums' }}>
        {rate.toFixed(2)}%
      </div>
    </div>
  )
}

function DpaTease({ program }) {
  const TYPE_STYLES = {
    grant:       { bg: '#dcfce7', color: '#166534', label: 'Grant' },
    forgivable:  { bg: '#d1fae5', color: '#065f46', label: 'Forgivable' },
    deferred:    { bg: '#e0f2fe', color: '#075985', label: 'Deferred Loan' },
    repayable:   { bg: '#fef9c3', color: '#713f12', label: 'Repayable' },
    second_lien: { bg: '#ede9fe', color: '#5b21b6', label: 'Second Lien' },
  }
  const s = TYPE_STYLES[program.dpa_type] || TYPE_STYLES.deferred
  return (
    <div style={{ background: '#2a2a2a', border: '1px solid #333', borderRadius: 10, padding: '18px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <span style={{ background: s.bg, color: s.color, padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600 }}>{s.label}</span>
        <span style={{ background: '#252525', color: '#888', padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem' }}>
          {program.state}{program.county ? ` · ${program.county}` : ''}
        </span>
      </div>
      <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.9375rem', marginBottom: 4 }}>{program.program_name}</div>
      <div style={{ color: '#f5c87a', fontWeight: 700, fontSize: '1rem' }}>{program.assistance_amount}</div>
    </div>
  )
}

export default function Home() {
  const { rates } = useCurrentRates()
  const [listings, setListings] = useState([])
  const [featuredDpa, setFeaturedDpa] = useState([])
  const [showIntake, setShowIntake] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/v1/listings/?featured_only=true`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setListings(data.slice(0, 3)))
      .catch(() => {})

    fetch(`${API}/api/v1/dpa/?featured_only=true`)
      .then(r => r.ok ? r.json() : [])
      .then(data => setFeaturedDpa(data.slice(0, 3)))
      .catch(() => {})
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="hero-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '90vh' }}>
        {/* LEFT — Buttermilk */}
        <div className="hero-left" style={{
          background: '#ffedd2',
          padding: '72px 56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 14,
            background: '#fff3dc', color: '#92520b',
            padding: '4px 12px', borderRadius: 99, fontSize: '0.75rem', fontWeight: 600,
            width: 'fit-content',
          }}>
            <span style={{ width: 6, height: 6, background: '#e8a84c', borderRadius: '50%', display: 'inline-block' }} />
            Maryland & DC · NMLS #{BANKER_NMLS}
          </span>

          <h1 style={{
            fontSize: 'clamp(2.2rem, 4.5vw, 3.5rem)',
            fontWeight: 900,
            color: '#1f1f1f',
            lineHeight: 1.08,
            letterSpacing: '-0.03em',
            margin: '0 0 20px',
          }}>
            Your local<br />homebuyer<br />intelligence hub.
          </h1>

          <p style={{ fontSize: '1.0625rem', color: '#555', lineHeight: 1.65, margin: '0 0 32px', maxWidth: 400 }}>
            Real rate data. Real homes. Real down payment programs.
            I'm a Maryland mortgage banker — not a faceless bank.
            Let's get you home.
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <a
              href={APP_1003}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '13px 28px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '1rem',
                cursor: 'pointer', transition: 'background 0.15s',
                display: 'inline-flex', alignItems: 'center', gap: 6,
                textDecoration: 'none',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#e8a84c'}
              onMouseLeave={e => e.currentTarget.style.background = '#f5c87a'}
            >
              Apply Now
            </a>
            <a
              href={CALCOM}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '13px 24px', background: '#1f1f1f', color: '#fff',
                border: 'none', borderRadius: 7, fontWeight: 600, fontSize: '1rem',
                cursor: 'pointer', textDecoration: 'none',
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}
            >
              Book a Call
            </a>
          </div>

          <div style={{ marginTop: 40, display: 'flex', gap: 32, flexWrap: 'wrap' }}>
            {[['MD & DC', 'Licensed'], ['$0 down', 'VA option'], ['3.5%', 'FHA min down'], ['25%', 'DSCR investor']].map(([val, sub]) => (
              <div key={val}>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#1f1f1f' }}>{val}</div>
                <div style={{ fontSize: '0.73rem', color: '#999', marginTop: 1 }}>{sub}</div>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT — Carbon */}
        <div className="hero-right" style={{
          background: '#1f1f1f',
          padding: '72px 56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 28,
        }}>
          {/* Rate chips */}
          <div>
            <div style={{ fontSize: '0.68rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 12 }}>
              Today's Example Rates
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              <RateChip label="Conv 30yr" rate={rates?.rate_conventional_30} highlight />
              <RateChip label="FHA 30yr"  rate={rates?.rate_fha_30} />
              <RateChip label="VA 30yr"   rate={rates?.rate_va_30} />
              <RateChip label="DSCR"      rate={rates?.rate_dscr} />
            </div>
            <p style={{ margin: '8px 0 0', fontSize: '0.67rem', color: '#555', lineHeight: 1.5 }}>
              Example rates for educational purposes only — not a commitment to lend.
            </p>
          </div>

          {/* Situation grid */}
          <div>
            <div style={{ fontSize: '0.68rem', color: '#888', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 12 }}>
              What's your situation?
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {LOAN_TYPES.map(lt => (
                <Link
                  key={lt.slug}
                  to={`/learn/${lt.slug}`}
                  style={{
                    background: '#2a2a2a', border: '1px solid #333', borderRadius: 8,
                    padding: '12px 14px', textDecoration: 'none',
                    transition: 'border-color 0.15s, background 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#f5c87a55'; e.currentTarget.style.background = '#2e2e2e' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#333'; e.currentTarget.style.background = '#2a2a2a' }}
                >
                  <div style={{ fontSize: '1.1rem', marginBottom: 3 }}>{lt.icon}</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#fff', marginBottom: 2 }}>{lt.label}</div>
                  <div style={{ fontSize: '0.68rem', color: '#666', lineHeight: 1.4 }}>{lt.desc}</div>
                </Link>
              ))}
            </div>
          </div>

          {/* Quick CTA bar */}
          <div style={{
            background: '#2a2a2a', border: '1px solid #333', borderRadius: 8,
            padding: '16px 18px', display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', gap: 12,
          }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.875rem', color: '#fff', marginBottom: 2 }}>Ready to run your numbers?</div>
              <div style={{ fontSize: '0.73rem', color: '#888' }}>Free consultation · No credit pull</div>
            </div>
            <a
              href={CALCOM}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '9px 16px', background: '#f5c87a', color: '#1f1f1f',
                borderRadius: 6, fontWeight: 700, fontSize: '0.8125rem',
                textDecoration: 'none', whiteSpace: 'nowrap', flexShrink: 0,
              }}
            >
              Book Free Call
            </a>
          </div>
        </div>
      </section>

      {/* ── Featured Listings ────────────────────────────────────────────── */}
      {listings.length > 0 && (
        <section style={{ padding: '72px 24px', background: '#faf6f0' }}>
          <div style={{ maxWidth: 1100, margin: '0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#92520b', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 4 }}>Homes</div>
                <h2 style={{ margin: 0, fontSize: 'clamp(1.5rem, 3vw, 2.1rem)', fontWeight: 800, color: '#1f1f1f' }}>
                  Run the numbers on these
                </h2>
              </div>
              <Link to="/homes" style={{ color: '#1f1f1f', fontWeight: 600, fontSize: '0.875rem', textDecoration: 'none' }}>
                View all homes →
              </Link>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 20 }}>
              {listings.map(l => <ListingCard key={l.id} listing={l} />)}
            </div>
          </div>
        </section>
      )}

      {/* ── DPA Spotlight ────────────────────────────────────────────────── */}
      <section style={{ padding: '72px 24px', background: '#1f1f1f' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 12 }}>
            <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
              Down Payment Help
            </div>
            <Link to="/dpa" style={{ color: '#f5c87a', fontWeight: 600, fontSize: '0.875rem', textDecoration: 'none' }}>
              Browse all programs →
            </Link>
          </div>
          <h2 style={{ margin: '0 0 8px', fontSize: 'clamp(1.5rem, 3vw, 2.1rem)', fontWeight: 800, color: '#fff' }}>
            Free money is on the table.
          </h2>
          <p style={{ margin: '0 0 28px', color: '#888', fontSize: '0.9375rem', maxWidth: 520 }}>
            Maryland and DC have some of the best down payment programs in the country.
            Most buyers don't know they qualify.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: 16 }}>
            {featuredDpa.length > 0 ? featuredDpa.map(p => (
              <DpaTease key={p.id} program={p} />
            )) : (
              [
                { id: 1, dpa_type: 'deferred',    state: 'MD', county: null,     program_name: 'MMP 1st Time Advantage', assistance_amount: 'Up to $6,000' },
                { id: 2, dpa_type: 'deferred',    state: 'DC', county: null,     program_name: 'HPAP',                   assistance_amount: 'Up to $202,000+' },
                { id: 3, dpa_type: 'second_lien', state: 'DC', county: null,     program_name: 'DC Open Doors',          assistance_amount: '3%–3.5% of price' },
              ].map(p => <DpaTease key={p.id} program={p} />)
            )}
          </div>
          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <Link
              to="/dpa"
              style={{
                padding: '13px 28px', background: '#f5c87a', color: '#1f1f1f',
                borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                textDecoration: 'none', display: 'inline-block',
              }}
            >
              See All MD & DC Programs →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Rate Reduction / Refi Spotlight ─────────────────────────────── */}
      <section style={{ padding: '72px 24px', background: '#0f1a2b' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ marginBottom: 32 }}>
            <div style={{ fontSize: '0.7rem', color: '#60a5fa', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
              Already Own a Home?
            </div>
            <h2 style={{ margin: '0 0 8px', fontSize: 'clamp(1.5rem, 3vw, 2.1rem)', fontWeight: 800, color: '#fff' }}>
              Your rate may be costing you every month.
            </h2>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.9375rem', maxWidth: 560 }}>
              If you bought or refinanced when rates were higher — or you're sitting on significant equity — these two moves are worth running the numbers on.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
            {/* Rate Reduction card */}
            <Link
              to="/learn/rate-reduction"
              style={{ textDecoration: 'none' }}
              onMouseEnter={e => e.currentTarget.querySelector('.refi-card').style.borderColor = '#60a5fa55'}
              onMouseLeave={e => e.currentTarget.querySelector('.refi-card').style.borderColor = '#1e3a5f'}
            >
              <div className="refi-card" style={{ background: '#111c2e', border: '1px solid #1e3a5f', borderRadius: 12, padding: '28px 26px', height: '100%', transition: 'border-color 0.18s', boxSizing: 'border-box' }}>
                <div style={{ fontSize: '2rem', marginBottom: 12 }}>📉</div>
                <div style={{ fontWeight: 800, color: '#fff', fontSize: '1.0625rem', marginBottom: 4 }}>Rate Reduction Refinance</div>
                <div style={{ color: '#60a5fa', fontWeight: 600, fontSize: '0.8rem', marginBottom: 10 }}>FHA Streamline &amp; Conventional Rate &amp; Term</div>
                <p style={{ margin: '0 0 16px', color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6 }}>
                  Rates dropped since you bought? A streamline refi can lower your payment with less paperwork and no appraisal in some cases. Break even in months — save for years.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
                  {['No appraisal options', 'FHA Streamline', 'Conv Rate & Term', 'Lower payment'].map(t => (
                    <span key={t} style={{ background: '#1e3a5f', color: '#93c5fd', padding: '3px 9px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 500 }}>{t}</span>
                  ))}
                </div>
                <div style={{ color: '#60a5fa', fontWeight: 600, fontSize: '0.8125rem' }}>
                  See how it works →
                </div>
              </div>
            </Link>

            {/* Cash-Out card */}
            <Link
              to="/learn/cash-out-refi"
              style={{ textDecoration: 'none' }}
              onMouseEnter={e => e.currentTarget.querySelector('.refi-card').style.borderColor = '#a78bfa55'}
              onMouseLeave={e => e.currentTarget.querySelector('.refi-card').style.borderColor = '#2d1f4e'}
            >
              <div className="refi-card" style={{ background: '#140f2a', border: '1px solid #2d1f4e', borderRadius: 12, padding: '28px 26px', height: '100%', transition: 'border-color 0.18s', boxSizing: 'border-box' }}>
                <div style={{ fontSize: '2rem', marginBottom: 12 }}>💵</div>
                <div style={{ fontWeight: 800, color: '#fff', fontSize: '1.0625rem', marginBottom: 4 }}>Cash-Out Refinance</div>
                <div style={{ color: '#a78bfa', fontWeight: 600, fontSize: '0.8rem', marginBottom: 10 }}>Turn your equity into liquid capital</div>
                <p style={{ margin: '0 0 16px', color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6 }}>
                  Access your equity for renovations, debt payoff, or a down payment on an investment property — at mortgage rates, not credit card rates.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
                  {['Up to 80% LTV', 'Fixed rate', 'Home improvements', 'Invest the equity'].map(t => (
                    <span key={t} style={{ background: '#2d1f4e', color: '#c4b5fd', padding: '3px 9px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 500 }}>{t}</span>
                  ))}
                </div>
                <div style={{ color: '#a78bfa', fontWeight: 600, fontSize: '0.8125rem' }}>
                  See how it works →
                </div>
              </div>
            </Link>
          </div>

          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '12px 28px', background: 'transparent', color: '#fff',
                border: '1px solid #334155', borderRadius: 7, fontWeight: 600,
                fontSize: '0.9375rem', cursor: 'pointer', transition: 'border-color 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = '#60a5fa'}
              onMouseLeave={e => e.currentTarget.style.borderColor = '#334155'}
            >
              Find Out If a Refinance Makes Sense for Me →
            </button>
          </div>
        </div>
      </section>

      {/* ── Learn ────────────────────────────────────────────────────────── */}
      <section style={{ padding: '72px 24px', background: '#ffedd2' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <div style={{ fontSize: '0.7rem', color: '#92520b', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>Education</div>
            <h2 style={{ margin: '0 0 8px', fontSize: 'clamp(1.5rem, 3vw, 2.1rem)', fontWeight: 800, color: '#1f1f1f' }}>
              Know before you go.
            </h2>
            <p style={{ margin: 0, color: '#666', fontSize: '0.9375rem', maxWidth: 460, marginLeft: 'auto', marginRight: 'auto' }}>
              Quick explainers on every loan type — written for real people, not underwriters.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))', gap: 12 }}>
            {LOAN_TYPES.map(lt => (
              <Link
                key={lt.slug}
                to={`/learn/${lt.slug}`}
                style={{
                  background: '#fff', border: '1px solid #ede8e0', borderRadius: 10,
                  padding: '20px', textDecoration: 'none', display: 'block',
                  transition: 'box-shadow 0.18s, transform 0.18s',
                }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.07)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.transform = '' }}
              >
                <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>{lt.icon}</div>
                <div style={{ fontWeight: 700, color: '#1f1f1f', fontSize: '0.9375rem', marginBottom: 4 }}>{lt.label}</div>
                <div style={{ fontSize: '0.75rem', color: '#888', lineHeight: 1.45 }}>{lt.desc}</div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────── */}
      <section style={{ padding: '72px 24px', background: '#1a1a1a', textAlign: 'center' }}>
        <div style={{ maxWidth: 540, margin: '0 auto' }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', fontWeight: 900, color: '#fff', lineHeight: 1.1 }}>
            Let's run your numbers.
          </h2>
          <p style={{ margin: '0 0 32px', color: '#888', fontSize: '1rem', lineHeight: 1.65 }}>
            No pressure. No credit pull. Just real numbers so you know exactly where you stand.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a
              href={APP_1003}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '14px 32px', background: '#f5c87a', color: '#1f1f1f',
                borderRadius: 7, fontWeight: 700, fontSize: '1rem',
                textDecoration: 'none', transition: 'background 0.15s',
                display: 'inline-block',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#e8a84c'}
              onMouseLeave={e => e.currentTarget.style.background = '#f5c87a'}
            >
              Apply Now
            </a>
            <a
              href={CALCOM}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '14px 28px', background: 'transparent', color: '#ccc',
                border: '1px solid #444', borderRadius: 7, fontWeight: 500,
                fontSize: '1rem', textDecoration: 'none',
              }}
            >
              Book a Free Call
            </a>
          </div>
          <p style={{ margin: '20px 0 0', color: '#444', fontSize: '0.73rem' }}>
            NMLS #{BANKER_NMLS} · Licensed MD & DC · Equal Housing Opportunity
          </p>
          <p style={{ margin: '14px 0 0', fontSize: '0.8rem', color: '#555' }}>
            Already spoke with us?{' '}
            <a
              href={APP_1003}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#f5c87a', fontWeight: 600, textDecoration: 'none' }}
              onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
              onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
            >
              Start your full mortgage application →
            </a>
          </p>
        </div>
      </section>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger="Ready to see your real numbers?"
          contextNote="I'll walk through FHA, Conventional, and DPA options — no credit pull needed."
          onClose={() => setShowIntake(false)}
        />
      )}

      <style>{`
        @media (max-width: 768px) {
          .hero-grid { grid-template-columns: 1fr !important; min-height: auto !important; }
          .hero-left  { padding: 52px 24px 44px !important; }
          .hero-right { padding: 44px 24px 56px !important; }
        }
      `}</style>
    </div>
  )
}

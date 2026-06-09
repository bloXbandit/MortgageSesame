import { Link } from 'react-router-dom'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'
import MicroIntake from '../components/MicroIntake'
import { CALCOM, APP_1003, BANKER_NMLS, SERVICE_STATES } from '../config'
import { useState } from 'react'
import { useCurrentRates } from '../hooks/useRates'

const RATE_DEFINITIONS = [
  {
    key: 'rate_conventional_30',
    label: 'Conventional 30yr Fixed',
    slug: 'conventional',
    icon: '🏦',
    who: 'Buyers with 5–20%+ down and good credit (680+)',
    notes: 'Most common loan type. No upfront MIP. PMI required below 20% down and drops automatically at 22% equity.',
  },
  {
    key: 'rate_fha_30',
    label: 'FHA 30yr Fixed',
    slug: 'fha',
    icon: '🏡',
    who: 'First-time buyers, buyers with 3.5%–10% down, or credit scores 580–679',
    notes: '1.75% upfront MIP + ~0.55% annual MIP. Lower rates than conventional in many markets.',
  },
  {
    key: 'rate_conventional_15',
    label: 'Conventional 15yr Fixed',
    slug: 'conventional',
    icon: '⚡',
    who: 'Buyers who can handle higher monthly payments to build equity faster',
    notes: 'Lowest rate on the board. Higher payment but you own the home in 15 years and pay far less interest.',
  },
  {
    key: 'rate_va_30',
    label: 'VA 30yr Fixed',
    slug: 'va',
    icon: '🎖️',
    who: 'Active duty military, veterans, surviving spouses',
    notes: '$0 down. No PMI ever. Lower rates than conventional. Small VA funding fee (typically 2.15–3.3%, financed).',
  },
  {
    key: 'rate_usda_30',
    label: 'USDA 30yr Fixed',
    slug: 'usda',
    icon: '🌾',
    who: 'Buyers in eligible rural/suburban areas with moderate income',
    notes: '$0 down. Income limits apply. Must be in a USDA-designated eligible area. Small guarantee fee.',
  },
  {
    key: 'rate_dscr',
    label: 'DSCR Investor Loan',
    slug: 'dscr',
    icon: '📊',
    who: 'Real estate investors — no W2 or personal income required',
    notes: 'Qualified on rental income (DSCR ratio). 25% down typical. No income tax returns needed.',
  },
  {
    key: 'rate_jumbo_30',
    label: 'Jumbo 30yr Fixed',
    slug: 'conventional',
    icon: '🏰',
    who: 'Buyers above conforming loan limits (~$766,550 in most MD/DC markets)',
    notes: 'Higher loan amount = higher rate, usually. Strong credit (720+) and reserves typically required.',
  },
  {
    key: 'rate_heloc_prime_plus',
    label: 'HELOC (Variable)',
    slug: 'heloc',
    icon: '🔑',
    who: 'Homeowners with equity who want a revolving credit line',
    notes: 'Variable rate tied to Prime Rate. Draw period typically 10 years, repayment 20 years.',
  },
]

export default function RatesPage() {
  const { rates, loading } = useCurrentRates()
  const [showIntake, setShowIntake] = useState(false)

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* Header */}
      <div style={{ background: '#1f1f1f', padding: '52px 24px 44px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
            {rates?.snapshot_date ? `Rate snapshot · ${rates.snapshot_date}` : 'Rate Snapshot'}
          </div>
          <h1 style={{ margin: '0 0 10px', color: '#fff', fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', fontWeight: 900, lineHeight: 1.1 }}>
            Today's Example Rates
          </h1>
          <p style={{ margin: '0 0 6px', color: '#888', fontSize: '1rem', maxWidth: 540 }}>
            {rates?.source === 'fred' || rates?.source === 'fred_live'
              ? 'Rates sourced from the Federal Reserve (FRED) and adjusted for typical market spreads.'
              : "Rates updated by your mortgage banker for today's market."}
          </p>
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#555' }}>
            These are example figures for educational purposes only — not a rate lock or commitment to lend.
          </p>
        </div>
      </div>

      {/* Rate cards */}
      <div style={{ flex: 1, padding: '36px 24px 64px', background: '#fafaf9' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ display: 'grid', gap: 12 }}>
            {RATE_DEFINITIONS.map(def => {
              const rate = rates?.[def.key]
              return (
                <div
                  key={def.key}
                  style={{
                    background: '#fff',
                    border: '1px solid #ede8e0',
                    borderRadius: 10,
                    padding: '20px 22px',
                    display: 'grid',
                    gridTemplateColumns: '1fr auto',
                    gap: 16,
                    alignItems: 'start',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                      <span style={{ fontSize: '1.2rem' }}>{def.icon}</span>
                      <span style={{ fontWeight: 700, fontSize: '1rem', color: '#1f1f1f' }}>{def.label}</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: 4 }}>
                      <strong style={{ color: '#555' }}>Best for:</strong> {def.who}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#999', lineHeight: 1.5 }}>{def.notes}</div>
                    <Link
                      to={`/learn/${def.slug}`}
                      style={{ display: 'inline-block', marginTop: 8, fontSize: '0.75rem', color: '#1f1f1f', fontWeight: 600, textDecoration: 'underline' }}
                    >
                      Learn more →
                    </Link>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    {loading ? (
                      <div style={{ width: 80, height: 36, background: '#f0ece4', borderRadius: 6 }} />
                    ) : rate ? (
                      <div style={{ fontSize: '2rem', fontWeight: 900, color: '#1f1f1f', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
                        {rate.toFixed(2)}%
                      </div>
                    ) : (
                      <div style={{ fontSize: '1rem', color: '#ccc' }}>—</div>
                    )}
                    <div style={{ fontSize: '0.7rem', color: '#bbb', marginTop: 2 }}>example rate</div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* CTA */}
          <div style={{ marginTop: 32, background: '#1f1f1f', borderRadius: 10, padding: '24px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
            <div>
              <div style={{ color: '#fff', fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>Want YOUR rate?</div>
              <div style={{ color: '#888', fontSize: '0.875rem' }}>
                These are market examples — your actual rate depends on credit, down payment, and loan type.
              </div>
            </div>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '12px 24px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
              }}
            >
              Get My Personalized Rate
            </button>
          </div>

          {/* Disclaimer */}
          <div style={{ marginTop: 20, padding: '14px 16px', background: '#fff', border: '1px solid #ede8e0', borderRadius: 8 }}>
            <p style={{ margin: 0, fontSize: '0.7rem', color: '#aaa', lineHeight: 1.65 }}>
              All rates displayed are example figures for educational purposes only and do not constitute a rate lock,
              mortgage commitment, or offer to lend. Actual rates vary based on credit score, loan-to-value ratio,
              property type, loan amount, occupancy, and other underwriting factors. Rate data sourced from FRED
              (Federal Reserve Economic Data) and/or manually updated. NMLS #{BANKER_NMLS}. Equal Housing Opportunity.
            </p>
          </div>
        </div>
      </div>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger="Let's find your actual rate."
          contextNote="I'll reach out to run through what rate range you'd realistically qualify for."
          onClose={() => setShowIntake(false)}
        />
      )}
    </div>
  )
}

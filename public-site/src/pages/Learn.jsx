import { Link } from 'react-router-dom'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'
import MicroIntake from '../components/MicroIntake'
import { useState } from 'react'
import { SERVICE_STATES } from '../config'

const PRODUCTS = [
  {
    slug: 'fha',
    label: 'FHA Loan',
    icon: '🏡',
    tagline: "The first-timer's best friend.",
    desc: '3.5% down, flexible credit requirements, and rates that often beat conventional. Backed by the Federal Housing Administration.',
    tags: ['3.5% down', '580+ credit', 'First-time friendly', 'MIP required'],
  },
  {
    slug: 'conventional',
    label: 'Conventional Loan',
    icon: '🏦',
    tagline: 'Clean, no-frills, and the most flexible.',
    desc: '5% down gets you in. 20% down drops PMI forever. No upfront insurance fee — just the mortgage.',
    tags: ['5–20% down', '620+ credit', 'PMI drops at 20% equity', 'No upfront fee'],
  },
  {
    slug: 'va',
    label: 'VA Loan',
    icon: '🎖️',
    tagline: 'The best mortgage in America. Earned it.',
    desc: '$0 down. No PMI. Lower rates than conventional. For veterans, active duty, and surviving spouses — a genuine earned benefit.',
    tags: ['$0 down', 'No PMI ever', 'Veterans only', 'VA funding fee'],
  },
  {
    slug: 'dpa',
    label: 'Down Payment Assistance',
    icon: '💰',
    tagline: 'Free money most buyers never ask about.',
    desc: `Grants, forgivable loans, and deferred seconds are available in ${SERVICE_STATES} and can cover your entire down payment. Most buyers qualify and don't know it.`,
    tags: ['Up to $202K in DC', 'Up to $40K in MD counties', 'First-time buyers', 'Income limits apply'],
  },
  {
    slug: 'usda',
    label: 'USDA Loan',
    icon: '🌾',
    tagline: '$0 down outside the city.',
    desc: `Zero down payment for eligible rural and suburban areas. Income limits apply. More areas in ${SERVICE_STATES} qualify than most people think.`,
    tags: ['$0 down', 'Rural eligible areas', 'Income limits', 'Low guarantee fee'],
  },
  {
    slug: 'dscr',
    label: 'DSCR Investor Loan',
    icon: '📊',
    tagline: 'Invest without the W2 drama.',
    desc: 'Debt Service Coverage Ratio loans qualify you based on rental income, not your personal tax returns. Designed for real estate investors.',
    tags: ['25% down', 'No W2 needed', 'Rental income qualifies', 'Higher rates'],
  },
  {
    slug: 'heloc',
    label: 'HELOC',
    icon: '🔑',
    tagline: 'Your equity, on demand.',
    desc: 'A Home Equity Line of Credit lets you draw from your equity as needed. Rates vary with Prime. Good for renovations, emergencies, or investing.',
    tags: ['Revolving credit line', 'Variable rate', 'Equity required', 'Draw + repayment periods'],
  },
  {
    slug: 'bank-statement',
    label: 'Bank Statement Loan',
    icon: '📄',
    tagline: 'Self-employed? Show your deposits, not your taxes.',
    desc: 'Qualify using 12–24 months of bank statements instead of tax returns. Built for self-employed borrowers, business owners, and freelancers.',
    tags: ['Self-employed', '12–24 mo. statements', 'No tax returns', 'Higher rate than conventional'],
  },
  {
    slug: 'rate-reduction',
    label: 'Rate Reduction Refinance',
    icon: '📉',
    tagline: 'Pay less every month — period.',
    desc: 'Rates dropped since you bought? FHA Streamline and conventional Rate & Term refis let you capture a lower rate — faster close, less paperwork than a purchase.',
    tags: ['No appraisal (FHA Streamline)', 'Lower monthly payment', 'FHA → Conventional option', 'Break-even 12–18 mo.'],
  },
  {
    slug: 'cash-out-refi',
    label: 'Cash-Out Refinance',
    icon: '💵',
    tagline: 'Turn your equity into liquid.',
    desc: 'Replace your mortgage with a larger one and pocket the difference. Use equity for home improvements, debt payoff, or a down payment on an investment property.',
    tags: ['Up to 80% LTV', 'Fixed lump sum', 'Lower rate than personal loans', 'Full underwrite required'],
  },
]

export default function Learn() {
  const [showIntake, setShowIntake] = useState(false)

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* Header */}
      <div style={{ background: '#1f1f1f', padding: '52px 24px 44px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
            Mortgage Education
          </div>
          <h1 style={{ margin: '0 0 10px', color: '#fff', fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', fontWeight: 900, lineHeight: 1.1 }}>
            Know before you go.
          </h1>
          <p style={{ margin: 0, color: '#888', fontSize: '1rem', maxWidth: 520 }}>
            Plain-English explainers on every loan type — written for buyers and investors, not underwriters.
          </p>
        </div>
      </div>

      {/* Product grid */}
      <div style={{ flex: 1, padding: '36px 24px 64px', background: '#fafaf9' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18 }}>
            {PRODUCTS.map(p => (
              <Link
                key={p.slug}
                to={`/learn/${p.slug}`}
                style={{
                  background: '#fff',
                  border: '1px solid #ede8e0',
                  borderRadius: 10,
                  padding: '22px',
                  textDecoration: 'none',
                  display: 'block',
                  transition: 'box-shadow 0.18s, transform 0.18s',
                }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 8px 28px rgba(0,0,0,0.08)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.transform = '' }}
              >
                <div style={{ fontSize: '2rem', marginBottom: 10 }}>{p.icon}</div>
                <div style={{ fontWeight: 800, color: '#1f1f1f', fontSize: '1.0625rem', marginBottom: 2 }}>{p.label}</div>
                <div style={{ fontStyle: 'italic', color: '#888', fontSize: '0.8125rem', marginBottom: 8 }}>{p.tagline}</div>
                <p style={{ margin: '0 0 12px', color: '#555', fontSize: '0.8rem', lineHeight: 1.55 }}>{p.desc}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {p.tags.map(t => (
                    <span key={t} style={{
                      background: '#f0ece4', color: '#666',
                      padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 500,
                    }}>{t}</span>
                  ))}
                </div>
                <div style={{ marginTop: 14, color: '#1f1f1f', fontWeight: 600, fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                  Learn more →
                </div>
              </Link>
            ))}
          </div>

          {/* CTA */}
          <div style={{ marginTop: 40, textAlign: 'center', background: '#1f1f1f', borderRadius: 12, padding: '36px 28px' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: 10 }}>🤔</div>
            <h3 style={{ margin: '0 0 8px', color: '#fff', fontSize: '1.2rem', fontWeight: 800 }}>
              Not sure which loan is right for you?
            </h3>
            <p style={{ margin: '0 0 20px', color: '#888', fontSize: '0.9rem' }}>
              Tell me about your situation and I'll run through your options — no pressure, no credit pull.
            </p>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '12px 28px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                cursor: 'pointer',
              }}
            >
              Let's Figure It Out
            </button>
          </div>
        </div>
      </div>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger="Let's figure out the right loan for you."
          contextNote="No credit pull, no pressure — just a quick conversation."
          onClose={() => setShowIntake(false)}
        />
      )}
    </div>
  )
}

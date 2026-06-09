/**
 * Generic product detail page.
 * Route: /learn/:slug
 * Content map drives all loan type pages from one component.
 */
import { useParams, Link } from 'react-router-dom'
import { CALCOM, APP_1003, BANKER_NMLS, SERVICE_STATES } from '../../config'
import { useState } from 'react'
import Nav from '../../components/Nav'
import Footer from '../../components/Footer'
import RateTicker from '../../components/RateTicker'
import MicroIntake from '../../components/MicroIntake'

const CONTENT = {
  fha: {
    label: 'FHA Loan',
    icon: '🏡',
    tagline: "The first-timer's best friend.",
    hero: '#1f1f1f',
    accentColor: '#f5c87a',
    summary: 'FHA loans are insured by the Federal Housing Administration and designed for buyers who need more flexibility on down payment and credit score. They\'re the most popular choice for first-time buyers in Maryland and DC.',
    pros: [
      '3.5% down payment with 580+ credit score',
      '10% down accepted with 500–579 credit score',
      'Lower rates than conventional in many scenarios',
      'Gift funds accepted for down payment',
      'Higher DTI tolerance (up to 57% in some cases)',
    ],
    cons: [
      '1.75% upfront MIP (rolled into loan)',
      '~0.55% annual MIP for life of loan if < 10% down',
      'Loan limits apply (~$498K–$1.15M in MD/DC metro)',
      'Property must meet FHA minimum property standards',
    ],
    faqs: [
      { q: 'Can I use DPA with an FHA loan?', a: 'Yes — FHA is one of the most DPA-compatible loan types. Most Maryland and DC DPA programs work with FHA.' },
      { q: 'Does FHA MIP ever go away?', a: 'If you put 10% or more down, MIP drops off after 11 years. Below 10%, MIP stays for the full loan term — refinancing to conventional later is the usual exit.' },
      { q: 'Can I use FHA for a 2–4 unit property?', a: 'Yes, as long as you live in one of the units as your primary residence.' },
    ],
  },
  conventional: {
    label: 'Conventional Loan',
    icon: '🏦',
    tagline: 'Clean, flexible, and the most common.',
    hero: '#1f1f1f',
    summary: 'Conventional loans are not government-backed — they conform to Fannie Mae and Freddie Mac guidelines. With stronger credit, they often offer better rates and terms than FHA.',
    pros: [
      '5% down (3% for first-time buyers via HomeReady/HomePossible)',
      'PMI automatically cancels at 22% equity',
      'No upfront insurance fee',
      'Higher loan limits than FHA in high-cost areas',
      'Shorter MIP timeline compared to FHA',
    ],
    cons: [
      'Stricter credit requirements (typically 620+, best rates at 740+)',
      'PMI required below 20% down',
      'Less flexible on DTI vs. FHA',
      'Gift funds have more restrictions',
    ],
    faqs: [
      { q: 'What\'s the difference between conforming and non-conforming?', a: 'Conforming loans meet Fannie/Freddie limits (~$766,550 in most areas, higher in MD/DC metro). Non-conforming (jumbo) loans exceed those limits.' },
      { q: 'When does PMI drop off?', a: 'Automatically when you reach 22% equity based on original amortization. You can request removal at 20% with an appraisal.' },
    ],
  },
  va: {
    label: 'VA Loan',
    icon: '🎖️',
    tagline: 'The best mortgage in America. You earned it.',
    hero: '#1a2744',
    summary: 'VA loans are guaranteed by the Department of Veterans Affairs for eligible servicemembers, veterans, and surviving spouses. No down payment, no PMI, and some of the lowest rates available anywhere.',
    pros: [
      '$0 down payment (100% financing)',
      'No private mortgage insurance ever',
      'Consistently lowest rates in the market',
      'No loan limit with full entitlement',
      'Lenient credit and DTI guidelines',
    ],
    cons: [
      'VA funding fee: 2.15%–3.3% (can be financed)',
      'Must have VA eligibility (Certificate of Eligibility)',
      'Property must meet VA minimum property requirements',
      'Primary residence only (no investment use)',
    ],
    faqs: [
      { q: 'How do I get a Certificate of Eligibility?', a: 'Your lender can pull it directly in most cases. You can also get it at VA.gov or through a VSO.' },
      { q: 'Is the VA funding fee waived for anyone?', a: 'Yes — veterans with a VA disability rating of 10%+ are exempt from the funding fee entirely.' },
    ],
  },
  usda: {
    label: 'USDA Loan',
    icon: '🌾',
    tagline: '$0 down outside the city limits.',
    hero: '#1a3020',
    summary: 'USDA loans are backed by the U.S. Department of Agriculture for buyers in eligible rural and suburban areas. Zero down payment and income limits apply — but much of Maryland is eligible.',
    pros: [
      '$0 down payment',
      'Below-market interest rates',
      'Low annual guarantee fee (~0.35%)',
      'No minimum credit score (though 640+ preferred)',
    ],
    cons: [
      'Must be in a USDA-eligible area (check eligibility map)',
      'Household income cannot exceed 115% of area median income',
      'Primary residence only',
      '1% upfront guarantee fee (financed)',
    ],
    faqs: [
      { q: 'How do I know if a property is USDA eligible?', a: 'Use the USDA eligibility map at eligibility.sc.egov.usda.gov. Many suburban Maryland towns qualify.' },
      { q: 'Does USDA work with DPA?', a: 'Some DPA programs allow USDA. Maryland Mortgage Program (MMP) lists USDA as eligible for many products.' },
    ],
  },
  dpa: {
    label: 'Down Payment Assistance',
    icon: '💰',
    tagline: 'Free money most buyers never ask about.',
    hero: '#1f1f1f',
    summary: 'Down Payment Assistance (DPA) programs provide grants, forgivable loans, or deferred seconds to help buyers cover their down payment and/or closing costs. Maryland and DC have among the best DPA programs in the country.',
    pros: [
      'Can cover entire 3.5% FHA down payment',
      'Multiple programs can be stacked',
      'Many programs have no monthly payment',
      'Some programs are forgivable over 3–10 years',
      'Available to first-time AND some repeat buyers',
    ],
    cons: [
      'Income limits apply to most programs',
      'Required homebuyer education in most cases',
      'Must use an approved lender',
      'Property must be primary residence',
      'Terms vary widely by program',
    ],
    faqs: [
      { q: 'Can I stack DPA programs?', a: 'Yes — in some cases. For example, MMP 6000 + county-level DPA is common. We can help identify combinations.' },
      { q: 'What\'s the biggest DPA program in DC?', a: 'HPAP (Home Purchase Assistance Program) offers up to $202,000+ for income-qualified buyers. It\'s one of the most generous in the country.' },
      { q: 'Is DPA taxable?', a: 'Grants may have tax implications. Deferred and forgivable loans generally are not taxable. Consult a tax advisor.' },
    ],
    ctaLink: '/dpa',
    ctaLabel: 'Browse MD & DC Programs →',
  },
  dscr: {
    label: 'DSCR Investor Loan',
    icon: '📊',
    tagline: 'Invest without the W2 drama.',
    hero: '#1f1f1f',
    summary: 'Debt Service Coverage Ratio (DSCR) loans qualify investors based on rental income from the property, not personal income or tax returns. The ideal loan for real estate investors who want to scale.',
    pros: [
      'No personal income verification',
      'No tax returns or W2s required',
      'Qualify on rental income alone',
      'Can close in an LLC',
      'Scalable — no limit on number of properties',
    ],
    cons: [
      '25% down payment typically required',
      'Higher rates (~1% above conventional)',
      'DSCR ratio usually needs to be ≥1.0–1.25',
      'Investors only — not for primary residences',
      'Fewer lender options than conventional',
    ],
    faqs: [
      { q: 'What is the DSCR ratio?', a: 'Gross rental income ÷ total monthly housing payment (PITIA). A ratio of 1.0 means rent exactly covers the payment. Most lenders want 1.0–1.25.' },
      { q: 'Can I use a DSCR loan if the property is vacant?', a: 'Some lenders use a market rent appraisal (Form 1007) instead of actual rent to qualify vacant properties.' },
      { q: 'Can I close in an LLC?', a: 'Yes — most DSCR lenders allow or even prefer LLC vesting, unlike conventional Fannie/Freddie loans.' },
    ],
  },
  heloc: {
    label: 'HELOC',
    icon: '🔑',
    tagline: 'Your equity, on demand.',
    hero: '#1f1f1f',
    summary: 'A Home Equity Line of Credit (HELOC) is a revolving line of credit secured by your home\'s equity. You draw what you need, when you need it — like a credit card backed by your house.',
    pros: [
      'Only pay interest on what you draw',
      'Flexible — ideal for renovations, emergencies, or down payment on next home',
      'Usually lower rate than personal loans or credit cards',
      'Interest may be tax-deductible (consult tax advisor)',
    ],
    cons: [
      'Variable rate — tied to Prime Rate, can go up',
      'Your home is collateral',
      'Draw period (typically 10 years) then repayment period starts',
      'Lenders can freeze line in a downturn',
    ],
    faqs: [
      { q: 'Can I use a HELOC as a down payment?', a: 'Yes — some buyers use a HELOC on their current home to fund the down payment on a new purchase or investment property.' },
      { q: 'How much can I borrow?', a: 'Typically up to 85–90% of your home\'s value minus what you owe. Example: $400K home, $250K owed = ~$90K–$110K HELOC available.' },
    ],
  },
  'bank-statement': {
    label: 'Bank Statement Loan',
    icon: '📄',
    tagline: 'Self-employed? Show your deposits, not your taxes.',
    hero: '#1f1f1f',
    summary: 'Bank Statement loans let self-employed borrowers qualify using 12–24 months of bank deposits instead of tax returns. Perfect for business owners who write off significant expenses.',
    pros: [
      'No tax returns required',
      '12 or 24 months business/personal bank statements',
      'Ideal for high-write-off business owners',
      'Available for purchase, refinance, and cash-out',
    ],
    cons: [
      'Higher rate than conventional (~0.5–1% above)',
      'Larger down payment often required (10–20%)',
      'Fewer lenders offer this product',
      'Manual underwriting — longer process',
    ],
    faqs: [
      { q: 'Do I need 2 years self-employed?', a: 'Most lenders require at least 2 years of self-employment history, though some accept 12 months.' },
      { q: 'Personal or business bank statements?', a: 'Either works. Business statements use an expense factor (typically 50% of deposits = income). Personal statements use a higher percentage.' },
    ],
  },

  'rate-reduction': {
    label: 'Rate Reduction Refinance',
    icon: '📉',
    tagline: 'Pay less every month — period.',
    hero: '#0f2337',
    accentColor: '#60a5fa',
    summary: 'If rates have dropped since you bought — or since you last refinanced — a Rate Reduction Refinance lets you capture a lower payment without starting over on equity. Two main paths: FHA Streamline (if you have an FHA loan) and Conventional Rate & Term. Both are faster and cheaper than a full purchase underwrite.',
    pros: [
      'FHA Streamline: no appraisal required, minimal documentation, net tangible benefit rule protects you',
      'Conventional Rate & Term: drop PMI if you\'ve hit 20% equity',
      'Lower monthly payment = more cash flow every month',
      'No new down payment required — you already own the home',
      'Can shorten loan term (30yr → 15yr) while lowering or maintaining payment',
    ],
    cons: [
      'Closing costs still apply (~$2,000–$5,000) — factor into break-even timeline',
      'FHA Streamline keeps MIP; to remove it you\'d refinance to conventional',
      'Rate must drop enough to justify costs — standard break-even is 12–18 months',
      'Must have been current on payments (typically 6 months on-time required)',
      'Conventional refi requires full appraisal in most cases',
    ],
    faqs: [
      {
        q: 'How do I know if refinancing makes sense right now?',
        a: 'Simple math: take your monthly savings and divide into your closing costs. If you\'ll break even in under 24 months and plan to stay, it usually makes sense. I run this calculation for free — no credit pull needed for the initial estimate.',
      },
      {
        q: 'What is FHA Streamline exactly?',
        a: 'An FHA-to-FHA refinance that skips the full appraisal and re-verification of income/assets. You must have an existing FHA loan, be current on payments, and demonstrate a "net tangible benefit" — typically at least a 0.5% rate drop or a switch from adjustable to fixed.',
      },
      {
        q: 'What\'s Conventional Rate & Term?',
        a: 'A refinance of a conventional loan where you\'re only changing the rate and/or term — not pulling cash out. Standard full underwrite applies (appraisal, income, credit) but you may be able to eliminate PMI if your home value has appreciated.',
      },
      {
        q: 'Can I switch from FHA to conventional when I refinance?',
        a: 'Yes — this is one of the most common moves. If you originally bought with FHA and now have 20% equity (via appreciation or paydown), refinancing to conventional eliminates the lifetime MIP. This alone can save $150–$250/month on a typical loan.',
      },
    ],
  },

  'cash-out-refi': {
    label: 'Cash-Out Refinance',
    icon: '💵',
    tagline: 'Turn your equity into liquid.',
    hero: '#1a1a2e',
    accentColor: '#a78bfa',
    summary: 'A Cash-Out Refinance replaces your existing mortgage with a new, larger loan — and you pocket the difference in cash. You\'re essentially converting built-up equity into spendable funds while resetting your mortgage terms. Popular for home improvements, debt consolidation, tuition, or investment.',
    pros: [
      'Access large amounts of equity (often $50K–$300K+)',
      'Lower interest rate than personal loans or credit cards',
      'Interest may be tax-deductible when used for home improvements (consult tax advisor)',
      'Single payment — no second mortgage complication',
      'Funds can be used for almost anything',
    ],
    cons: [
      'Higher balance = higher monthly payment than your current mortgage',
      'You\'re resetting the clock on amortization',
      'If you pull too much equity, you\'re exposed if home values dip',
      'Closing costs apply (~2–5% of new loan amount)',
      'Requires full underwrite: credit, income, appraisal',
    ],
    faqs: [
      {
        q: 'How much can I cash out?',
        a: 'Most conventional lenders allow up to 80% LTV (loan-to-value). Example: $500K home, $250K owed → up to $400K new loan → $150K cash out, minus closing costs. FHA allows up to 80% LTV too. VA cash-out goes to 90%+ for eligible veterans.',
      },
      {
        q: 'What\'s the difference between a cash-out refi and a HELOC?',
        a: 'A HELOC is a revolving line (like a credit card) at a variable rate — you draw only what you need. A cash-out refi replaces your first mortgage with a fixed lump sum at a fixed rate. If rates are low, cash-out is usually better for large, one-time needs. HELOC works better for ongoing draws.',
      },
      {
        q: 'Can investors do cash-out refis?',
        a: 'Yes — DSCR loan products support cash-out for investment properties. This is how investors scale: buy, wait for appreciation, cash out equity, reinvest as down payment on the next property.',
      },
      {
        q: 'What credit score do I need?',
        a: 'Conventional cash-out typically requires 620+, with better terms above 680–720. FHA cash-out starts at 500 (with 10% equity remaining) but practically most lenders want 580+.',
      },
    ],
  },
}

export default function ProductDetail() {
  const { slug } = useParams()
  const [showIntake, setShowIntake] = useState(false)
  const content = CONTENT[slug]

  if (!content) {
    return (
      <div style={{ minHeight: '100vh' }}>
        <RateTicker />
        <Nav />
        <div style={{ padding: '80px 24px', textAlign: 'center' }}>
          <h2 style={{ color: '#1f1f1f' }}>Page not found</h2>
          <Link to="/learn" style={{ color: '#1f1f1f', fontWeight: 600 }}>← Back to Learn</Link>
        </div>
        <Footer />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* Hero */}
      <div style={{ background: content.hero || '#1f1f1f', padding: '52px 24px 44px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <Link to="/learn" style={{ color: '#666', fontSize: '0.8rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 16 }}>
            ← Back to Learn
          </Link>
          <div style={{ fontSize: '2.5rem', marginBottom: 10 }}>{content.icon}</div>
          <h1 style={{ margin: '0 0 6px', color: '#fff', fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', fontWeight: 900, lineHeight: 1.1 }}>
            {content.label}
          </h1>
          <p style={{ margin: 0, color: '#888', fontSize: '1.0625rem', fontStyle: 'italic' }}>{content.tagline}</p>
        </div>
      </div>

      <div style={{ flex: 1, padding: '40px 24px 64px', background: '#fafaf9' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          {/* Summary */}
          <div style={{ background: '#fff', border: '1px solid #ede8e0', borderRadius: 10, padding: '24px 26px', marginBottom: 20 }}>
            <p style={{ margin: 0, fontSize: '1rem', color: '#333', lineHeight: 1.7 }}>{content.summary}</p>
          </div>

          {/* Pros / Cons */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20 }} className="pros-cons">
            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, padding: '20px 22px' }}>
              <div style={{ fontWeight: 700, color: '#166534', fontSize: '0.875rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                ✅ Advantages
              </div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {content.pros.map(p => (
                  <li key={p} style={{ fontSize: '0.875rem', color: '#166534', display: 'flex', gap: 8, lineHeight: 1.45 }}>
                    <span style={{ color: '#4ade80', flexShrink: 0 }}>•</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '20px 22px' }}>
              <div style={{ fontWeight: 700, color: '#991b1b', fontSize: '0.875rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                ⚠️ Considerations
              </div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {content.cons.map(c => (
                  <li key={c} style={{ fontSize: '0.875rem', color: '#991b1b', display: 'flex', gap: 8, lineHeight: 1.45 }}>
                    <span style={{ color: '#f87171', flexShrink: 0 }}>•</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* FAQ */}
          {content.faqs?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h2 style={{ margin: '0 0 14px', fontSize: '1.1rem', fontWeight: 800, color: '#1f1f1f' }}>
                Common Questions
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {content.faqs.map(faq => (
                  <div key={faq.q} style={{ background: '#fff', border: '1px solid #ede8e0', borderRadius: 8, padding: '16px 18px' }}>
                    <div style={{ fontWeight: 700, color: '#1f1f1f', fontSize: '0.9rem', marginBottom: 6 }}>Q: {faq.q}</div>
                    <div style={{ fontSize: '0.875rem', color: '#555', lineHeight: 1.6 }}>{faq.a}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Content-specific secondary CTA */}
          {content.ctaLink && (
            <div style={{ marginBottom: 20 }}>
              <Link
                to={content.ctaLink}
                style={{
                  padding: '12px 22px', background: '#f5c87a', color: '#1f1f1f',
                  borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                  textDecoration: 'none', display: 'inline-block',
                }}
              >
                {content.ctaLabel}
              </Link>
            </div>
          )}

          {/* CTA card */}
          <div style={{ background: '#1f1f1f', borderRadius: 12, padding: '28px', textAlign: 'center' }}>
            <h3 style={{ margin: '0 0 8px', color: '#fff', fontSize: '1.15rem', fontWeight: 800 }}>
              Is a {content.label} right for you?
            </h3>
            <p style={{ margin: '0 0 20px', color: '#888', fontSize: '0.9rem' }}>
              Let me run your numbers — no credit pull, no pressure.
            </p>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '12px 28px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                cursor: 'pointer',
              }}
            >
              Get My Numbers
            </button>
          </div>

          <p style={{ marginTop: 16, fontSize: '0.7rem', color: '#bbb', lineHeight: 1.6 }}>
            All information is for educational purposes only. Not a commitment to lend. Program terms and rates
            subject to change. NMLS #{BANKER_NMLS}. Equal Housing Opportunity.
          </p>
        </div>
      </div>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger={`Is a ${content.label} right for me?`}
          contextNote={`Let me walk you through your ${content.label} options — quick and no credit pull.`}
          onClose={() => setShowIntake(false)}
        />
      )}

      <style>{`
        @media (max-width: 600px) {
          .pros-cons { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}

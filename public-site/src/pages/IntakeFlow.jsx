import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, ArrowLeft, Shield, CheckCircle } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

const LOAN_TYPES = [
  { value: 'purchase', label: '🏠 Buy a Home', sub: 'FHA, conventional, VA, USDA' },
  { value: 'dpa', label: '💰 Down Payment Assistance', sub: 'Programs up to $25K+' },
  { value: 'dscr_investor', label: '📈 DSCR Investor Loan', sub: 'Qualify on rental income' },
  { value: 'heloc', label: '🔑 HELOC / Cash-Out', sub: 'Tap your home equity' },
  { value: 'refinance', label: '🔄 Refinance', sub: 'Rate/term or cash-out refi' },
  { value: 'realtor', label: '🤝 Realtor Partnership', sub: 'Tools for your buyers' },
]

const CREDIT_RANGES = [
  { value: 'below_580', label: 'Below 580', color: '#ef4444' },
  { value: '580_619', label: '580–619', color: '#f97316' },
  { value: '620_659', label: '620–659', color: '#eab308' },
  { value: '660_699', label: '660–699', color: '#84cc16' },
  { value: '700_739', label: '700–739', color: '#22c55e' },
  { value: '740_plus', label: '740+', color: '#10b981' },
  { value: 'unknown', label: "Not sure", color: '#6b7280' },
]

const INCOME_RANGES = [
  { value: 'below_30k', label: 'Under $30K' },
  { value: '30k_50k', label: '$30K–$50K' },
  { value: '50k_75k', label: '$50K–$75K' },
  { value: '75k_100k', label: '$75K–$100K' },
  { value: '100k_150k', label: '$100K–$150K' },
  { value: '150k_plus', label: '$150K+' },
]

const TIMELINES = [
  { value: 'asap', label: 'ASAP (ready now)' },
  { value: 'within_30_days', label: 'Within 30 days' },
  { value: 'within_90_days', label: '1–3 months' },
  { value: 'within_6_months', label: '3–6 months' },
  { value: 'within_1_year', label: '6–12 months' },
  { value: 'just_exploring', label: 'Just exploring' },
]

const CASH_RANGES = [
  { value: 'under_1k', label: 'Under $1,000' },
  { value: '1k_5k', label: '$1K–$5K' },
  { value: '5k_15k', label: '$5K–$15K' },
  { value: '15k_30k', label: '$15K–$30K' },
  { value: '30k_plus', label: '$30K+' },
]

const PROPERTY_GOALS = [
  { value: 'primary_residence', label: 'Primary Home' },
  { value: 'investment', label: 'Investment Property' },
  { value: 'vacation', label: 'Vacation Home' },
  { value: 'refinance_existing', label: 'Refinance Existing' },
]

const TOTAL_STEPS = 6

export default function IntakeFlow() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const initialType = searchParams.get('type') || ''
  const [step, setStep] = useState(initialType ? 1 : 0)
  const [form, setForm] = useState({
    loan_interest_type: initialType,
    first_name: '', last_name: '', email: '', phone: '',
    city: '', state: '', county: '',
    credit_score_range: '', income_range: '', timeline: '',
    cash_available: '', current_rent_mortgage: '',
    property_goal: '',
    consent_email: false, consent_sms: false, consent_call: false,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))
  const next = () => setStep(s => Math.min(s + 1, TOTAL_STEPS))
  const back = () => setStep(s => Math.max(s - 1, 0))

  const submit = async () => {
    if (!form.consent_email && !form.consent_sms && !form.consent_call) {
      setError('Please select at least one contact preference.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_URL}/leads/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error('Submission failed')
      const data = await res.json()
      navigate('/thank-you', { state: { message: data.message, cta: data.recommended_cta } })
    } catch {
      setError('Something went wrong. Please try again or call us directly.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      {/* LEFT — progress/brand strip */}
      <div className="split-left" style={{
        width: '38%', padding: '48px 48px',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      }}>
        <div>
          <a href="/" style={{ textDecoration: 'none', fontWeight: 900, fontSize: '1.2rem', color: 'var(--color-inkwell)' }}>
            Mortgage<span style={{ color: '#b36b00' }}>Sesame</span>
          </a>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <h2 className="font-display-heavy" style={{ margin: 0, fontSize: '2rem' }}>
            Let's find<br />your loan.
          </h2>
          <p className="font-body-lg" style={{ margin: 0, color: '#555', maxWidth: '280px' }}>
            A few quick questions — no hard pull, no commitment.
            We'll match you with the right programs.
          </p>

          {/* Step progress */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '16px' }}>
            {['Loan Type', 'Contact Info', 'Location', 'Financial Picture', 'Timeline & Goals', 'Consent'].map((label, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '24px', height: '24px', borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.7rem', fontWeight: 700,
                  background: step > i ? '#0d0d0d' : step === i ? '#b36b00' : 'transparent',
                  border: step > i ? 'none' : step === i ? 'none' : '1.5px solid #ccc',
                  color: step > i ? 'white' : step === i ? 'white' : '#999',
                  transition: 'all 0.2s',
                }}>
                  {step > i ? <CheckCircle size={13} /> : i + 1}
                </div>
                <span style={{
                  fontSize: '0.8125rem',
                  color: step === i ? 'var(--color-inkwell)' : step > i ? '#555' : '#aaa',
                  fontWeight: step === i ? 600 : 400,
                }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Shield size={12} color="#999" />
          <span style={{ fontSize: '0.7rem', color: '#999' }}>No credit pull · Private · Equal Housing</span>
        </div>
      </div>

      {/* RIGHT — Carbon step panel */}
      <div className="split-right" style={{
        flex: 1, padding: '48px 56px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
      }}>
        <StepContent step={step} form={form} set={set} />

        {error && (
          <p style={{ color: '#ef4444', fontSize: '0.875rem', marginTop: '16px' }}>{error}</p>
        )}

        {/* Navigation */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '32px', alignItems: 'center' }}>
          {step > 0 && (
            <button onClick={back} className="btn-primary" style={{ background: 'transparent', color: '#888', border: '1px solid #333' }}>
              <ArrowLeft size={14} /> Back
            </button>
          )}
          {step < TOTAL_STEPS ? (
            <button onClick={next} className="btn-warm" disabled={!canAdvance(step, form)}>
              Continue <ArrowRight size={14} />
            </button>
          ) : (
            <button onClick={submit} className="btn-warm" disabled={loading}>
              {loading ? 'Submitting...' : 'Submit →'}
            </button>
          )}
          <span style={{ fontSize: '0.75rem', color: '#555', marginLeft: 'auto' }}>
            Step {step + 1} of {TOTAL_STEPS + 1}
          </span>
        </div>

        <p style={{ marginTop: '24px', fontSize: '0.7rem', color: '#555', lineHeight: 1.5, maxWidth: '420px' }}>
          For educational purposes only. Not a commitment to lend. All loans subject to credit approval,
          income verification, and underwriting. Results may vary. Equal Housing Opportunity.
          NMLS# [YOUR_NMLS].
        </p>
      </div>
    </div>
  )
}

function StepContent({ step, form, set }) {
  switch (step) {
    case 0: return <StepLoanType form={form} set={set} />
    case 1: return <StepContact form={form} set={set} />
    case 2: return <StepLocation form={form} set={set} />
    case 3: return <StepFinancial form={form} set={set} />
    case 4: return <StepTimeline form={form} set={set} />
    case 5: return <StepConsent form={form} set={set} />
    case 6: return <StepReview form={form} />
    default: return null
  }
}

function canAdvance(step, form) {
  if (step === 0) return !!form.loan_interest_type
  if (step === 1) return !!(form.first_name && form.email)
  return true
}

/* ── Step 0: Loan Type ─────────────────────────────────────────────── */
function StepLoanType({ form, set }) {
  return (
    <div className="fade-up">
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: '0 0 8px' }}>
        What are you looking to do?
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: '0 0 24px' }}>Pick the one that fits best — you can always change it.</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {LOAN_TYPES.map(({ value, label, sub }) => (
          <button key={value} onClick={() => set('loan_interest_type', value)}
            style={{
              background: form.loan_interest_type === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
              border: `1.5px solid ${form.loan_interest_type === value ? '#f5c87a' : '#333'}`,
              borderRadius: '8px', padding: '14px 16px', cursor: 'pointer', textAlign: 'left',
              transition: 'all 0.15s',
            }}>
            <p style={{ margin: '0 0 4px', color: 'var(--color-paper)', fontWeight: 500, fontSize: '0.875rem' }}>{label}</p>
            <p style={{ margin: 0, color: '#888', fontSize: '0.75rem' }}>{sub}</p>
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── Step 1: Contact ────────────────────────────────────────────────── */
function StepContact({ form, set }) {
  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        How do we reach you?
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: '0 0 8px' }}>We'll only contact you through channels you approve below.</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div>
          <label style={labelStyle}>First Name *</label>
          <input className="input-field" placeholder="Jane" value={form.first_name} onChange={e => set('first_name', e.target.value)} />
        </div>
        <div>
          <label style={labelStyle}>Last Name</label>
          <input className="input-field" placeholder="Smith" value={form.last_name} onChange={e => set('last_name', e.target.value)} />
        </div>
      </div>
      <div>
        <label style={labelStyle}>Email Address *</label>
        <input className="input-field" type="email" placeholder="jane@email.com" value={form.email} onChange={e => set('email', e.target.value)} />
      </div>
      <div>
        <label style={labelStyle}>Phone Number</label>
        <input className="input-field" type="tel" placeholder="(555) 000-0000" value={form.phone} onChange={e => set('phone', e.target.value)} />
      </div>
    </div>
  )
}

/* ── Step 2: Location ───────────────────────────────────────────────── */
function StepLocation({ form, set }) {
  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        Where are you located?
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: '0 0 8px' }}>
        Loan programs, rates, and DPA availability vary by location.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div>
          <label style={labelStyle}>State</label>
          <input className="input-field" placeholder="TX" value={form.state} onChange={e => set('state', e.target.value)} />
        </div>
        <div>
          <label style={labelStyle}>County</label>
          <input className="input-field" placeholder="Harris County" value={form.county} onChange={e => set('county', e.target.value)} />
        </div>
      </div>
      <div>
        <label style={labelStyle}>City</label>
        <input className="input-field" placeholder="Houston" value={form.city} onChange={e => set('city', e.target.value)} />
      </div>
    </div>
  )
}

/* ── Step 3: Financial ──────────────────────────────────────────────── */
function StepFinancial({ form, set }) {
  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        Financial picture
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: 0 }}>Estimates are fine — this is for program matching only.</p>

      <div>
        <label style={labelStyle}>Credit Score Range</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginTop: '8px' }}>
          {CREDIT_RANGES.map(({ value, label, color }) => (
            <button key={value} onClick={() => set('credit_score_range', value)} style={{
              background: form.credit_score_range === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
              border: `1.5px solid ${form.credit_score_range === value ? '#f5c87a' : '#333'}`,
              borderRadius: '6px', padding: '10px 8px', cursor: 'pointer',
              color: form.credit_score_range === value ? '#f5c87a' : '#aaa',
              fontSize: '0.8rem', fontWeight: 500, transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>
      </div>

      <div>
        <label style={labelStyle}>Approximate Annual Income</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '8px' }}>
          {INCOME_RANGES.map(({ value, label }) => (
            <button key={value} onClick={() => set('income_range', value)} style={{
              background: form.income_range === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
              border: `1.5px solid ${form.income_range === value ? '#f5c87a' : '#333'}`,
              borderRadius: '6px', padding: '10px 8px', cursor: 'pointer',
              color: form.income_range === value ? '#f5c87a' : '#aaa',
              fontSize: '0.8rem', fontWeight: 500, transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div>
          <label style={labelStyle}>Cash Available (Down / Closing)</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
            {CASH_RANGES.map(({ value, label }) => (
              <button key={value} onClick={() => set('cash_available', value)} style={{
                background: form.cash_available === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
                border: `1.5px solid ${form.cash_available === value ? '#f5c87a' : '#333'}`,
                borderRadius: '6px', padding: '8px 12px', cursor: 'pointer',
                color: form.cash_available === value ? '#f5c87a' : '#aaa',
                fontSize: '0.8rem', textAlign: 'left', transition: 'all 0.15s',
              }}>{label}</button>
            ))}
          </div>
        </div>
        <div>
          <label style={labelStyle}>Current Rent or Mortgage / mo</label>
          <input className="input-field" placeholder="$1,800" value={form.current_rent_mortgage}
            onChange={e => set('current_rent_mortgage', e.target.value)} style={{ marginTop: '8px' }} />
        </div>
      </div>
    </div>
  )
}

/* ── Step 4: Timeline & Goals ────────────────────────────────────────── */
function StepTimeline({ form, set }) {
  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        Timeline & property goal
      </h3>

      <div>
        <label style={labelStyle}>When are you looking to move?</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
          {TIMELINES.map(({ value, label }) => (
            <button key={value} onClick={() => set('timeline', value)} style={{
              background: form.timeline === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
              border: `1.5px solid ${form.timeline === value ? '#f5c87a' : '#333'}`,
              borderRadius: '6px', padding: '12px 16px', cursor: 'pointer',
              color: form.timeline === value ? '#f5c87a' : '#ccc',
              fontSize: '0.875rem', textAlign: 'left', transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>
      </div>

      <div>
        <label style={labelStyle}>Property Goal</label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '8px' }}>
          {PROPERTY_GOALS.map(({ value, label }) => (
            <button key={value} onClick={() => set('property_goal', value)} style={{
              background: form.property_goal === value ? 'rgba(245,200,122,0.15)' : 'var(--color-carbon-light)',
              border: `1.5px solid ${form.property_goal === value ? '#f5c87a' : '#333'}`,
              borderRadius: '6px', padding: '12px', cursor: 'pointer',
              color: form.property_goal === value ? '#f5c87a' : '#aaa',
              fontSize: '0.8rem', fontWeight: 500, textAlign: 'center', transition: 'all 0.15s',
            }}>{label}</button>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ── Step 5: Consent ─────────────────────────────────────────────────── */
function StepConsent({ form, set }) {
  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        How can we follow up?
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: 0 }}>
        Choose how you'd like us to reach you. You can opt out any time.
      </p>

      {[
        { key: 'consent_email', label: 'Email', sub: 'Loan summaries, program updates, follow-up info' },
        { key: 'consent_sms', label: 'Text / SMS', sub: 'Quick updates and scheduling (msg & data rates may apply)' },
        { key: 'consent_call', label: 'Phone Call', sub: 'Direct call from our licensed mortgage banker' },
      ].map(({ key, label, sub }) => (
        <label key={key} style={{
          display: 'flex', alignItems: 'flex-start', gap: '14px',
          background: form[key] ? 'rgba(245,200,122,0.08)' : 'var(--color-carbon-light)',
          border: `1.5px solid ${form[key] ? '#f5c87a' : '#333'}`,
          borderRadius: '8px', padding: '16px', cursor: 'pointer', transition: 'all 0.15s',
        }}>
          <input type="checkbox" className="checkbox-warm" checked={form[key]}
            onChange={e => set(key, e.target.checked)} style={{ marginTop: '2px' }} />
          <div>
            <p style={{ margin: '0 0 3px', fontWeight: 600, color: 'var(--color-paper)', fontSize: '0.9rem' }}>{label}</p>
            <p style={{ margin: 0, color: '#888', fontSize: '0.8rem' }}>{sub}</p>
          </div>
        </label>
      ))}

      <p style={{ fontSize: '0.7rem', color: '#555', lineHeight: 1.6 }}>
        By submitting, you agree to be contacted regarding your mortgage inquiry.
        We will never sell your information. Opt out any time by replying STOP (SMS),
        clicking unsubscribe (email), or calling us. Your data is handled per our Privacy Policy.
        This is not a credit application. Not a commitment to lend. All loans subject to approval.
        NMLS# [YOUR_NMLS] · Equal Housing Opportunity Lender.
      </p>
    </div>
  )
}

/* ── Step 6: Review ─────────────────────────────────────────────────── */
function StepReview({ form }) {
  const loanLabel = LOAN_TYPES.find(l => l.value === form.loan_interest_type)?.label || form.loan_interest_type
  const creditLabel = CREDIT_RANGES.find(c => c.value === form.credit_score_range)?.label || '—'
  const incomeLabel = INCOME_RANGES.find(i => i.value === form.income_range)?.label || '—'
  const timelineLabel = TIMELINES.find(t => t.value === form.timeline)?.label || '—'

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 style={{ color: 'var(--color-paper)', fontWeight: 700, fontSize: '1.375rem', margin: 0 }}>
        Review your information
      </h3>
      <p style={{ color: '#888', fontSize: '0.875rem', margin: 0 }}>Look good? Hit Submit and we'll be in touch.</p>

      <div className="card-dark" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        {[
          ['Loan Type', loanLabel],
          ['Name', `${form.first_name} ${form.last_name}`],
          ['Email', form.email],
          ['Phone', form.phone || '—'],
          ['Location', [form.city, form.state].filter(Boolean).join(', ') || '—'],
          ['Credit Range', creditLabel],
          ['Income', incomeLabel],
          ['Timeline', timelineLabel],
          ['Cash Available', CASH_RANGES.find(c => c.value === form.cash_available)?.label || '—'],
        ].map(([label, value]) => (
          <div key={label}>
            <p style={{ margin: '0 0 2px', fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</p>
            <p style={{ margin: 0, color: 'var(--color-paper)', fontSize: '0.875rem' }}>{value}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        {[
          form.consent_email && '✉️ Email',
          form.consent_sms && '📱 SMS',
          form.consent_call && '📞 Call',
        ].filter(Boolean).map(c => (
          <span key={c} className="badge badge-warm">{c}</span>
        ))}
      </div>
    </div>
  )
}

const labelStyle = {
  display: 'block', fontSize: '0.8rem', color: '#888',
  marginBottom: '6px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px',
}

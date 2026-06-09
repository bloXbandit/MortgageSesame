import { BANKER_NMLS, SERVICE_STATES } from '../config'
import { useState, useEffect } from 'react'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'
import DpaCard from '../components/DpaCard'
import MicroIntake from '../components/MicroIntake'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATE_FILTERS = [
  { value: '',   label: 'All States' },
  { value: 'MD', label: 'Maryland' },
  { value: 'DC', label: 'Washington DC' },
]

const TYPE_FILTERS = [
  { value: '',            label: 'All Types' },
  { value: 'grant',       label: 'Grant' },
  { value: 'forgivable',  label: 'Forgivable' },
  { value: 'deferred',    label: 'Deferred Loan' },
  { value: 'second_lien', label: 'Second Lien' },
]

export default function DpaHub() {
  const [programs, setPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [stateFilter, setStateFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showIntake, setShowIntake] = useState(false)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ active_only: 'true' })
    if (stateFilter) params.set('state', stateFilter)
    fetch(`${API}/api/v1/dpa/?${params}`)
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        let filtered = data
        if (typeFilter) filtered = data.filter(p => p.dpa_type === typeFilter)
        setPrograms(filtered)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [stateFilter, typeFilter])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* Hero */}
      <div style={{ background: '#1f1f1f', padding: '52px 24px 44px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
            Down Payment Assistance
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <h1 style={{ margin: '0 0 10px', color: '#fff', fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', fontWeight: 900, lineHeight: 1.1 }}>
                MD & DC Down Payment Programs
              </h1>
              <p style={{ margin: 0, color: '#888', fontSize: '1rem', maxWidth: 520, lineHeight: 1.65 }}>
                Grants, forgivable loans, and deferred seconds — Maryland and DC have programs
                that can cover your entire down payment. Most buyers don't know they qualify.
              </p>
            </div>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '12px 22px', background: '#f5c87a', color: '#1f1f1f',
                border: 'none', borderRadius: 7, fontWeight: 700, fontSize: '0.9375rem',
                cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                marginTop: 4,
              }}
            >
              Check My Eligibility
            </button>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div style={{ background: '#2a2a2a', padding: '16px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          {[
            ['$202,000+', 'Max DC HPAP amount'],
            ['$40,000', 'Max Howard Co. MD amount'],
            ['3.5%', 'FHA min down — DPA can cover it'],
            ['$0 out-of-pocket', 'Possible with stacking programs'],
          ].map(([val, sub]) => (
            <div key={val}>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f5c87a' }}>{val}</div>
              <div style={{ fontSize: '0.7rem', color: '#666', marginTop: 1 }}>{sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ background: '#fff', borderBottom: '1px solid #ede8e0', padding: '14px 24px', position: 'sticky', top: 58, zIndex: 30 }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', color: '#888', fontWeight: 500, marginRight: 4 }}>State:</span>
          {STATE_FILTERS.map(f => (
            <FilterBtn key={f.value} label={f.label} active={stateFilter === f.value} onClick={() => setStateFilter(f.value)} />
          ))}
          <span style={{ fontSize: '0.8rem', color: '#888', fontWeight: 500, marginLeft: 12, marginRight: 4 }}>Type:</span>
          {TYPE_FILTERS.map(f => (
            <FilterBtn key={f.value} label={f.label} active={typeFilter === f.value} onClick={() => setTypeFilter(f.value)} />
          ))}
          {programs.length > 0 && (
            <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#999' }}>
              {programs.length} program{programs.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Programs list */}
      <div style={{ flex: 1, padding: '32px 24px 64px', background: '#fafaf9' }}>
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#999' }}>
              <div style={{ fontSize: '2rem', marginBottom: 12 }}>💰</div>
              Loading programs…
            </div>
          ) : programs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '80px 0' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>🔍</div>
              <h3 style={{ margin: '0 0 8px', color: '#1f1f1f', fontWeight: 700 }}>No programs found</h3>
              <p style={{ color: '#888', margin: '0 0 20px' }}>
                Try adjusting your filters, or ask us directly.
              </p>
              <button
                onClick={() => setShowIntake(true)}
                style={{
                  padding: '11px 22px', background: '#1f1f1f', color: '#f5c87a',
                  border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer',
                }}
              >
                Check My Eligibility
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {programs.map(p => <DpaCard key={p.id} program={p} />)}
            </div>
          )}
        </div>
      </div>

      {/* Bottom explainer */}
      <section style={{ background: '#1f1f1f', padding: '56px 24px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <h2 style={{ margin: '0 0 20px', color: '#fff', fontSize: 'clamp(1.4rem, 3vw, 1.9rem)', fontWeight: 800 }}>
            How DPA programs actually work
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
            {[
              { type: 'Grant', icon: '🎁', desc: 'Free money — no repayment required. Rarest type. Usually small amounts or specific to certain professions.' },
              { type: 'Forgivable Loan', icon: '✅', desc: 'Loan that gets "forgiven" over time — typically 3–10 years. Stay in the home and the balance disappears.' },
              { type: 'Deferred Loan', icon: '⏸️', desc: '0% interest, no monthly payment. Full balance due when you sell, refinance, or move out. Very common in MD/DC.' },
              { type: 'Second Lien', icon: '🏛️', desc: 'A second mortgage, usually at low or 0% interest. May have monthly payments or may be deferred.' },
            ].map(({ type, icon, desc }) => (
              <div key={type} style={{ background: '#2a2a2a', border: '1px solid #333', borderRadius: 8, padding: '18px' }}>
                <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>{icon}</div>
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.9375rem', marginBottom: 6 }}>{type}</div>
                <div style={{ fontSize: '0.8rem', color: '#888', lineHeight: 1.55 }}>{desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 28, padding: '16px 18px', background: '#252525', border: '1px solid #333', borderRadius: 8 }}>
            <p style={{ margin: 0, fontSize: '0.8125rem', color: '#666', lineHeight: 1.6 }}>
              <strong style={{ color: '#888' }}>Note:</strong> DPA program details, income limits, and availability change frequently.
              Information shown here is for educational purposes. Verify current requirements directly with
              the administering agency or contact us for current guidance. NMLS #{BANKER_NMLS}.
            </p>
          </div>
        </div>
      </section>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger="Let's check your DPA eligibility."
          contextNote="Tell me a bit about yourself and I'll identify which programs you might qualify for."
          onClose={() => setShowIntake(false)}
        />
      )}
    </div>
  )
}

function FilterBtn({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '5px 13px', borderRadius: 99,
        border: '1px solid', borderColor: active ? '#1f1f1f' : '#ddd',
        background: active ? '#1f1f1f' : 'transparent',
        color: active ? '#fff' : '#555',
        fontSize: '0.8125rem', fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )
}

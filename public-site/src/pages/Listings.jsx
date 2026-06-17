import { CALCOM, APP_1003, BANKER_NMLS, SERVICE_STATES } from '../config'
import { useState, useEffect } from 'react'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'
import ListingCard from '../components/ListingCard'
import { useCurrentRates } from '../hooks/useRates'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS_FILTERS = [
  { value: '',                 label: 'All Active' },
  { value: 'active',           label: 'Active' },
  { value: 'coming_soon',      label: 'Coming Soon' },
  { value: 'under_contract',   label: 'Under Contract' },
]

export default function Listings() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const { rates } = useCurrentRates()

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    fetch(`${API}/api/v1/listings/?${params}`)
      .then(r => r.ok ? r.json() : [])
      .then(data => { setListings(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [statusFilter])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <RateTicker />
      <Nav />

      {/* Header */}
      <div style={{ background: '#1f1f1f', padding: '48px 24px 40px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 6 }}>
            Maryland & DC
          </div>
          <h1 style={{ margin: '0 0 10px', color: '#fff', fontSize: 'clamp(1.8rem, 4vw, 2.8rem)', fontWeight: 900, lineHeight: 1.1 }}>
            Homes with real numbers.
          </h1>
          <p style={{ margin: 0, color: '#888', fontSize: '1rem', maxWidth: 500 }}>
            Every listing shows a full FHA, Conventional, and DSCR payment breakdown.
            Tap "See Your Numbers" on any home to get a personalized estimate.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ background: '#faf6f0', borderBottom: '1px solid #ede8e0', padding: '14px 24px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', color: '#888', fontWeight: 500, marginRight: 4 }}>Show:</span>
          {STATUS_FILTERS.map(f => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              style={{
                padding: '5px 14px',
                borderRadius: 99,
                border: '1px solid',
                borderColor: statusFilter === f.value ? '#1f1f1f' : '#ddd',
                background: statusFilter === f.value ? '#1f1f1f' : 'transparent',
                color: statusFilter === f.value ? '#fff' : '#555',
                fontSize: '0.8125rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {f.label}
            </button>
          ))}
          {listings.length > 0 && (
            <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#999' }}>
              {listings.length} {listings.length === 1 ? 'home' : 'homes'}
            </span>
          )}
        </div>
      </div>

      {/* Grid */}
      <div style={{ flex: 1, padding: '36px 24px 60px', background: '#faf6f0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#999' }}>
              <div style={{ fontSize: '2rem', marginBottom: 12 }}>🏡</div>
              Loading homes…
            </div>
          ) : listings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '80px 0' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>🏗️</div>
              <h2 style={{ margin: '0 0 8px', color: '#1f1f1f', fontSize: '1.3rem', fontWeight: 700 }}>
                No listings yet
              </h2>
              <p style={{ margin: '0 0 24px', color: '#888' }}>
                Check back soon — or get ahead of the market now.
              </p>
              <a
                href={CALCOM}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: '12px 24px', background: '#1f1f1f', color: '#f5c87a',
                  borderRadius: 7, fontWeight: 600, fontSize: '0.9375rem',
                  textDecoration: 'none',
                }}
              >
                Book a Free Consultation
              </a>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 22 }}>
              {listings.map(l => <ListingCard key={l.id} listing={l} rates={rates} />)}
            </div>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div style={{ background: '#fff', borderTop: '1px solid #ede8e0', padding: '16px 24px' }}>
        <p style={{ maxWidth: 1100, margin: '0 auto', fontSize: '0.7rem', color: '#aaa', lineHeight: 1.6 }}>
          All payment estimates shown are for educational purposes only. Not a rate lock or commitment to lend.
          Payment estimates use current FRED weekly average rates as a baseline. Actual rate depends on credit score, down payment, and loan type. Estimates may not reflect current market conditions.
          NMLS #{BANKER_NMLS}.
        </p>
      </div>

      <Footer />
    </div>
  )
}

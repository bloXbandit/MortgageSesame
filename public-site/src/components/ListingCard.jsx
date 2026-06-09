import { useState } from 'react'
import MicroIntake from './MicroIntake'

const STATUS_STYLES = {
  active:           { bg: '#dcfce7', color: '#166534', label: 'Active' },
  coming_soon:      { bg: '#fff3dc', color: '#92520b', label: 'Coming Soon' },
  under_contract:   { bg: '#fef9c3', color: '#713f12', label: 'Under Contract' },
  sold:             { bg: '#f1f5f9', color: '#64748b', label: 'Sold' },
}

function fmt(n) {
  if (!n && n !== 0) return '—'
  return '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

function ScenarioPanel({ label, accentColor, totalMo, closing, multiplierPct }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e8e2d8', borderRadius: 7, padding: '9px 10px' }}>
      <div style={{ fontSize: '0.65rem', fontWeight: 700, color: accentColor, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6, lineHeight: 1.2 }}>
        {label}
      </div>
      <div style={{ marginBottom: 5 }}>
        <div style={{ color: '#aaa', fontSize: '0.65rem' }}>Monthly est.</div>
        <div style={{ fontWeight: 800, fontSize: '0.9rem', color: '#1f1f1f', lineHeight: 1.1 }}>
          ~{fmt(totalMo)}<span style={{ fontSize: '0.65rem', fontWeight: 400, color: '#999' }}>/mo</span>
        </div>
      </div>
      <div style={{ borderTop: '1px solid #f0ece4', paddingTop: 5 }}>
        <div style={{ color: '#aaa', fontSize: '0.65rem' }}>Est. Cash to Close ({multiplierPct})</div>
        <div style={{ fontWeight: 800, color: '#1f1f1f', fontSize: '0.9rem' }}>~{fmt(closing)}</div>
      </div>
    </div>
  )
}

/**
 * Quick inline estimate — same multipliers as calculator.py
 * No API call needed; runs purely from list_price.
 */
function estimatePayments(price) {
  const piRate = (annualRate, years) => {
    const mo = annualRate / 100 / 12
    const n = years * 12
    if (mo === 0) return 0
    return mo * Math.pow(1 + mo, n) / (Math.pow(1 + mo, n) - 1)
  }

  const taxesMo = (price * 0.011) / 12
  const insMo   = (price * 0.005) / 12

  // FHA — 3.5% down, 6.75%, 1.75% upfront MIP rolled in, 0.55% annual MIP
  const fhaDown    = price * 0.035
  const fhaBase    = price - fhaDown
  const fhaLoan    = fhaBase * 1.0175
  const fhaPi      = fhaLoan * piRate(6.75, 30)
  const fhaMip     = fhaBase * 0.0055 / 12
  const fhaTotalMo = Math.round(fhaPi + fhaMip + taxesMo + insMo)
  const fhaClosing = Math.round(price * 0.07)   // 7% of sale price
  const fhaCash    = Math.round(fhaDown) + fhaClosing

  // Conventional 3% down — 7.00%, 0.7% PMI, 6.5% closing cost multiplier
  const conv3Down    = price * 0.03
  const conv3Loan    = price - conv3Down
  const conv3Pi      = conv3Loan * piRate(7.00, 30)
  const conv3Pmi     = conv3Loan * 0.007 / 12
  const conv3TotalMo = Math.round(conv3Pi + conv3Pmi + taxesMo + insMo)
  const conv3Closing = Math.round(price * 0.065) // 6.5% of sale price
  const conv3Cash    = Math.round(conv3Down) + conv3Closing

  // Conventional 5% down — 7.00%, 0.7% PMI, 8.5% closing cost multiplier
  const conv5Down    = price * 0.05
  const conv5Loan    = price - conv5Down
  const conv5Pi      = conv5Loan * piRate(7.00, 30)
  const conv5Pmi     = conv5Loan * 0.007 / 12
  const conv5TotalMo = Math.round(conv5Pi + conv5Pmi + taxesMo + insMo)
  const conv5Closing = Math.round(price * 0.085) // 8.5% of sale price
  const conv5Cash    = Math.round(conv5Down) + conv5Closing

  return {
    fhaTotalMo,  fhaClosing,  fhaCash,  fhaDown:  Math.round(fhaDown),
    conv3TotalMo, conv3Closing, conv3Cash, conv3Down: Math.round(conv3Down),
    conv5TotalMo, conv5Closing, conv5Cash, conv5Down: Math.round(conv5Down),
  }
}

export default function ListingCard({ listing }) {
  const [showIntake,    setShowIntake]    = useState(false)
  const [showEstimates, setShowEstimates] = useState(false)
  const status = STATUS_STYLES[listing.status] || STATUS_STYLES.active
  const est    = estimatePayments(listing.list_price || 0)

  return (
    <>
      <div style={{
        background: '#fff',
        borderRadius: 10,
        overflow: 'hidden',
        border: '1px solid #ede8e0',
        transition: 'box-shadow 0.18s, transform 0.18s',
      }}
        onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
        onMouseLeave={e => { e.currentTarget.style.boxShadow = ''; e.currentTarget.style.transform = '' }}
      >
        {/* Photo */}
        <div style={{ position: 'relative', height: 188, background: '#f0ece4', overflow: 'hidden' }}>
          {listing.photo_url ? (
            <img
              src={listing.photo_url}
              alt={listing.address}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="48" height="42" viewBox="0 0 48 42" fill="none" opacity="0.25">
                <path d="M24 3L3 21H9V39H21V27H27V39H39V21H45L24 3Z" fill="#1f1f1f"/>
              </svg>
            </div>
          )}
          {/* Status badge */}
          <span style={{
            position: 'absolute', top: 10, left: 10,
            background: status.bg, color: status.color,
            padding: '3px 9px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600,
          }}>
            {status.label}
          </span>
          {listing.is_featured && (
            <span style={{
              position: 'absolute', top: 10, right: 10,
              background: '#1f1f1f', color: '#f5c87a',
              padding: '3px 9px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600,
            }}>
              Featured
            </span>
          )}
        </div>

        {/* Body */}
        <div style={{ padding: '16px 18px 18px' }}>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#1f1f1f', marginBottom: 2 }}>
            {fmt(listing.list_price)}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#444', marginBottom: 10, lineHeight: 1.4 }}>
            {listing.address}
            {listing.city && <>, {listing.city}, {listing.state}</>}
          </div>

          {/* Specs row */}
          <div style={{ display: 'flex', gap: 14, marginBottom: 14 }}>
            {listing.bedrooms && (
              <span style={{ fontSize: '0.8rem', color: '#666', display: 'flex', alignItems: 'center', gap: 4 }}>
                <svg width="14" height="10" viewBox="0 0 14 10" fill="none"><rect x="1" y="4" width="12" height="6" rx="1" stroke="#999" strokeWidth="1.2"/><rect x="2" y="1" width="4" height="4" rx="1" stroke="#999" strokeWidth="1.2"/><rect x="8" y="1" width="4" height="4" rx="1" stroke="#999" strokeWidth="1.2"/></svg>
                {listing.bedrooms} bed
              </span>
            )}
            {listing.bathrooms && (
              <span style={{ fontSize: '0.8rem', color: '#666' }}>
                {listing.bathrooms} bath
              </span>
            )}
            {listing.sqft && (
              <span style={{ fontSize: '0.8rem', color: '#666' }}>
                {listing.sqft.toLocaleString()} sqft
              </span>
            )}
            {listing.property_type && (
              <span style={{ fontSize: '0.8rem', color: '#999', marginLeft: 'auto', textTransform: 'capitalize' }}>
                {listing.property_type}
              </span>
            )}
          </div>

          {/* ── Quick Estimate Toggle ── */}
          <button
            onClick={() => setShowEstimates(v => !v)}
            style={{
              width: '100%', marginBottom: 8,
              padding: '8px 12px',
              background: showEstimates ? '#f5f0e8' : '#faf6f0',
              color: '#555',
              border: '1px solid #e8e2d8',
              borderRadius: 7,
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              transition: 'background 0.15s',
            }}
          >
            <span>📊 Est. Payments &amp; Closing Costs</span>
            <span style={{ color: '#aaa', fontWeight: 400 }}>{showEstimates ? '▲' : '▼'}</span>
          </button>

          {showEstimates && (
            <div style={{
              marginBottom: 10,
              background: '#faf6f0',
              border: '1px solid #ede8e0',
              borderRadius: 8,
              padding: '12px 14px',
              fontSize: '0.8125rem',
            }}>
              {/* Three-column grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 10 }}>
                {/* FHA column */}
                <ScenarioPanel
                  label="FHA · 3.5% dn"
                  accentColor="#92520b"
                  totalMo={est.fhaTotalMo}
                  closing={est.fhaClosing}
                  multiplierPct="7%"
                />
                <ScenarioPanel
                  label="Conv · 3% dn"
                  accentColor="#1e40af"
                  totalMo={est.conv3TotalMo}
                  closing={est.conv3Closing}
                  multiplierPct="6.5%"
                />
                <ScenarioPanel
                  label="Conv · 5% dn"
                  accentColor="#166534"
                  totalMo={est.conv5TotalMo}
                  closing={est.conv5Closing}
                  multiplierPct="8.5%"
                />
              </div>

              {/* Includes note */}
              <div style={{
                background: '#fffbf2',
                border: '1px solid #f0e0b0',
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: '0.7rem',
                color: '#7a5c1e',
                lineHeight: 1.5,
              }}>
                <strong>What's included in closing cost estimates:</strong> county/insurance escrow prepaids,
                basic title &amp; settlement fees, and lender origination costs — calculated as a multiplier
                of the sale price (FHA&nbsp;7%&nbsp;·&nbsp;Conv&nbsp;3%:&nbsp;6.5%&nbsp;·&nbsp;Conv&nbsp;5%:&nbsp;8.5%).
                <br/>
                <span style={{ color: '#999', marginTop: 4, display: 'block' }}>
                  ⚠ Raw estimate only — does <strong>not</strong> include specialized lender pricing,
                  seller concessions, or down payment assistance programs, any of which can
                  significantly reduce your actual out-of-pocket costs. Tap below for your real numbers.
                </span>
              </div>
            </div>
          )}

          {/* CTA */}
          <button
            onClick={() => setShowIntake(true)}
            style={{
              width: '100%',
              padding: '10px',
              background: '#1f1f1f',
              color: '#f5c87a',
              border: 'none',
              borderRadius: 7,
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#2a2a2a'}
            onMouseLeave={e => e.currentTarget.style.background = '#1f1f1f'}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7h10M7 2l5 5-5 5" stroke="#f5c87a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Get My Real Numbers
          </button>
        </div>
      </div>

      {showIntake && (
        <MicroIntake
          trigger={`What would it take to own ${listing.address}?`}
          contextNote={`Listed at ${fmt(listing.list_price)}${listing.city ? ` · ${listing.city}, ${listing.state}` : ''}`}
          onClose={() => setShowIntake(false)}
        />
      )}
    </>
  )
}

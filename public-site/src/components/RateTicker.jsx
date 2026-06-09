/**
 * RateTicker — full-width scrolling mortgage rate strip.
 * Shows all 8 loan types with day-over-day trend arrows.
 * Falls back to static rates when API data is missing.
 */
import { useRateTicker } from '../hooks/useRates'

// Fallback static rates when API returns null / empty
const FALLBACK_ITEMS = [
  { label: 'Conv 30yr',  rate: 7.00, change: 'flat', delta: 0 },
  { label: 'FHA 30yr',   rate: 6.75, change: 'flat', delta: 0 },
  { label: 'Conv 15yr',  rate: 6.25, change: 'flat', delta: 0 },
  { label: 'VA 30yr',    rate: 6.50, change: 'flat', delta: 0 },
  { label: 'USDA 30yr',  rate: 6.62, change: 'flat', delta: 0 },
  { label: 'DSCR',       rate: 8.00, change: 'flat', delta: 0 },
  { label: 'Jumbo 30yr', rate: 7.25, change: 'flat', delta: 0 },
  { label: 'HELOC',      rate: 8.50, change: 'flat', delta: 0 },
]

function TrendArrow({ change, delta, period }) {
  if (change === 'flat' || delta === 0) {
    return <span style={{ color: '#555', fontSize: '0.65rem' }}>—</span>
  }
  const isUp = change === 'up'
  const color = isUp ? '#ef4444' : '#22c55e' // red = higher rate (bad for buyers), green = lower (good)
  const arrow = isUp ? '▲' : '▼'
  const absDelta = Math.abs(delta).toFixed(2)
  const periodLabel = period === 'week' ? 'wk' : period === 'day' ? '' : period
  return (
    <span style={{ color, fontSize: '0.68rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 1 }}>
      {arrow}{absDelta}
      {periodLabel && (
        <span style={{ fontSize: '0.58rem', fontWeight: 400, opacity: 0.8, marginLeft: 1 }}>{periodLabel}</span>
      )}
    </span>
  )
}

export default function RateTicker() {
  const { ticker, loading } = useRateTicker()

  // Merge API data with fallback so all 8 products always appear
  const apiItems = ticker?.items || []
  const merged = FALLBACK_ITEMS.map((fb, idx) => {
    const api = apiItems[idx]
    if (!api) return fb
    return {
      label: api.label || fb.label,
      rate: api.rate !== null && api.rate !== undefined ? api.rate : fb.rate,
      change: api.change || 'flat',
      delta: api.delta !== undefined ? api.delta : 0,
    }
  })

  const asOf         = ticker?.as_of || null
  const changePeriod = ticker?.change_period || 'day'

  // Triple the list for seamless infinite marquee
  const tripled = [...merged, ...merged, ...merged]
  const scrollDuration = merged.length * 5 // seconds; slower = more readable

  return (
    <div
      style={{
        background: '#111',
        borderBottom: '1px solid #222',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 50,
        height: 40,
        display: 'flex',
        alignItems: 'center',
      }}
      aria-label="Live mortgage rate ticker"
    >
      {/* Left fade */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 60,
        background: 'linear-gradient(to right, #111, transparent)',
        zIndex: 2, pointerEvents: 'none',
      }} />
      {/* Right fade */}
      <div style={{
        position: 'absolute', right: 0, top: 0, bottom: 0, width: 60,
        background: 'linear-gradient(to left, #111, transparent)',
        zIndex: 2, pointerEvents: 'none',
      }} />

      {/* Scrolling track */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          animation: `tickerScroll ${scrollDuration}s linear infinite`,
          width: 'max-content',
        }}
      >
        {tripled.map((item, i) => (
          <span
            key={i}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              padding: '0 32px',
              borderRight: '1px solid #222',
              whiteSpace: 'nowrap',
              height: 40,
            }}
          >
            {/* Product label */}
            <span style={{
              color: '#999',
              fontSize: '0.7rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontWeight: 600,
            }}>
              {item.label}
            </span>

            {/* Rate value */}
            <span style={{
              color: '#f5c87a',
              fontSize: '0.9rem',
              fontWeight: 800,
              fontVariantNumeric: 'tabular-nums',
              minWidth: 52,
              textAlign: 'right',
            }}>
              {item.rate != null ? item.rate.toFixed(2) : '—'}%
            </span>

            {/* Trend arrow */}
            <TrendArrow change={item.change} delta={item.delta} period={changePeriod} />

            {/* As-of inline (only on first loop) */}
            {i === 0 && asOf && (
              <span style={{
                color: '#444',
                fontSize: '0.6rem',
                letterSpacing: '0.05em',
                marginLeft: 8,
                fontWeight: 400,
              }}>
                {asOf}
              </span>
            )}
          </span>
        ))}
      </div>

      <style>{`
        @keyframes tickerScroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(calc(-100% / 3)); }
        }
      `}</style>
    </div>
  )
}

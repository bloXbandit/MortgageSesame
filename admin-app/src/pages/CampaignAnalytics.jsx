/**
 * CampaignAnalytics — Resource spend, funnel, and ROI dashboard.
 *
 * Answers the core question: "Is this campaign worth running again?"
 *
 * Sections:
 *  1. Hero KPIs    — Total Spend | Pipeline Value | ROI | QR Scans | Converted
 *  2. Funnel       — Drafted → Sent → Delivered → Opened → Scanned → Called → Converted
 *  3. By Channel   — Cost / response rate per channel
 *  4. Call Outcomes — Breakdown of all call task results
 *  5. By List      — Per-prospect-list performance table
 *  6. Cost Assumptions — Editable $/piece estimates
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import {
  RefreshCw, DollarSign, TrendingUp, QrCode, CheckCircle2,
  Mail, Home, MessageSquare, Phone, ChevronDown, ChevronUp,
  AlertCircle, Settings2,
} from 'lucide-react'

// ── Palette helpers ───────────────────────────────────────────────────────────
const WARM   = '#c8860a'
const GOLD   = '#f5c87a'
const DARK   = '#e5e5e5'   // primary text on dark bg
const MUTED  = '#888'
const PAPER  = '#252525'   // card header / table row surfaces
const BORDER = '#3a3a3a'   // borders

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, highlight }) {
  return (
    <div style={{
      background: highlight ? 'rgba(245,200,122,0.1)' : '#2a2a2a',
      color: highlight ? GOLD : DARK,
      border: `1px solid ${highlight ? 'rgba(245,200,122,0.35)' : BORDER}`,
      borderRadius: 10,
      padding: '18px 20px',
      flex: 1,
      minWidth: 140,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Icon size={15} style={{ color: highlight ? GOLD : WARM }} />
        <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.07em', color: highlight ? '#aaa' : MUTED }}>
          {label}
        </span>
      </div>
      <div style={{ fontSize: '1.6rem', fontWeight: 900, lineHeight: 1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ marginTop: 4, fontSize: '0.72rem', color: highlight ? '#888' : MUTED }}>
          {sub}
        </div>
      )}
    </div>
  )
}

function FunnelBar({ label, value, max, color, pct }) {
  const width = max > 0 ? Math.max((value / max) * 100, value > 0 ? 2 : 0) : 0
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: DARK }}>{label}</span>
        <span style={{ fontSize: '0.8rem', color: MUTED }}>
          {value.toLocaleString()}
          {pct != null && (
            <span style={{ marginLeft: 6, color: WARM, fontWeight: 700 }}>{pct}%</span>
          )}
        </span>
      </div>
      <div style={{ height: 8, background: '#333', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${width}%`,
          background: color,
          borderRadius: 4,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

const CHANNEL_META = {
  email:       { label: 'Email',       icon: Mail,           color: '#1565c0' },
  direct_mail: { label: 'Direct Mail', icon: Home,           color: WARM      },
  sms:         { label: 'SMS',         icon: MessageSquare,  color: '#2e7d32' },
  call_task:   { label: 'Calls',       icon: Phone,          color: '#7b1fa2' },
}

function ChannelRow({ ch, data }) {
  const meta   = CHANNEL_META[ch] || { label: ch, icon: Mail, color: MUTED }
  const Icon   = meta.icon
  const sent   = data.sent || 0
  const opened = data.opened || 0
  const scanned = data.qr_scanned || 0
  const respRate = sent > 0 ? ((opened + scanned) / sent * 100).toFixed(1) : '—'

  return (
    <tr style={{ borderTop: `1px solid ${BORDER}` }}>
      <td style={{ padding: '10px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon size={14} style={{ color: meta.color }} />
          <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{meta.label}</span>
        </div>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem' }}>
        {data.drafted || 0}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem', fontWeight: 700 }}>
        {sent}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem' }}>
        {opened || 0}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem' }}>
        {scanned}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem', color: MUTED }}>
        {respRate !== '—' ? `${respRate}%` : '—'}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem', color: MUTED }}>
        ${data.cost_per_piece?.toFixed(3) || '0.000'}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem',
        color: data.cost_estimate > 0 ? WARM : MUTED }}>
        ${data.cost_estimate?.toFixed(2) || '0.00'}
      </td>
    </tr>
  )
}

const OUTCOME_META = {
  converted:          { label: 'Converted 🎯', color: WARM    },
  completed:          { label: 'Called ✓',     color: '#2e7d32' },
  callback_scheduled: { label: 'Callback Set', color: '#1565c0' },
  voicemail_left:     { label: 'Voicemail',    color: '#999'    },
  no_answer:          { label: 'No Answer',    color: '#999'    },
  not_interested:     { label: 'Not Interested', color: '#c62828' },
  pending:            { label: 'Pending',      color: '#aaa'    },
}

function OutcomeBar({ status, count, total }) {
  const meta  = OUTCOME_META[status] || { label: status, color: MUTED }
  const width = total > 0 ? (count / total * 100) : 0
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: '0.8rem', color: DARK, fontWeight: 500 }}>{meta.label}</span>
        <span style={{ fontSize: '0.8rem', color: MUTED }}>
          {count}
          {total > 0 && (
            <span style={{ marginLeft: 5, color: meta.color, fontWeight: 700 }}>
              ({(width).toFixed(0)}%)
            </span>
          )}
        </span>
      </div>
      <div style={{ height: 6, background: '#333', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${width}%`,
          background: meta.color,
          borderRadius: 3,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

function CostAssumptions({ assumptions, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.45)',
      zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: '#2a2a2a', borderRadius: 12, padding: 24, width: 380,
        boxShadow: '0 8px 40px rgba(0,0,0,0.18)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>Cost Assumptions</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '1.2rem', color: MUTED, lineHeight: 1 }}>×</button>
        </div>

        <p style={{ fontSize: '0.8rem', color: MUTED, margin: '0 0 16px' }}>
          These defaults come from environment variables. Set them in your{' '}
          <code style={{ background: '#1f1f1f', padding: '1px 5px', borderRadius: 3, color: '#f5c87a' }}>.env</code>{' '}
          file to match your actual provider costs.
        </p>

        {[
          { key: 'COST_PER_EMAIL',       label: 'Email (per send)',   value: assumptions.email,       ex: 'Resend / SendGrid' },
          { key: 'COST_PER_DIRECT_MAIL', label: 'Direct Mail (each)', value: assumptions.direct_mail, ex: 'Lob / PostGrid postcard' },
          { key: 'COST_PER_SMS',         label: 'SMS (per message)',   value: assumptions.sms,         ex: 'SignalWire' },
          { key: 'COMMISSION_ESTIMATE',  label: 'Avg Commission',      value: assumptions.commission,  ex: 'Per closed loan' },
        ].map(({ key, label, value, ex }) => (
          <div key={key} style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{label}</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 800, color: WARM }}>${value}</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#aaa' }}>
              <code style={{ color: '#999' }}>{key}</code> · {ex}
            </div>
          </div>
        ))}

        <div style={{ marginTop: 16, padding: '10px 12px', background: '#1f1f1f',
          borderRadius: 6, fontSize: '0.78rem', color: MUTED, borderLeft: `3px solid ${GOLD}` }}>
          Pipeline = conversions × commission estimate. ROI = pipeline ÷ spend.
        </div>
      </div>
    </div>
  )
}


// ── Main page ─────────────────────────────────────────────────────────────────

const PERIOD_OPTIONS = [
  { value: 30,  label: '30 days' },
  { value: 60,  label: '60 days' },
  { value: 90,  label: '90 days' },
  { value: 180, label: '6 months' },
  { value: 365, label: '1 year' },
]

export default function CampaignAnalytics() {
  const [data, setData]               = useState(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState('')
  const [days, setDays]               = useState(90)
  const [showAssumptions, setShowAssumptions] = useState(false)
  const [listsExpanded, setListsExpanded]     = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await api.get(`/outreach/analytics?days=${days}`)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => { load() }, [load])

  // ── Loading / error states ────────────────────────────────────────────────
  if (loading) return (
    <div style={{ padding: 32, textAlign: 'center', color: MUTED }}>
      Loading analytics…
    </div>
  )

  if (error) return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center',
        background: '#fef2f2', border: '1px solid #fecaca',
        borderRadius: 8, padding: '12px 16px', color: '#b91c1c', fontSize: '0.85rem' }}>
        <AlertCircle size={15} />
        {error}
        <button onClick={load} style={{ marginLeft: 'auto', background: 'none', border: 'none',
          cursor: 'pointer', color: '#b91c1c', fontWeight: 700 }}>Retry</button>
      </div>
    </div>
  )

  const { funnel, by_channel, call_outcomes, by_list, totals, cost_assumptions } = data

  const funnelMax    = funnel.drafted || 1
  const totalTasks   = Object.values(call_outcomes).reduce((s, v) => s + v, 0)

  // Rate helpers
  const fmt$ = (n) => n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : `$${n.toFixed(2)}`
  const fmtX = (n) => n === 0 ? '—' : `${n}×`

  return (
    <div style={{ padding: '24px 28px', maxWidth: 980, margin: '0 auto' }}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 900, color: DARK }}>
            Campaign Performance
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: MUTED }}>
            Resource spend, funnel, and ROI — last {days} days
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Period selector */}
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            style={{
              padding: '6px 12px', borderRadius: 20, fontSize: '0.78rem',
              fontWeight: 600, cursor: 'pointer', border: `1px solid ${BORDER}`,
              background: '#2a2a2a', color: '#d0d0d0',
            }}
          >
            {PERIOD_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <button
            onClick={() => setShowAssumptions(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '6px 12px', borderRadius: 20, fontSize: '0.78rem',
              fontWeight: 600, cursor: 'pointer', border: `1px solid ${BORDER}`,
              background: '#2a2a2a', color: MUTED,
            }}
          >
            <Settings2 size={13} />
            Assumptions
          </button>

          <button
            onClick={load}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '6px 12px', borderRadius: 20, fontSize: '0.78rem',
              fontWeight: 600, cursor: 'pointer', border: `1px solid ${BORDER}`,
              background: '#2a2a2a', color: MUTED,
            }}
          >
            <RefreshCw size={13} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── KPI row ──────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <KpiCard
          label="Est. Spend"
          value={fmt$(totals.spend_estimate)}
          sub={`${funnel.sent} pieces sent`}
          icon={DollarSign}
        />
        <KpiCard
          label="Pipeline Value"
          value={fmt$(totals.pipeline_estimate)}
          sub={`${funnel.converted} conversion${funnel.converted !== 1 ? 's' : ''}`}
          icon={TrendingUp}
        />
        <KpiCard
          label="ROI"
          value={fmtX(totals.roi_ratio)}
          sub={totals.roi_ratio > 0 ? 'return on spend' : 'No conversions yet'}
          icon={TrendingUp}
          highlight
        />
        <KpiCard
          label="QR Scans"
          value={funnel.qr_scanned}
          sub={`${totals.scan_rate_pct}% scan rate`}
          icon={QrCode}
        />
        <KpiCard
          label="Converted"
          value={funnel.converted}
          sub={totals.scan_to_conv_pct > 0 ? `${totals.scan_to_conv_pct}% of scans` : 'from scans → close'}
          icon={CheckCircle2}
        />
      </div>

      {/* ── Two-column layout: Funnel + Call Outcomes ────────────────────────── */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>

        {/* Funnel */}
        <div style={{
          flex: '1 1 320px', background: '#2a2a2a',
          borderRadius: 10, border: `1px solid ${BORDER}`, padding: 20,
        }}>
          <h2 style={{ margin: '0 0 16px', fontSize: '0.88rem', fontWeight: 800,
            textTransform: 'uppercase', letterSpacing: '0.07em', color: MUTED }}>
            Campaign Funnel
          </h2>

          <FunnelBar label="Drafted"    value={funnel.drafted}    max={funnelMax} color="#d0ccc4" />
          <FunnelBar
            label="Sent"
            value={funnel.sent}
            max={funnelMax}
            color="#6b9be8"
            pct={funnel.drafted > 0 ? Math.round(funnel.sent / funnel.drafted * 100) : null}
          />
          <FunnelBar
            label="Delivered"
            value={funnel.delivered}
            max={funnelMax}
            color="#5a9cc5"
            pct={funnel.sent > 0 ? Math.round(funnel.delivered / funnel.sent * 100) : null}
          />
          <FunnelBar
            label="Opened / Read"
            value={funnel.opened}
            max={funnelMax}
            color="#e8a838"
            pct={funnel.sent > 0 ? Math.round(funnel.opened / funnel.sent * 100) : null}
          />
          <FunnelBar
            label="QR Scanned"
            value={funnel.qr_scanned}
            max={funnelMax}
            color={WARM}
            pct={funnel.sent > 0 ? Math.round(funnel.qr_scanned / funnel.sent * 100) : null}
          />
          <FunnelBar
            label="Called"
            value={funnel.called}
            max={funnelMax}
            color="#7b5ea7"
            pct={funnel.qr_scanned > 0 ? Math.round(funnel.called / funnel.qr_scanned * 100) : null}
          />
          <FunnelBar
            label="Converted 🎯"
            value={funnel.converted}
            max={funnelMax}
            color="#2e7d32"
            pct={funnel.called > 0 ? Math.round(funnel.converted / funnel.called * 100) : null}
          />

          {funnel.sent === 0 && (
            <p style={{ margin: '12px 0 0', fontSize: '0.8rem', color: MUTED, textAlign: 'center' }}>
              No outreach sent in this period yet.
            </p>
          )}
        </div>

        {/* Call outcomes */}
        <div style={{
          flex: '1 1 240px', background: '#2a2a2a',
          borderRadius: 10, border: `1px solid ${BORDER}`, padding: 20,
        }}>
          <h2 style={{ margin: '0 0 4px', fontSize: '0.88rem', fontWeight: 800,
            textTransform: 'uppercase', letterSpacing: '0.07em', color: MUTED }}>
            Call Outcomes
          </h2>
          <p style={{ margin: '0 0 16px', fontSize: '0.75rem', color: '#bbb' }}>
            {totalTasks} total task{totalTasks !== 1 ? 's' : ''}
          </p>

          {Object.entries(call_outcomes).map(([status, count]) => (
            <OutcomeBar key={status} status={status} count={count} total={totalTasks} />
          ))}

          {totalTasks === 0 && (
            <p style={{ fontSize: '0.8rem', color: MUTED, textAlign: 'center', marginTop: 12 }}>
              No call tasks in this period.
            </p>
          )}

          {/* Cost-per-call note */}
          {totalTasks > 0 && totals.spend_estimate > 0 && (
            <div style={{ marginTop: 16, padding: '10px 12px',
              background: '#1f1f1f', borderRadius: 6, fontSize: '0.75rem', color: MUTED,
              borderLeft: `3px solid ${GOLD}` }}>
              <strong style={{ color: DARK }}>
                ${totals.spend_estimate > 0 && funnel.qr_scanned > 0
                  ? (totals.spend_estimate / funnel.qr_scanned).toFixed(2)
                  : '—'}
              </strong>
              {' '}per QR scan &nbsp;·&nbsp;{' '}
              <strong style={{ color: DARK }}>
                {funnel.converted > 0
                  ? `$${(totals.spend_estimate / funnel.converted).toFixed(0)}`
                  : '—'}
              </strong>
              {' '}per conversion
            </div>
          )}
        </div>
      </div>

      {/* ── By Channel table ──────────────────────────────────────────────────── */}
      <div style={{
        background: '#2a2a2a', borderRadius: 10, border: `1px solid ${BORDER}`,
        marginBottom: 20, overflow: 'hidden',
      }}>
        <div style={{ padding: '16px 20px 12px', borderBottom: `1px solid ${BORDER}` }}>
          <h2 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 800,
            textTransform: 'uppercase', letterSpacing: '0.07em', color: MUTED }}>
            By Channel
          </h2>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: PAPER }}>
                {['Channel', 'Drafted', 'Sent', 'Opened', 'QR Scanned', 'Response %', '$/Piece', 'Total Spend'].map(h => (
                  <th key={h} style={{
                    padding: '8px 12px', fontSize: '0.7rem', fontWeight: 700,
                    textTransform: 'uppercase', letterSpacing: '0.06em', color: MUTED,
                    textAlign: h === 'Channel' ? 'left' : 'right',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(by_channel).map(([ch, chData]) => (
                <ChannelRow key={ch} ch={ch} data={chData} />
              ))}
              {/* Totals row */}
              <tr style={{ borderTop: `2px solid ${BORDER}`, background: PAPER }}>
                <td style={{ padding: '10px 12px', fontWeight: 800, fontSize: '0.85rem' }}>Total</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem' }}>
                  {funnel.drafted}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem' }}>
                  {funnel.sent}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem' }}>
                  {funnel.opened}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem' }}>
                  {funnel.qr_scanned}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: '0.85rem' }}>
                  {totals.open_rate_pct > 0 ? `${totals.open_rate_pct}%` : '—'}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.85rem', color: MUTED }}>
                  —
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 900,
                  fontSize: '0.9rem', color: WARM }}>
                  ${totals.spend_estimate.toFixed(2)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── By List breakdown ─────────────────────────────────────────────────── */}
      <div style={{
        background: '#2a2a2a', borderRadius: 10, border: `1px solid ${BORDER}`,
        marginBottom: 20, overflow: 'hidden',
      }}>
        <button
          onClick={() => setListsExpanded(e => !e)}
          style={{
            width: '100%', padding: '16px 20px', background: 'none', border: 'none',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            borderBottom: listsExpanded ? `1px solid ${BORDER}` : 'none',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 800,
            textTransform: 'uppercase', letterSpacing: '0.07em', color: MUTED }}>
            By Prospect List ({by_list.length})
          </h2>
          {listsExpanded ? <ChevronUp size={15} color={MUTED} /> : <ChevronDown size={15} color={MUTED} />}
        </button>

        {listsExpanded && (
          by_list.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: MUTED, fontSize: '0.85rem' }}>
              No prospect lists with activity yet.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: PAPER }}>
                    {['List Name', 'Records', 'A-Targets', 'Drafted', 'Sent', 'Opened', 'QR Scanned', 'Est. Spend'].map(h => (
                      <th key={h} style={{
                        padding: '8px 12px', fontSize: '0.7rem', fontWeight: 700,
                        textTransform: 'uppercase', letterSpacing: '0.06em', color: MUTED,
                        textAlign: h === 'List Name' ? 'left' : 'right',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {by_list.map(row => (
                    <tr key={row.list_id} style={{ borderTop: `1px solid ${BORDER}` }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{row.list_name}</span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem' }}>
                        {(row.total_records || 0).toLocaleString()}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem' }}>
                        <span style={{ color: WARM, fontWeight: 700 }}>{row.a_targets || 0}</span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem' }}>
                        {row.drafted || 0}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem', fontWeight: 700 }}>
                        {row.sent || 0}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem' }}>
                        {row.opened || 0}
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: '0.83rem' }}>
                        <span style={{ color: row.qr_scanned > 0 ? WARM : MUTED, fontWeight: row.qr_scanned > 0 ? 700 : 400 }}>
                          {row.qr_scanned || 0}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right',
                        fontWeight: row.spend_estimate > 0 ? 700 : 400,
                        fontSize: '0.83rem', color: row.spend_estimate > 0 ? WARM : MUTED }}>
                        ${(row.spend_estimate || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {/* ── ROI callout ──────────────────────────────────────────────────────── */}
      {funnel.converted > 0 && (
        <div style={{
          background: '#1e1a12', borderRadius: 10, padding: '20px 24px', border: '1px solid rgba(245,200,122,0.2)',
          display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap',
          marginBottom: 20,
        }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: '0.75rem', color: '#888', textTransform: 'uppercase',
              letterSpacing: '0.08em', marginBottom: 4 }}>
              Bottom line
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 900, color: GOLD }}>
              ${totals.spend_estimate.toFixed(2)} spent → ${totals.pipeline_estimate.toLocaleString()} closed
            </div>
            <div style={{ marginTop: 4, fontSize: '0.8rem', color: '#888' }}>
              {totals.roi_ratio}× return. Every $1 spent made ${totals.roi_ratio}.
            </div>
          </div>
          <div style={{ fontSize: '3rem', fontWeight: 900, color: GOLD, lineHeight: 1 }}>
            {fmtX(totals.roi_ratio)}
          </div>
        </div>
      )}

      {funnel.sent > 0 && funnel.converted === 0 && (
        <div style={{
          background: '#252525', borderRadius: 10, padding: '16px 20px',
          border: `1px solid ${BORDER}`, marginBottom: 20,
          fontSize: '0.83rem', color: MUTED,
        }}>
          <strong style={{ color: DARK }}>No conversions recorded yet.</strong>
          {' '}When a call task is marked "Converted 🎯" in the Call Queue,
          the ROI calculation updates automatically.
          {funnel.qr_scanned > 0 && (
            <span style={{ color: WARM }}>
              {' '}You have {funnel.qr_scanned} QR scan{funnel.qr_scanned !== 1 ? 's' : ''} — those are warm leads.
            </span>
          )}
        </div>
      )}

      {/* Cost assumptions modal */}
      {showAssumptions && cost_assumptions && (
        <CostAssumptions
          assumptions={cost_assumptions}
          onClose={() => setShowAssumptions(false)}
        />
      )}
    </div>
  )
}

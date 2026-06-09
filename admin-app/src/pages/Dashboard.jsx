import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { api } from '../utils/api'
import {
  Users, Bell, CheckSquare, Sparkles, ArrowRight, TrendingUp,
  TrendingDown, Bot, PhoneCall, DollarSign, QrCode, Minus,
  BarChart2, Zap,
} from 'lucide-react'

const STAGE_ORDER  = ['script_only','voice_ready','video_processing','video_ready','assembled','published']
const STAGE_LABELS = { script_only:'Script', voice_ready:'Voice', video_processing:'Rendering', video_ready:'Video', assembled:'Assembled', published:'Live' }
const STAGE_COLORS = { script_only:'#555', voice_ready:'#60a5fa', video_processing:'#c8860a', video_ready:'#4ade80', assembled:'#a78bfa', published:'#4ade80' }
const PLATFORM_DOT = { tiktok:'#69C9D0', instagram_reel:'#E1306C', facebook:'#1877F2', linkedin:'#0A66C2', google_business:'#4285F4' }

function fmtRate(v) { return v != null ? `${v.toFixed(2)}%` : '—' }

export default function Dashboard() {
  const { user } = useAuth()
  const [leads, setLeads]           = useState([])
  const [approvals, setApprovals]   = useState([])
  const [rates, setRates]           = useState(null)
  const [prevRates, setPrevRates]   = useState(null)
  const [posts, setPosts]           = useState([])
  const [callQueue, setCallQueue]   = useState([])
  const [analytics, setAnalytics]   = useState(null)
  const [loading, setLoading]       = useState(true)

  useEffect(() => {
    const now = Date.now()
    Promise.allSettled([
      api.get('/leads/').then(setLeads).catch(() => {}),
      api.get('/approvals/').then(setApprovals).catch(() => {}),
      api.get('/rates/current').then(setRates).catch(() => {}),
      api.get('/rates/history?limit=2').then(h => { if (h.length > 1) setPrevRates(h[1]) }).catch(() => {}),
      api.get('/content/posts?limit=200').then(setPosts).catch(() => {}),
      api.get('/outreach/analytics?days=7').then(setAnalytics).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  // Aggregations
  const hotLeads    = leads.filter(l => l.score?.label === 'hot')
  const warmLeads   = leads.filter(l => l.score?.label === 'warm')
  const pending     = approvals.length
  const pipelineVal = (hotLeads.length * 8000) + (warmLeads.length * 2000)

  const stageCounts = STAGE_ORDER.reduce((acc, s) => {
    acc[s] = posts.filter(p => p.pipeline_stage === s).length
    return acc
  }, {})

  const readyToPublish = stageCounts.assembled + stageCounts.video_ready
  const qrScans = analytics?.totals?.scan_rate_pct != null
    ? Math.round((analytics.funnel?.scans || 0))
    : null

  const rateDelta = (field) => {
    if (!rates || !prevRates) return null
    const diff = (rates[field] || 0) - (prevRates[field] || 0)
    return diff
  }

  const conv30    = rates?.rate_conventional_30
  const delta30   = rateDelta('rate_conventional_30')

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: '0 0 3px', fontSize: '1.25rem', fontWeight: 700 }}>
            {greeting}{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''} 👋
          </h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
            Here's your pipeline at a glance.
          </p>
        </div>
        <Link to="/leads" className="btn btn-primary btn-sm">
          All Leads <ArrowRight size={12} />
        </Link>
      </div>

      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
        <KpiCard
          icon={DollarSign} color="#4ade80"
          label="Est. Pipeline"
          value={`$${(pipelineVal / 1000).toFixed(0)}K`}
          sub={`${hotLeads.length} hot · ${warmLeads.length} warm`}
        />
        <KpiCard
          icon={Bell} color="#f5c87a"
          label="Hot Leads"
          value={hotLeads.length}
          sub="need follow-up"
          to="/leads"
        />
        <KpiCard
          icon={CheckSquare} color="#60a5fa"
          label="Pending Approvals"
          value={pending}
          sub={pending === 0 ? 'queue is clear' : 'need review'}
          to="/approvals"
        />
        <KpiCard
          icon={Sparkles} color="#a78bfa"
          label="Content Ready"
          value={readyToPublish}
          sub="video + assembled"
          to="/content"
        />
        <KpiCard
          icon={TrendingUp} color={delta30 == null ? '#888' : delta30 < 0 ? '#4ade80' : delta30 > 0 ? '#f87171' : '#888'}
          label="Conv 30yr"
          value={fmtRate(conv30)}
          sub={
            delta30 == null ? 'FRED data' :
            delta30 === 0   ? 'unchanged' :
            `${delta30 > 0 ? '+' : ''}${delta30.toFixed(2)}% vs prev`
          }
          to="/rates"
        />
        <KpiCard
          icon={QrCode} color="#22d3ee"
          label="QR Scans (7d)"
          value={analytics?.funnel?.scans ?? '—'}
          sub={analytics ? `${analytics.funnel?.prospects ?? 0} prospects` : 'outreach data'}
          to="/analytics"
        />
      </div>

      {/* ── Body row ───────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px' }}>

        {/* Recent hot leads */}
        <div className="card">
          <SectionHead title="Hot & Warm Leads" link="/leads" />
          {loading ? <Skel rows={4} /> : (hotLeads.length + warmLeads.length === 0) ? (
            <Empty text="No scored leads yet." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
              {[...hotLeads, ...warmLeads].slice(0, 7).map(l => <LeadRow key={l.id} lead={l} />)}
            </div>
          )}
        </div>

        {/* Approval queue */}
        <div className="card">
          <SectionHead title="Pending Approvals" link="/approvals" />
          {loading ? <Skel rows={4} /> : approvals.length === 0 ? (
            <Empty text="Queue is clear — nice work." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
              {approvals.slice(0, 6).map(item => <ApprovalRow key={item.id} item={item} />)}
            </div>
          )}
        </div>
      </div>

      {/* ── Second body row ─────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '18px' }}>

        {/* Content pipeline */}
        <div className="card">
          <SectionHead title="Content Pipeline" link="/content" />
          {loading ? <Skel rows={3} /> : posts.length === 0 ? (
            <Empty text="No content yet. Go to Content Studio to generate your first post." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {STAGE_ORDER.map(s => stageCounts[s] > 0 && (
                  <div key={s} style={{
                    display: 'flex', alignItems: 'center', gap: '5px',
                    padding: '4px 10px', borderRadius: 20, fontSize: '0.75rem',
                    background: `${STAGE_COLORS[s]}18`, color: STAGE_COLORS[s],
                    border: `1px solid ${STAGE_COLORS[s]}30`, fontWeight: 600,
                  }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 800 }}>{stageCounts[s]}</span>
                    {STAGE_LABELS[s]}
                  </div>
                ))}
              </div>
              {/* Pending approvals by platform */}
              <PlatformBreakdown posts={posts} />
              {/* Quick stat */}
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.78rem', color: '#666' }}>
                <span>{posts.filter(p => p.approval_status === 'pending').length} pending approval</span>
                <span>{posts.filter(p => p.approval_status === 'published').length} published</span>
                <span>{stageCounts.published} live</span>
              </div>
            </div>
          )}
        </div>

        {/* Rates + Quick actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Today's rates */}
          <div className="card" style={{ flex: 1 }}>
            <SectionHead title="Today's Rates" link="/rates" />
            {!rates ? <Skel rows={3} /> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {[
                  ['Conv 30yr',  'rate_conventional_30'],
                  ['FHA 30yr',   'rate_fha_30'],
                  ['VA 30yr',    'rate_va_30'],
                  ['DSCR',       'rate_dscr'],
                ].map(([label, field]) => {
                  const val = rates[field]
                  const d   = rateDelta(field)
                  return val ? (
                    <div key={field} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.82rem' }}>
                      <span style={{ color: '#888' }}>{label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ color: '#ddd', fontWeight: 600, fontFamily: 'monospace' }}>{fmtRate(val)}</span>
                        {d != null && d !== 0 && (
                          <span style={{ fontSize: '0.7rem', color: d < 0 ? '#4ade80' : '#f87171', display: 'flex', alignItems: 'center', gap: '2px' }}>
                            {d < 0 ? <TrendingDown size={10} /> : <TrendingUp size={10} />}
                            {Math.abs(d).toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                  ) : null
                })}
                {rates.source && (
                  <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: '#444' }}>
                    Source: {rates.source} · {rates.snapshot_date}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="card">
            <SectionHead title="Quick Actions" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {[
                { to: '/content',  icon: Sparkles,  label: 'Generate Content', sub: 'AI content studio' },
                { to: '/outreach', icon: Zap,        label: 'New Outreach Run', sub: 'Direct mail / email' },
                { to: '/approvals',icon: CheckSquare,label: `Review Queue`,     sub: `${pending} item${pending !== 1 ? 's' : ''} waiting` },
                { to: '/analytics',icon: BarChart2,  label: 'View Performance', sub: 'ROI + spend' },
              ].map(({ to, icon: Icon, label, sub }) => (
                <Link key={to} to={to} style={{ textDecoration: 'none' }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '8px 10px', borderRadius: 7,
                    background: 'var(--color-carbon-mid)',
                    transition: 'background 0.15s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = '#2a2a2a'}
                    onMouseLeave={e => e.currentTarget.style.background = 'var(--color-carbon-mid)'}
                  >
                    <Icon size={15} color="var(--color-warm)" />
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: '#ddd' }}>{label}</p>
                      <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>{sub}</p>
                    </div>
                    <ArrowRight size={12} color="#444" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Platform breakdown bar ───────────────────────────────────────────────────
function PlatformBreakdown({ posts }) {
  const counts = {}
  posts.filter(p => p.approval_status !== 'published').forEach(p => {
    counts[p.platform] = (counts[p.platform] || 0) + 1
  })
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5)
  if (!sorted.length) return null
  const max = sorted[0][1]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
      {sorted.map(([platform, count]) => (
        <div key={platform} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
          <div style={{ width: '70px', color: '#666', textAlign: 'right', flexShrink: 0 }}>
            {platform.replace(/_/g, ' ')}
          </div>
          <div style={{ flex: 1, height: '6px', background: '#222', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{
              width: `${(count / max) * 100}%`, height: '100%',
              background: PLATFORM_DOT[platform] || '#f5c87a',
              borderRadius: 3,
            }} />
          </div>
          <span style={{ color: '#888', width: '16px', textAlign: 'right' }}>{count}</span>
        </div>
      ))}
    </div>
  )
}

// ── Small shared components ──────────────────────────────────────────────────
function KpiCard({ icon: Icon, label, value, sub, color, to }) {
  const content = (
    <div className="stat-card" style={{ cursor: to ? 'pointer' : 'default' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="stat-label">{label}</span>
        <Icon size={15} color={color || '#666'} />
      </div>
      <span className="stat-value">{value ?? '—'}</span>
      {sub && <span style={{ fontSize: '0.7rem', color: '#555', marginTop: '2px' }}>{sub}</span>}
    </div>
  )
  return to ? <Link to={to} style={{ textDecoration: 'none' }}>{content}</Link> : content
}

function SectionHead({ title, link }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
      <h3 style={{ margin: 0, fontSize: '0.875rem', fontWeight: 600 }}>{title}</h3>
      {link && <Link to={link} style={{ fontSize: '0.72rem', color: 'var(--color-warm)', textDecoration: 'none' }}>View all →</Link>}
    </div>
  )
}

function LeadRow({ lead }) {
  const colors = { hot: '#4ade80', warm: '#f5c87a', long_term: '#60a5fa', bad_fit: '#9ca3af', unscored: '#444' }
  const dot = colors[lead.score?.label] || '#444'
  return (
    <Link to="/leads" style={{ textDecoration: 'none' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '7px 10px', borderRadius: 6, background: 'var(--color-carbon-mid)',
        fontSize: '0.8rem',
      }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: dot, flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontWeight: 500, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {lead.name || lead.email || 'Anonymous'}
          </p>
          <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>
            {lead.loan_interest_type?.replace(/_/g,' ')} · {lead.state || '—'}
          </p>
        </div>
        <span style={{ fontSize: '0.7rem', color: dot, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', flexShrink: 0 }}>
          {lead.score?.label || 'unscored'}
        </span>
      </div>
    </Link>
  )
}

function ApprovalRow({ item }) {
  return (
    <Link to="/approvals" style={{ textDecoration: 'none' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px',
        padding: '7px 10px', borderRadius: 6, background: 'var(--color-carbon-mid)',
      }}>
        <div style={{
          width: 26, height: 26, borderRadius: 6,
          background: 'rgba(245,200,122,0.08)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <CheckSquare size={13} color="var(--color-warm)" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 500, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.title}
          </p>
          <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>{item.item_type}</p>
        </div>
        <span className="badge badge-warm" style={{ flexShrink: 0, fontSize: '0.65rem' }}>Pending</span>
      </div>
    </Link>
  )
}

function Skel({ rows = 3 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ height: '40px', background: 'var(--color-carbon-mid)', borderRadius: 6, animation: 'pulse 1.5s ease-in-out infinite' }} />
      ))}
    </div>
  )
}

function Empty({ text }) {
  return <p style={{ color: '#555', fontSize: '0.8rem', textAlign: 'center', padding: '16px 0', margin: 0 }}>{text}</p>
}

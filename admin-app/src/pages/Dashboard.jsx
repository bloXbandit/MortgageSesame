import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { api } from '../utils/api'
import { Users, Bell, CheckSquare, Sparkles, ArrowRight, TrendingUp, Bot } from 'lucide-react'

export default function Dashboard() {
  const { user } = useAuth()
  const [leads, setLeads] = useState([])
  const [approvals, setApprovals] = useState([])
  const [agentCtx, setAgentCtx] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.get('/leads/').then(setLeads).catch(() => {}),
      api.get('/approvals/').then(setApprovals).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const hotLeads = leads.filter(l => l.score?.label === 'hot')
  const warmLeads = leads.filter(l => l.score?.label === 'warm')

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>
            Good morning{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''} 👋
          </h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
            Here's what needs your attention today.
          </p>
        </div>
        <Link to="/leads" className="btn btn-primary btn-sm">
          View All Leads <ArrowRight size={12} />
        </Link>
      </div>

      {/* Stat row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
        <StatCard icon={Bell} label="New Leads" value={leads.length} delta="+3 today" up color="#f5c87a" />
        <StatCard icon={TrendingUp} label="Hot Leads" value={hotLeads.length} color="#4ade80" />
        <StatCard icon={CheckSquare} label="Pending Approvals" value={approvals.length} color="#60a5fa" />
        <StatCard icon={Users} label="Warm Pipeline" value={warmLeads.length} color="#f5c87a" />
      </div>

      {/* Two-column body */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Recent leads */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>Recent Leads</h3>
            <Link to="/leads" style={{ fontSize: '0.75rem', color: 'var(--color-warm)', textDecoration: 'none' }}>View all →</Link>
          </div>
          {loading ? <Skeleton /> : leads.length === 0 ? (
            <Empty text="No leads yet. Share your intake link to get started." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {leads.slice(0, 6).map(lead => (
                <LeadRow key={lead.id} lead={lead} />
              ))}
            </div>
          )}
        </div>

        {/* Approval queue */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>Pending Approvals</h3>
            <Link to="/approvals" style={{ fontSize: '0.75rem', color: 'var(--color-warm)', textDecoration: 'none' }}>Review all →</Link>
          </div>
          {loading ? <Skeleton /> : approvals.length === 0 ? (
            <Empty text="Queue is clear. Nice work." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {approvals.slice(0, 5).map(item => (
                <ApprovalRow key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div className="card">
        <h3 style={{ margin: '0 0 16px', fontSize: '0.9rem', fontWeight: 600 }}>Quick Actions</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          {[
            { to: '/content', icon: Sparkles, label: 'Generate Content', sub: 'TikTok, IG, LinkedIn' },
            { to: '/contacts', icon: Users, label: 'Import Contacts', sub: 'CSV upload' },
            { to: '/campaigns', icon: Bot, label: 'New Campaign', sub: 'Outreach sequence' },
            { to: '/approvals', icon: CheckSquare, label: 'Review Queue', sub: `${approvals.length} pending` },
          ].map(({ to, icon: Icon, label, sub }) => (
            <Link key={to} to={to} style={{ textDecoration: 'none' }}>
              <div className="card card-sm" style={{
                display: 'flex', flexDirection: 'column', gap: '8px',
                cursor: 'pointer', transition: 'border-color 0.13s',
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-carbon-border)'}
              >
                <Icon size={18} color="var(--color-warm)" />
                <div>
                  <p style={{ margin: '0 0 2px', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-paper)' }}>{label}</p>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: '#666' }}>{sub}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, delta, up, color }) {
  return (
    <div className="stat-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="stat-label">{label}</span>
        <Icon size={16} color={color || '#666'} />
      </div>
      <span className="stat-value">{value ?? '—'}</span>
      {delta && <span className={`stat-delta ${up ? 'up' : ''}`}>{delta}</span>}
    </div>
  )
}

function LeadRow({ lead }) {
  const scoreColors = { hot: '#4ade80', warm: '#f5c87a', long_term: '#60a5fa', bad_fit: '#9ca3af', unscored: '#666' }
  const color = scoreColors[lead.score?.label] || '#666'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '12px',
      padding: '8px 12px', borderRadius: '6px',
      background: 'var(--color-carbon-mid)', fontSize: '0.8125rem',
    }}>
      <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: color, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontWeight: 500, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {lead.name || lead.email || 'Anonymous'}
        </p>
        <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>{lead.loan_interest_type} · {lead.state || '—'}</p>
      </div>
      <span style={{ fontSize: '0.7rem', color, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {lead.score?.label || 'unscored'}
      </span>
    </div>
  )
}

function ApprovalRow({ item }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '12px',
      padding: '8px 12px', borderRadius: '6px',
      background: 'var(--color-carbon-mid)',
    }}>
      <div style={{
        width: '28px', height: '28px', borderRadius: '6px',
        background: 'rgba(245,200,122,0.1)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <CheckSquare size={14} color="var(--color-warm)" />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: '0.8rem', fontWeight: 500, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.title}
        </p>
        <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>{item.item_type}</p>
      </div>
      <span className="badge badge-warm" style={{ flexShrink: 0 }}>Pending</span>
    </div>
  )
}

function Skeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {[1, 2, 3].map(i => (
        <div key={i} style={{ height: '44px', background: 'var(--color-carbon-mid)', borderRadius: '6px', animation: 'pulse 1.5s ease-in-out infinite' }} />
      ))}
    </div>
  )
}

function Empty({ text }) {
  return <p style={{ color: '#555', fontSize: '0.8125rem', textAlign: 'center', padding: '20px 0', margin: 0 }}>{text}</p>
}

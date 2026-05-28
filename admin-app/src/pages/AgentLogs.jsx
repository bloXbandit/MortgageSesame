import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Bot, Activity, CheckCircle, XCircle, Clock } from 'lucide-react'
import toast from 'react-hot-toast'

export default function AgentLogs() {
  const [context, setContext] = useState(null)
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.get('/agent/context').then(setContext),
      api.get('/agent/pending-approvals').then(setPending),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Agent Hub</h1>
        <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
          Monitor your AI agent (Clawdbot / OpenClaw / Hermes). All actions queue here for your review.
        </p>
      </div>

      {context && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {[
            { label: 'Active Products', val: context.active_products, color: '#f5c87a' },
            { label: 'Contacts Loaded', val: context.total_contacts, color: '#60a5fa' },
            { label: 'Campaigns', val: context.total_campaigns, color: '#4ade80' },
            { label: 'Pending Approvals', val: context.pending_approvals, color: '#f87171' },
          ].map(({ label, val, color }) => (
            <div key={label} className="stat-card">
              <span className="stat-label">{label}</span>
              <span className="stat-value" style={{ color }}>{val}</span>
            </div>
          ))}
        </div>
      )}

      {/* Agent instruction block */}
      {context && (
        <div className="card" style={{ borderColor: 'rgba(245,200,122,0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <Bot size={15} color="var(--color-warm)" />
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 600 }}>Active Agent Instructions</h3>
          </div>
          <p style={{ margin: 0, color: '#aaa', fontSize: '0.8125rem', lineHeight: 1.6, fontFamily: 'monospace' }}>
            {context.agent_instructions}
          </p>
        </div>
      )}

      {/* Pending agent actions */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>Pending Agent Actions</h3>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>{pending.length} queued</span>
        </div>

        {loading ? (
          <p style={{ color: '#555', fontSize: '0.8rem' }}>Loading...</p>
        ) : pending.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px' }}>
            <CheckCircle size={24} color="#4ade80" style={{ marginBottom: '8px' }} />
            <p style={{ color: '#555', fontSize: '0.8rem', margin: 0 }}>No pending agent actions.</p>
          </div>
        ) : pending.map(item => (
          <div key={item.id} style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '10px 12px', borderRadius: '6px',
            background: 'var(--color-carbon-mid)', marginBottom: '8px',
          }}>
            <Clock size={13} color="#f5c87a" />
            <div style={{ flex: 1 }}>
              <p style={{ margin: '0 0 2px', fontSize: '0.8125rem', fontWeight: 500, color: '#ddd' }}>{item.title}</p>
              <p style={{ margin: 0, fontSize: '0.7rem', color: '#666' }}>{item.item_type} · {new Date(item.created_at).toLocaleString()}</p>
            </div>
            <span className="badge badge-warm">Pending</span>
          </div>
        ))}
      </div>

      {/* API key info */}
      <div className="card" style={{ borderStyle: 'dashed', borderColor: 'var(--color-carbon-border)' }}>
        <h3 style={{ margin: '0 0 10px', fontSize: '0.85rem', fontWeight: 600, color: '#888' }}>Connect Your Agent</h3>
        <p style={{ fontSize: '0.8rem', color: '#666', margin: '0 0 10px', lineHeight: 1.6 }}>
          Point Clawdbot, OpenClaw, or Hermes at your backend. All agent endpoints are at:
        </p>
        <code style={{ background: 'var(--color-carbon-mid)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.8rem', color: '#aaa', display: 'block' }}>
          {`{BACKEND_URL}/api/v1/agent/...`}
        </code>
        <p style={{ fontSize: '0.8rem', color: '#666', margin: '10px 0 0', lineHeight: 1.6 }}>
          Auth header: <code style={{ background: 'var(--color-carbon-mid)', padding: '1px 6px', borderRadius: '3px' }}>Authorization: Bearer {'{AGENT_API_KEY}'}</code>
          <br />Set <code style={{ background: 'var(--color-carbon-mid)', padding: '1px 6px', borderRadius: '3px' }}>AGENT_API_KEY</code> in your backend <code>.env</code> and your agent config.
        </p>
      </div>
    </div>
  )
}

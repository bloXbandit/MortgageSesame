import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { CheckCircle, XCircle, Edit3, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Approvals() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [statusFilter, setStatusFilter] = useState('pending')

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.get(`/approvals/?status=${statusFilter}`)
      setItems(data)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [statusFilter])

  const review = async (id, action) => {
    try {
      await api.post(`/approvals/${id}/review`, { action })
      toast.success(`Item ${action}d`)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (e) {
      toast.error(e.message)
    }
  }

  const pending = items.filter(i => i.status === 'pending')

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Approval Queue</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
            Review AI-generated outreach and content before anything goes out.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['pending', 'approve', 'reject', 'all'].map(s => (
            <button key={s} className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setStatusFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {statusFilter === 'pending' && pending.length > 0 && (
        <div style={{
          background: 'rgba(245,200,122,0.06)', border: '1px solid rgba(245,200,122,0.15)',
          borderRadius: '8px', padding: '12px 16px',
          display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <Clock size={14} color="var(--color-warm)" />
          <span style={{ fontSize: '0.8125rem', color: '#ccc' }}>
            <strong style={{ color: 'var(--color-warm)' }}>{pending.length} item{pending.length !== 1 ? 's' : ''}</strong> waiting for your review.
            Nothing gets sent without your approval.
          </span>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px', color: '#555' }}>Loading...</div>
      ) : items.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <CheckCircle size={32} color="#4ade80" style={{ marginBottom: '12px' }} />
          <p style={{ color: '#ccc', fontWeight: 600, margin: '0 0 4px' }}>Queue is clear</p>
          <p style={{ color: '#555', fontSize: '0.8125rem', margin: 0 }}>No pending items.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {items.map(item => (
            <ApprovalCard
              key={item.id}
              item={item}
              isExpanded={expanded === item.id}
              onToggle={() => setExpanded(expanded === item.id ? null : item.id)}
              onApprove={() => review(item.id, 'approve')}
              onReject={() => review(item.id, 'reject')}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ApprovalCard({ item, isExpanded, onToggle, onApprove, onReject }) {
  const typeColors = {
    outreach_message: 'badge-blue',
    social_post: 'badge-warm',
    campaign_step: 'badge-green',
    agent_action: 'badge-gray',
    content_item: 'badge-warm',
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header row */}
      <div
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: '14px',
          padding: '14px 18px', cursor: 'pointer',
          transition: 'background 0.12s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <span className={`badge ${typeColors[item.item_type] || 'badge-gray'}`}>{item.item_type?.replace(/_/g, ' ')}</span>
        <span style={{ flex: 1, fontSize: '0.875rem', fontWeight: 500, color: '#ddd' }}>{item.title}</span>
        <span style={{ fontSize: '0.75rem', color: '#555' }}>
          {new Date(item.created_at).toLocaleDateString()}
        </span>
        {isExpanded ? <ChevronUp size={14} color="#666" /> : <ChevronDown size={14} color="#666" />}
      </div>

      {/* Expanded preview */}
      {isExpanded && (
        <div style={{ borderTop: '1px solid var(--color-carbon-border)', padding: '16px 18px' }}>
          <div style={{
            background: 'var(--color-carbon-mid)', borderRadius: '6px',
            padding: '14px 16px', marginBottom: '16px',
            fontSize: '0.8125rem', color: '#bbb', lineHeight: 1.6,
            whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto',
          }}>
            {item.preview || 'No preview available.'}
          </div>
          {item.status === 'pending' && (
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn btn-primary" onClick={onApprove}>
                <CheckCircle size={13} /> Approve
              </button>
              <button className="btn btn-ghost" style={{ color: '#888' }}>
                <Edit3 size={13} /> Edit
              </button>
              <button className="btn btn-danger" onClick={onReject}>
                <XCircle size={13} /> Reject
              </button>
            </div>
          )}
          {item.status !== 'pending' && (
            <span className={`badge ${item.status === 'approve' ? 'badge-green' : 'badge-red'}`}>
              {item.status}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

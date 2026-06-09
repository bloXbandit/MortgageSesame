/**
 * CallQueue — Warm-lead call task queue.
 *
 * Shows all pending calls ordered by priority.
 * Priority 1 = QR scan (hottest). Priority 5 = manual queue. Priority 10 = cold.
 *
 * Each card shows:
 *   - Name, phone, property address
 *   - Trigger badge (QR Scan / Form Fill / Email Reply / High Score)
 *   - Talking points (expandable)
 *   - Quick-action buttons: Called ✓ / Voicemail / No Answer / Not Interested / Converted 🎯
 *   - Notes textarea
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import {
  Phone, PhoneOff, PhoneCall, PhoneMissed, CheckCircle2,
  ChevronDown, ChevronUp, RefreshCw, QrCode, Mail, Star,
  FileText, AlertCircle, Clock,
} from 'lucide-react'

const TRIGGER_META = {
  qr_scan:     { label: 'QR Scan',     color: '#c8860a', bg: '#fffbf2', icon: QrCode },
  form_fill:   { label: 'Form Fill',   color: '#2e7d32', bg: '#f0fdf0', icon: FileText },
  email_reply: { label: 'Email Reply', color: '#1565c0', bg: '#e8f0fe', icon: Mail },
  high_score:  { label: 'High Score',  color: '#7b1fa2', bg: '#f8e8ff', icon: Star },
  manual:      { label: 'Manual',      color: '#999',    bg: '#f5f5f5', icon: Phone },
}

const STATUS_BUTTONS = [
  { status: 'completed',          label: 'Called ✓',        icon: CheckCircle2,  color: '#2e7d32' },
  { status: 'voicemail_left',     label: 'Voicemail',       icon: PhoneOff,      color: '#1565c0' },
  { status: 'no_answer',          label: 'No Answer',       icon: PhoneMissed,   color: '#888'    },
  { status: 'not_interested',     label: 'Not Interested',  icon: PhoneCall,     color: '#c62828' },
  { status: 'converted',          label: 'Converted 🎯',    icon: CheckCircle2,  color: '#c8860a' },
  { status: 'callback_scheduled', label: 'Callback Set',    icon: Clock,         color: '#999'    },
]

function TriggerBadge({ trigger }) {
  const meta = TRIGGER_META[trigger] || TRIGGER_META.manual
  const Icon = meta.icon
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: meta.bg, color: meta.color,
      padding: '3px 8px', borderRadius: 12, fontSize: '0.72rem', fontWeight: 600,
    }}>
      <Icon size={11} />
      {meta.label}
    </span>
  )
}

function CallCard({ task, onUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const [notes, setNotes] = useState(task.notes || '')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  const handleAction = async (status) => {
    setSaving(true)
    try {
      await api.patch(`/outreach/call-tasks/${task.id}`, { status, notes: notes || undefined })
      setDone(true)
      onUpdate(task.id, status)
    } catch (e) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  const saveNotes = async () => {
    if (!notes.trim()) return
    try {
      await api.patch(`/outreach/call-tasks/${task.id}`, { notes })
    } catch (e) { /* silent */ }
  }

  if (done) return null

  const priorityColor = task.priority <= 1 ? '#c8860a' : task.priority <= 3 ? '#1565c0' : '#888'

  return (
    <div style={{
      background: '#2a2a2a', borderRadius: 8, marginBottom: 12,
      border: '1px solid #3a3a3a',
      borderLeft: `4px solid ${priorityColor}`,
      boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
    }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        {/* Priority badge */}
        <div style={{
          minWidth: 28, height: 28, borderRadius: '50%',
          background: priorityColor, color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.72rem', fontWeight: 700, flexShrink: 0,
        }}>
          P{task.priority}
        </div>

        {/* Main info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 2 }}>
            <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e5e5e5' }}>
              {task.prospect_name || 'Unknown'}
            </span>
            <TriggerBadge trigger={task.trigger} />
            {task.score && (
              <span style={{ fontSize: '0.72rem', color: '#888' }}>Score: {task.score}</span>
            )}
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 2 }}>
            {task.phone && (
              <a href={`tel:${task.phone}`} style={{
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: '0.9rem', fontWeight: 700, color: '#c8860a', textDecoration: 'none',
              }}>
                <Phone size={14} />
                {task.phone}
              </a>
            )}
            {task.property_address && (
              <span style={{ fontSize: '0.82rem', color: '#888' }}>
                📍 {task.property_address}
              </span>
            )}
          </div>

          {task.trigger_detail && (
            <p style={{ margin: '6px 0 0', fontSize: '0.78rem', color: '#888', fontStyle: 'italic' }}>
              {task.trigger_detail}
            </p>
          )}
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(e => !e)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#aaa', padding: 4 }}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Expanded: talking points + script + notes */}
      {expanded && (
        <div style={{ padding: '0 16px 14px', borderTop: '1px solid #f0ece4' }}>

          {/* Talking points */}
          {task.talking_points?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#888',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                Talking Points
              </div>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {task.talking_points.map((pt, i) => (
                  <li key={i} style={{ fontSize: '0.83rem', color: '#d0d0d0', marginBottom: 4, lineHeight: 1.5 }}>
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Call script preview */}
          {task.call_script && (
            <details style={{ marginTop: 12 }}>
              <summary style={{ fontSize: '0.78rem', color: '#888', cursor: 'pointer', fontWeight: 600 }}>
                View call script
              </summary>
              <p style={{
                marginTop: 8, fontSize: '0.82rem', color: '#d0d0d0',
                background: '#f9f7f4', padding: '10px 12px', borderRadius: 6,
                lineHeight: 1.6, fontStyle: 'italic',
              }}>
                {task.call_script}
              </p>
            </details>
          )}

          {/* Notes */}
          <div style={{ marginTop: 12 }}>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              onBlur={saveNotes}
              placeholder="Call notes…"
              rows={2}
              style={{
                width: '100%', padding: '8px 10px',
                border: '1px solid #e0d8cc', borderRadius: 6,
                fontSize: '0.83rem', fontFamily: 'inherit',
                resize: 'vertical', background: '#252525',
              }}
            />
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div style={{
        padding: '10px 14px', borderTop: '1px solid #f0ece4',
        display: 'flex', gap: 6, flexWrap: 'wrap',
      }}>
        {STATUS_BUTTONS.map(({ status, label, icon: Icon, color }) => (
          <button
            key={status}
            onClick={() => handleAction(status)}
            disabled={saving}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 10px', borderRadius: 5, fontSize: '0.78rem',
              fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer',
              background: '#f5f2ea', border: `1px solid #e0d8cc`,
              color: color, transition: 'background 0.15s',
            }}
            onMouseEnter={e => !saving && (e.currentTarget.style.background = '#efe9de')}
            onMouseLeave={e => (e.currentTarget.style.background = '#f5f2ea')}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function CallQueue() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('pending')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.get(`/outreach/call-tasks?status=${filter}&limit=100`)
      setTasks(data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { load() }, [load])

  const handleUpdate = (taskId, newStatus) => {
    setTasks(prev => prev.filter(t => t.id !== taskId))
  }

  const priorityCounts = {
    1: tasks.filter(t => t.priority === 1).length,
    other: tasks.filter(t => t.priority > 1).length,
  }

  return (
    <div style={{ padding: 24, maxWidth: 780, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#e5e5e5', margin: 0 }}>
            Call Queue
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#888' }}>
            {tasks.length} task{tasks.length !== 1 ? 's' : ''} pending
            {priorityCounts[1] > 0 && (
              <span style={{ marginLeft: 8, color: '#c8860a', fontWeight: 700 }}>
                ● {priorityCounts[1]} QR scan{priorityCounts[1] > 1 ? 's' : ''} — call first
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {['pending', 'completed', 'no_answer', 'voicemail_left'].map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              style={{
                padding: '5px 12px', borderRadius: 20, fontSize: '0.78rem',
                fontWeight: 600, cursor: 'pointer', border: '1px solid #3a3a3a',
                background: filter === s ? 'rgba(245,200,122,0.15)' : '#252525',
                color: filter === s ? '#f5c87a' : '#888',
              }}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
          <button
            onClick={load}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 12px', borderRadius: 20, fontSize: '0.78rem',
              fontWeight: 600, cursor: 'pointer', border: '1px solid #3a3a3a',
              background: '#252525', color: '#888',
            }}
          >
            <RefreshCw size={13} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center',
          background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 6, padding: '10px 14px', marginBottom: 16,
          fontSize: '0.83rem', color: '#b91c1c' }}>
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 48, color: '#aaa' }}>
          Loading call queue…
        </div>
      )}

      {/* Empty */}
      {!loading && !error && tasks.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '48px 24px',
          background: '#2a2a2a', borderRadius: 8, border: '1px solid #3a3a3a',
        }}>
          <Phone size={36} style={{ color: '#ddd', marginBottom: 12 }} />
          <p style={{ color: '#999', fontSize: '0.9rem', margin: 0 }}>
            {filter === 'pending' ? 'No pending calls. Send some mailers and watch this fill up.' : `No ${filter.replace('_', ' ')} tasks.`}
          </p>
        </div>
      )}

      {/* Task cards — QR scans first */}
      {!loading && tasks
        .sort((a, b) => a.priority - b.priority || new Date(b.created_at) - new Date(a.created_at))
        .map(task => (
          <CallCard key={task.id} task={task} onUpdate={handleUpdate} />
        ))
      }
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Bell, BellOff, Plus, Trash2, TrendingDown, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'

const RATE_FIELD_LABELS = {
  rate_conventional_30: 'Conv 30yr',
  rate_conventional_15: 'Conv 15yr',
  rate_fha_30:          'FHA 30yr',
  rate_va_30:           'VA 30yr',
  rate_usda_30:         'USDA 30yr',
  rate_dscr:            'DSCR Investor',
  rate_heloc_prime_plus:'HELOC',
  rate_jumbo_30:        'Jumbo 30yr',
}

function AlertsSection() {
  const [alerts, setAlerts]   = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]       = useState({
    name: '', rate_field: 'rate_conventional_30', threshold: '', direction: 'below', action: 'log', message: '',
  })

  const load = () => api.get('/rates/alerts').then(setAlerts).catch(() => {})
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!form.name || !form.threshold) { toast.error('Name and threshold are required'); return }
    try {
      await api.post('/rates/alerts', { ...form, threshold: parseFloat(form.threshold) })
      toast.success('Alert created')
      setShowForm(false)
      setForm({ name: '', rate_field: 'rate_conventional_30', threshold: '', direction: 'below', action: 'log', message: '' })
      load()
    } catch (e) { toast.error(e.message) }
  }

  const toggle = async (alert) => {
    try {
      await api.patch(`/rates/alerts/${alert.id}`, { is_active: !alert.is_active })
      load()
    } catch (e) { toast.error(e.message) }
  }

  const remove = async (alertId) => {
    if (!confirm('Delete this alert?')) return
    try { await api.delete(`/rates/alerts/${alertId}`); load() }
    catch (e) { toast.error(e.message) }
  }

  return (
    <div style={{ marginTop: 28 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-paper)' }}>Rate Alerts</h2>
          <p style={{ margin: '3px 0 0', fontSize: '0.8rem', color: '#666' }}>
            Auto-fires when a rate crosses your threshold. Actions: log event or queue outreach task.
          </p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm(s => !s)}>
          <Plus size={12} /> New Alert
        </button>
      </div>

      {showForm && (
        <div className="card fade-in" style={{ marginBottom: 14, padding: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
            <div>
              <label style={labelSty}>Alert Name</label>
              <input className="input" placeholder="Refi trigger — Conv 30yr drops" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label style={labelSty}>Rate Field</label>
              <select className="select" value={form.rate_field} onChange={e => setForm(f => ({ ...f, rate_field: e.target.value }))}>
                {Object.entries(RATE_FIELD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label style={labelSty}>Threshold (%)</label>
              <input className="input" type="number" step="0.01" placeholder="6.50" value={form.threshold}
                onChange={e => setForm(f => ({ ...f, threshold: e.target.value }))} />
            </div>
            <div>
              <label style={labelSty}>Direction</label>
              <select className="select" value={form.direction} onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}>
                <option value="below">Drops below</option>
                <option value="above">Rises above</option>
              </select>
            </div>
            <div>
              <label style={labelSty}>Action</label>
              <select className="select" value={form.action} onChange={e => setForm(f => ({ ...f, action: e.target.value }))}>
                <option value="log">Log event only</option>
                <option value="queue_outreach">Log + Queue outreach task</option>
              </select>
            </div>
            <div>
              <label style={labelSty}>Note (optional)</label>
              <input className="input" placeholder="Message for the outreach task" value={form.message}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary btn-sm" onClick={create}>Create Alert</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {alerts.length === 0 ? (
        <div style={{ padding: '20px', textAlign: 'center', color: '#555', fontSize: '0.8rem', background: '#1a1a1a', borderRadius: 8 }}>
          No alerts yet. Create one to get notified when rates cross a threshold.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {alerts.map(a => (
            <div key={a.id} className="card card-sm" style={{ opacity: a.is_active ? 1 : 0.5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ flexShrink: 0 }}>
                  {a.direction === 'below' ? <TrendingDown size={14} color="#4ade80" /> : <TrendingUp size={14} color="#f87171" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontWeight: 600, fontSize: '0.83rem', color: '#ddd' }}>{a.name}</p>
                  <p style={{ margin: 0, fontSize: '0.72rem', color: '#666' }}>
                    {RATE_FIELD_LABELS[a.rate_field]} {a.direction} {a.threshold}%
                    {' · '}{a.action === 'queue_outreach' ? '📋 queue outreach' : '🪵 log only'}
                    {a.last_triggered_at && ` · Last fired ${new Date(a.last_triggered_at).toLocaleDateString()} @ ${a.last_triggered_rate?.toFixed(2)}%`}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={() => toggle(a)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: a.is_active ? '#4ade80' : '#555', padding: '3px' }}
                    title={a.is_active ? 'Disable' : 'Enable'}
                  >
                    {a.is_active ? <Bell size={14} /> : <BellOff size={14} />}
                  </button>
                  <button
                    onClick={() => remove(a.id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', padding: '3px' }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const labelSty = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '4px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }

export default function Rates() {
  const [current, setCurrent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [msg, setMsg] = useState(null)
  const [form, setForm] = useState({
    rate_conventional_30: '',
    rate_conventional_15: '',
    rate_fha_30: '',
    rate_va_30: '',
    rate_usda_30: '',
    rate_dscr: '',
    rate_heloc_prime_plus: '',
    rate_jumbo_30: '',
    notes: '',
  })

  const FIELDS = [
    { key: 'rate_conventional_30', label: 'Conventional 30yr' },
    { key: 'rate_conventional_15', label: 'Conventional 15yr' },
    { key: 'rate_fha_30',          label: 'FHA 30yr' },
    { key: 'rate_va_30',           label: 'VA 30yr' },
    { key: 'rate_usda_30',         label: 'USDA 30yr' },
    { key: 'rate_dscr',            label: 'DSCR Investor' },
    { key: 'rate_heloc_prime_plus',label: 'HELOC' },
    { key: 'rate_jumbo_30',        label: 'Jumbo 30yr' },
  ]

  const load = async () => {
    try {
      const data = await api.get('/rates/current')
      setCurrent(data)
      const populated = {}
      FIELDS.forEach(f => { populated[f.key] = data[f.key]?.toString() || '' })
      populated.notes = data.notes || ''
      setForm(populated)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const body = { notes: form.notes || null }
      FIELDS.forEach(f => {
        const v = parseFloat(form[f.key])
        if (!isNaN(v)) body[f.key] = v
      })
      await api.post('/rates/admin/update', body)
      setMsg({ type: 'success', text: 'Rates saved for today ✓' })
      load()
    } catch {
      setMsg({ type: 'error', text: 'Save failed — check connection.' })
    }
    setSaving(false)
  }

  const handleFredSync = async () => {
    setSyncing(true)
    setMsg(null)
    try {
      const data = await api.post('/rates/admin/sync-fred', {})
      if (data.success) {
        const dates = (data.saved || []).map(s => s.date).join(', ')
        const resetNote = data.reset ? ' Manual overrides cleared — all rates now from FRED.' : ''
        setMsg({ type: 'success', text: `FRED data synced ✓  (${dates || 'rates updated'}).${resetNote}` })
        load()
      } else if (data.needs_key) {
        setMsg({
          type: 'error',
          text: '⚠ FRED_API_KEY not set in your .env — get a free key at fred.stlouisfed.org/docs/api/api_key.html then restart the backend.',
        })
      } else {
        setMsg({ type: 'error', text: data.message || 'FRED sync failed.' })
      }
    } catch (e) {
      setMsg({ type: 'error', text: `FRED sync failed: ${e.message}` })
    } finally {
      setSyncing(false)
    }
  }

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div style={{ maxWidth: 700 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, color: 'var(--color-paper)', fontSize: '1.4rem', fontWeight: 800 }}>Rate Snapshot</h1>
        <p style={{ margin: '4px 0 0', color: '#666', fontSize: '0.875rem' }}>
          Set today's example rates shown on the public site. Leave blank to inherit yesterday's value.
          {current?.source && <span style={{ marginLeft: 8, color: '#555' }}>Current source: <strong style={{ color: '#888' }}>{current.source}</strong> · {current.snapshot_date}</span>}
        </p>
      </div>

      {msg && (
        <div style={{
          marginBottom: 16, padding: '10px 14px', borderRadius: 7,
          background: msg.type === 'success' ? '#14532d22' : msg.type === 'error' ? '#7f1d1d22' : '#1e3a5f22',
          color: msg.type === 'success' ? '#4ade80' : msg.type === 'error' ? '#f87171' : '#93c5fd',
          fontSize: '0.875rem',
        }}>
          {msg.text}
        </div>
      )}

      {loading ? (
        <div style={{ color: '#555' }}>Loading…</div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            {FIELDS.map(f => (
              <div key={f.key}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#888', fontWeight: 500, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {f.label}
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="20"
                    value={form[f.key]}
                    onChange={e => set(f.key, e.target.value)}
                    placeholder="e.g. 7.00"
                    style={{
                      width: '100%', padding: '9px 30px 9px 12px',
                      background: '#2a2a2a', border: '1px solid #3a3a3a',
                      borderRadius: 6, color: '#fff', fontSize: '0.9rem',
                      outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                  <span style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#555', fontSize: '0.875rem' }}>%</span>
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#888', fontWeight: 500, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Notes (optional, shown to self only)
            </label>
            <input
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              placeholder="e.g. Rates ticked up 10bps today after CPI"
              style={{
                width: '100%', padding: '9px 12px',
                background: '#2a2a2a', border: '1px solid #3a3a3a',
                borderRadius: 6, color: '#fff', fontSize: '0.875rem',
                outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: '10px 22px', background: saving ? '#444' : '#f5c87a',
                color: '#1f1f1f', border: 'none', borderRadius: 6,
                fontWeight: 700, fontSize: '0.9rem', cursor: saving ? 'not-allowed' : 'pointer',
              }}
            >
              {saving ? 'Saving…' : 'Save Today\'s Rates'}
            </button>
            <button
              onClick={handleFredSync}
              disabled={syncing}
              style={{
                padding: '10px 18px', background: 'transparent',
                color: '#888', border: '1px solid #444', borderRadius: 6,
                fontWeight: 500, fontSize: '0.875rem', cursor: syncing ? 'not-allowed' : 'pointer',
              }}
            >
              {syncing ? 'Pulling…' : '↻ Pull FRED Data'}
            </button>
          </div>

          <div style={{ marginTop: 10, fontSize: '0.73rem', color: '#555', lineHeight: 1.8 }}>
            <strong style={{ color: '#888' }}>Manual rates</strong> — fill in any fields and save. Only the fields you enter are overridden; the rest keep pulling from the last FRED sync.<br/>
            <strong style={{ color: '#888' }}>Pull FRED Data</strong> — <em>full reset</em>: clears today's manual entries and reloads all rates from Freddie Mac PMMS (published Thursdays). After syncing, any manual edits you make on top will blend with the FRED base. Click Pull again to reset.<br/>
            <span style={{ color: current?.source === 'manual' ? '#f5c87a' : current?.source === 'fred' ? '#4ade80' : '#888' }}>
              Current source: <strong>{current?.source || '—'}</strong>
            </span>
            {'  ·  '}
            <span>
              FRED key: {' '}
              <a href="https://fred.stlouisfed.org/docs/api/api_key.html" target="_blank" rel="noopener noreferrer"
                style={{ color: '#60a5fa', textDecoration: 'none' }}>
                get free key → add <code style={{ background: '#1a1a1a', padding: '1px 5px', borderRadius: 3, fontSize: '0.7rem' }}>FRED_API_KEY=...</code> to .env, restart backend
              </a>
            </span>
          </div>
        </>
      )}

      <AlertsSection />
    </div>
  )
}

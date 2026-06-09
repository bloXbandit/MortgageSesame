/**
 * Outreach — Campaign engine command center.
 *
 * Three tabs:
 *   1. Prospect Lists  — create, import CSV, score, view grade distribution
 *   2. Generate        — drill into a list, view prospects, generate batch
 *   3. Review & Send   — outreach items filtered by status, approve/reject/send, HTML preview
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../utils/api'
import {
  Plus, Upload, Target, Zap, Send, Eye, CheckCircle, XCircle,
  ChevronDown, ChevronUp, RefreshCw, AlertCircle, Users,
  BarChart2, Mail, MessageSquare, FileText, Phone, Trash2,
} from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────────

const GRADE_COLORS = {
  A_TARGET: { bg: '#f0fdf0', color: '#166534', label: 'A — Target' },
  B_TARGET: { bg: '#eff6ff', color: '#1d4ed8', label: 'B — Target' },
  NURTURE:  { bg: '#fffbeb', color: '#92400e', label: 'Nurture' },
  SKIP:     { bg: '#f9fafb', color: '#9ca3af', label: 'Skip' },
  BLOCKED:  { bg: '#fef2f2', color: '#b91c1c', label: 'Blocked' },
}

const CHANNEL_META = {
  email:       { label: 'Email',       icon: Mail },
  direct_mail: { label: 'Direct Mail', icon: FileText },
  sms:         { label: 'SMS',         icon: MessageSquare },
  call_task:   { label: 'Call Script', icon: Phone },
}

const CAMPAIGN_TYPES = [
  { value: 'refi_rate_reduction',    label: 'Refi Rate Reduction' },
  { value: 'cash_out_equity',        label: 'Cash-Out / HELOC' },
  { value: 'fha_streamline_watch',   label: 'FHA Streamline' },
  { value: 'past_client_equity_review', label: 'Past Client Equity Review' },
  { value: 'investor_refi',          label: 'Investor / DSCR Refi' },
  { value: 'realtor_partnership',    label: 'Realtor Partnership' },
  { value: 'listing_agent_outreach', label: 'Listing Agent Outreach' },
  { value: 'dpa_education',          label: 'DPA Education' },
]

function GradePill({ grade }) {
  const meta = GRADE_COLORS[grade] || GRADE_COLORS.SKIP
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
      fontSize: '0.72rem', fontWeight: 700,
      background: meta.bg, color: meta.color,
    }}>
      {meta.label}
    </span>
  )
}

function StatusPill({ status }) {
  const colorMap = {
    draft: '#888', approved: '#2e7d32', sent: '#1565c0',
    delivered: '#1565c0', opened: '#7b1fa2', clicked: '#c8860a',
    qr_scanned: '#c8860a', failed: '#b91c1c', rejected: '#b91c1c',
    pending_approval: '#92400e', converted: '#c8860a',
  }
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
      fontSize: '0.72rem', fontWeight: 600,
      background: '#f5f2ea', color: colorMap[status] || '#888',
    }}>
      {status?.replace(/_/g, ' ')}
    </span>
  )
}

// ── Tab: Prospect Lists ───────────────────────────────────────────────────────

function ProspectListsTab({ onDrillIn }) {
  const [lists, setLists] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', prospect_type: 'homeowner', state: 'MD' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/outreach/prospect-lists')
      setLists(data || [])
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const createList = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await api.post('/outreach/prospect-lists', form)
      setShowCreate(false)
      setForm({ name: '', description: '', prospect_type: 'homeowner', state: 'MD' })
      load()
    } catch (e) { alert(e.message) }
    finally { setSaving(false) }
  }

  const deleteList = async (id, name) => {
    if (!confirm(`Delete "${name}" and all its prospects?`)) return
    try {
      await api.delete(`/outreach/prospect-lists/${id}`)
      setLists(l => l.filter(x => x.id !== id))
    } catch (e) { alert(e.message) }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <p style={{ margin: 0, fontSize: '0.85rem', color: '#888' }}>
          {lists.length} list{lists.length !== 1 ? 's' : ''} — click any list to import, score, and generate
        </p>
        <button
          onClick={() => setShowCreate(s => !s)}
          style={{ display: 'flex', alignItems: 'center', gap: 6,
            padding: '7px 14px', borderRadius: 6, border: 'none',
            background: '#1f1f1f', color: '#f5c87a', fontSize: '0.83rem',
            fontWeight: 700, cursor: 'pointer' }}
        >
          <Plus size={14} /> New List
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div style={{ background: '#252525', border: '1px solid #f5c87a', borderRadius: 8,
          padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="List name *" style={inputStyle} />
            <select value={form.prospect_type} onChange={e => setForm(f => ({ ...f, prospect_type: e.target.value }))}
              style={inputStyle}>
              <option value="homeowner">Homeowner</option>
              <option value="investor">Investor</option>
              <option value="realtor">Realtor</option>
              <option value="past_client">Past Client</option>
            </select>
            <input value={form.state} onChange={e => setForm(f => ({ ...f, state: e.target.value }))}
              placeholder="State (MD, DC…)" style={inputStyle} />
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Description (optional)" style={inputStyle} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={createList} disabled={saving || !form.name.trim()}
              style={{ padding: '7px 16px', borderRadius: 6, border: 'none',
                background: '#1f1f1f', color: '#f5c87a', fontWeight: 700, cursor: 'pointer' }}>
              {saving ? 'Creating…' : 'Create List'}
            </button>
            <button onClick={() => setShowCreate(false)}
              style={{ padding: '7px 14px', borderRadius: 6, border: '1px solid #e0d8cc',
                background: '#2a2a2a', cursor: 'pointer', fontSize: '0.83rem' }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <ErrorBanner msg={error} />}
      {loading ? <Loading /> : (
        <div>
          {lists.length === 0 ? (
            <Empty icon={Users} text="No prospect lists yet. Create one and upload a CSV." />
          ) : lists.map(pl => (
            <div key={pl.id} onClick={() => onDrillIn(pl)}
              style={{ background: '#2a2a2a', borderRadius: 8, border: '1px solid #3a3a3a',
                padding: '14px 16px', marginBottom: 10, cursor: 'pointer',
                transition: 'box-shadow 0.15s' }}
              onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
              onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e5e5e5', marginBottom: 2 }}>
                    {pl.name}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#888' }}>
                    {pl.prospect_type} · {pl.state || 'all states'}
                    {pl.description && ` · ${pl.description}`}
                  </div>
                </div>
                <button onClick={e => { e.stopPropagation(); deleteList(pl.id, pl.name) }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ccc',
                    padding: 4, borderRadius: 4 }}
                  title="Delete list">
                  <Trash2 size={14} />
                </button>
              </div>

              <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
                <Stat label="Total" value={pl.total_records || 0} />
                <Stat label="Scored" value={pl.scored_count || 0} />
                <Stat label="A Targets" value={pl.a_target_count || 0} color="#2e7d32" />
                <Stat label="B Targets" value={pl.b_target_count || 0} color="#1d4ed8" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tab: List Drill-In (import + score + generate) ────────────────────────────

function ListDetailTab({ list, onBack }) {
  const [prospects, setProspects] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scoring, setScoring] = useState(false)
  const [scoreResult, setScoreResult] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult] = useState(null)
  const [uploadJob, setUploadJob] = useState(null)
  const [jobPoll, setJobPoll] = useState(null)
  const fileRef = useRef()

  const [genOpts, setGenOpts] = useState({
    campaign_type: 'refi_rate_reduction',
    channel: 'email',
    step: 1,
    grades: ['A_TARGET', 'B_TARGET'],
    max_items: 200,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [pts, sum] = await Promise.all([
        api.get(`/outreach/prospect-lists/${list.id}/prospects?limit=100`),
        api.get(`/outreach/prospect-lists/${list.id}/score-summary`),
      ])
      setProspects(pts || [])
      setSummary(sum)
    } catch (e) { /* ignore */ }
    finally { setLoading(false) }
  }, [list.id])

  useEffect(() => { load() }, [load])

  // Poll import job
  useEffect(() => {
    if (!uploadJob || uploadJob.status === 'complete' || uploadJob.status === 'failed') return
    const t = setTimeout(async () => {
      try {
        const job = await api.get(`/outreach/jobs/${uploadJob.job_id}`)
        setUploadJob(job)
        if (job.status === 'complete') load()
      } catch (e) { /* ignore */ }
    }, 1500)
    return () => clearTimeout(t)
  }, [uploadJob, load])

  const uploadCsv = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try {
      const job = await api.upload(`/outreach/prospect-lists/${list.id}/upload-csv`, fd)
      setUploadJob(job)
    } catch (err) { alert(err.message) }
    e.target.value = ''
  }

  const runScore = async () => {
    setScoring(true)
    setScoreResult(null)
    try {
      const res = await api.post(`/outreach/prospect-lists/${list.id}/score`)
      setScoreResult(res)
      load()
    } catch (e) { alert(e.message) }
    finally { setScoring(false) }
  }

  const runGenerate = async () => {
    setGenerating(true)
    setGenResult(null)
    try {
      const res = await api.post(`/outreach/prospect-lists/${list.id}/generate-batch`, genOpts)
      setGenResult(res)
    } catch (e) { alert(e.message) }
    finally { setGenerating(false) }
  }

  const gradeKeys = summary ? Object.entries(summary.grade_distribution || {}).filter(([, v]) => v > 0) : []

  return (
    <div>
      <button onClick={onBack}
        style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer',
          fontSize: '0.82rem', marginBottom: 12, padding: 0 }}>
        ← All Lists
      </button>

      <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#e5e5e5', margin: '0 0 4px' }}>
        {list.name}
      </h2>
      <p style={{ fontSize: '0.8rem', color: '#888', margin: '0 0 16px' }}>
        {list.total_records || 0} records · {list.prospect_type} · {list.state || 'all states'}
      </p>

      {/* Step bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {/* Step 1: Import */}
        <div style={stepCard}>
          <div style={stepNum}>1</div>
          <div>
            <div style={stepTitle}>Import CSV</div>
            <button onClick={() => fileRef.current?.click()}
              style={actionBtn}>
              <Upload size={13} /> Upload CSV
            </button>
            <input ref={fileRef} type="file" accept=".csv" onChange={uploadCsv} style={{ display: 'none' }} />
            {uploadJob && (
              <div style={{ marginTop: 6, fontSize: '0.75rem', color: uploadJob.status === 'complete' ? '#2e7d32' : '#888' }}>
                {uploadJob.status === 'complete'
                  ? `✓ ${uploadJob.imported} imported`
                  : `Processing… ${uploadJob.progress || 0}/${uploadJob.total || '?'}`}
                {uploadJob.errors?.length > 0 && ` · ${uploadJob.errors.length} errors`}
              </div>
            )}
          </div>
        </div>

        {/* Step 2: Score */}
        <div style={stepCard}>
          <div style={stepNum}>2</div>
          <div>
            <div style={stepTitle}>Score Prospects</div>
            <button onClick={runScore} disabled={scoring} style={actionBtn}>
              <Target size={13} /> {scoring ? 'Scoring…' : 'Run Score'}
            </button>
            {scoreResult && (
              <div style={{ marginTop: 6, fontSize: '0.75rem', color: '#2e7d32' }}>
                ✓ {scoreResult.a_target} A · {scoreResult.b_target} B · {scoreResult.nurture} Nurture
              </div>
            )}
            {summary && gradeKeys.length > 0 && !scoreResult && (
              <div style={{ marginTop: 6, fontSize: '0.75rem', color: '#888' }}>
                {gradeKeys.map(([g, v]) => `${g.replace('_TARGET', '')}: ${v}`).join(' · ')}
              </div>
            )}
          </div>
        </div>

        {/* Step 3: Generate */}
        <div style={{ ...stepCard, flexDirection: 'column', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <div style={stepNum}>3</div>
            <div style={stepTitle}>Generate Outreach</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, width: '100%' }}>
            <select value={genOpts.campaign_type}
              onChange={e => setGenOpts(o => ({ ...o, campaign_type: e.target.value }))}
              style={selectStyle}>
              {CAMPAIGN_TYPES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <select value={genOpts.channel}
              onChange={e => setGenOpts(o => ({ ...o, channel: e.target.value }))}
              style={selectStyle}>
              {Object.entries(CHANNEL_META).map(([v, m]) => (
                <option key={v} value={v}>{m.label}</option>
              ))}
            </select>
            <select value={genOpts.step}
              onChange={e => setGenOpts(o => ({ ...o, step: Number(e.target.value) }))}
              style={selectStyle}>
              {[1, 2, 3].map(s => <option key={s} value={s}>Step {s}</option>)}
            </select>
            <input type="number" value={genOpts.max_items}
              onChange={e => setGenOpts(o => ({ ...o, max_items: Number(e.target.value) }))}
              placeholder="Max items" style={selectStyle} min={1} max={1000} />
          </div>
          <button onClick={runGenerate} disabled={generating}
            style={{ ...actionBtn, marginTop: 8, background: '#c8860a', color: '#fff' }}>
            <Zap size={13} /> {generating ? 'Generating…' : `Generate A+B Batch`}
          </button>
          {genResult && (
            <div style={{ marginTop: 6, fontSize: '0.75rem', color: '#2e7d32' }}>
              ✓ {genResult.generated} items generated — view in Review tab
              {genResult.errors?.length > 0 && ` · ${genResult.errors.length} errors`}
            </div>
          )}
        </div>
      </div>

      {/* Prospect preview table */}
      {loading ? <Loading /> : (
        <div>
          <div style={{ fontSize: '0.78rem', color: '#888', marginBottom: 8 }}>
            Showing first {prospects.length} prospects
          </div>
          <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid #3a3a3a' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ background: '#f9f7f4' }}>
                  {['Name', 'Email', 'Property', 'Rate', 'Equity', 'Loan Type', 'Grade', 'Channel'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left',
                      fontSize: '0.72rem', fontWeight: 700, color: '#888',
                      textTransform: 'uppercase', letterSpacing: '0.05em',
                      borderBottom: '1px solid #333' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {prospects.map((p, i) => (
                  <tr key={p.id} style={{ background: i % 2 === 0 ? '#fff' : '#fafaf8' }}>
                    <td style={td}>{p.full_name || '—'}</td>
                    <td style={td}><span style={{ color: '#888' }}>{p.email || '—'}</span></td>
                    <td style={td}>{p.property_address?.split(',')[0] || '—'}</td>
                    <td style={td}>{p.current_rate_estimate ? `${p.current_rate_estimate}%` : '—'}</td>
                    <td style={td}>{p.estimated_equity_pct ? `${p.estimated_equity_pct}%` : '—'}</td>
                    <td style={td}>{p.loan_type || '—'}</td>
                    <td style={td}>{p.grade ? <GradePill grade={p.grade} /> : <span style={{ color: '#ccc' }}>—</span>}</td>
                    <td style={td}><span style={{ color: '#888' }}>{p.recommended_channel || '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: Review & Send ────────────────────────────────────────────────────────

function ReviewTab() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('draft')
  const [channelFilter, setChannelFilter] = useState('')
  const [preview, setPreview] = useState(null)
  const [actionLoading, setActionLoading] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (statusFilter) params.set('status', statusFilter)
      if (channelFilter) params.set('channel', channelFilter)
      const data = await api.get(`/outreach/items?${params}`)
      setItems(data || [])
    } catch (e) { /* ignore */ }
    finally { setLoading(false) }
  }, [statusFilter, channelFilter])

  useEffect(() => { load() }, [load])

  const doAction = async (id, action) => {
    setActionLoading(l => ({ ...l, [id]: action }))
    try {
      if (action === 'approve') await api.post(`/outreach/items/${id}/approve`)
      else if (action === 'reject') await api.post(`/outreach/items/${id}/reject`, 'Rejected in review')
      else if (action === 'send') await api.post(`/outreach/items/${id}/send`)
      load()
    } catch (e) { alert(e.message) }
    finally { setActionLoading(l => ({ ...l, [id]: null })) }
  }

  const channelIcon = (ch) => {
    const meta = CHANNEL_META[ch]
    if (!meta) return null
    const Icon = meta.icon
    return <Icon size={13} style={{ color: '#888' }} />
  }

  return (
    <div>
      {/* Filters */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {['draft', 'approved', 'sent', 'delivered', 'opened', 'qr_scanned', 'failed'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            style={{ padding: '4px 10px', borderRadius: 14, fontSize: '0.75rem',
              fontWeight: 600, cursor: 'pointer', border: '1px solid #e0d8cc',
              background: statusFilter === s ? '#1f1f1f' : '#fff',
              color: statusFilter === s ? '#f5c87a' : '#666' }}>
            {s.replace(/_/g, ' ')}
          </button>
        ))}
        <select value={channelFilter} onChange={e => setChannelFilter(e.target.value)}
          style={{ ...selectStyle, marginLeft: 'auto' }}>
          <option value="">All channels</option>
          {Object.entries(CHANNEL_META).map(([v, m]) => (
            <option key={v} value={v}>{m.label}</option>
          ))}
        </select>
        <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 4,
          padding: '4px 10px', borderRadius: 14, fontSize: '0.75rem', cursor: 'pointer',
          border: '1px solid #e0d8cc', background: '#2a2a2a', color: '#888' }}>
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {loading ? <Loading /> : items.length === 0 ? (
        <Empty icon={Mail} text={`No ${statusFilter} items. Generate a batch from a prospect list.`} />
      ) : (
        <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid #3a3a3a' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ background: '#f9f7f4' }}>
                {['Ch', 'Template', 'Subject / Preview', 'Status', 'Actions'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left',
                    fontSize: '0.72rem', fontWeight: 700, color: '#888',
                    textTransform: 'uppercase', letterSpacing: '0.05em',
                    borderBottom: '1px solid #333' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={item.id} style={{ background: i % 2 === 0 ? '#fff' : '#fafaf8' }}>
                  <td style={{ ...td, width: 32 }}>{channelIcon(item.channel)}</td>
                  <td style={td}>
                    <span style={{ fontSize: '0.75rem', color: '#888' }}>{item.template_name || item.template_key || '—'}</span>
                  </td>
                  <td style={{ ...td, maxWidth: 260 }}>
                    <div style={{ fontWeight: 600, color: '#e5e5e5', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.subject || item.template_key || '—'}
                    </div>
                    {item.qr_code && (
                      <span style={{ fontSize: '0.72rem', color: '#c8860a' }}>QR: {item.qr_code}</span>
                    )}
                  </td>
                  <td style={td}><StatusPill status={item.status} /></td>
                  <td style={{ ...td, whiteSpace: 'nowrap' }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <ActionBtn icon={Eye} label="View" color="#888"
                        onClick={() => setPreview(item)} />
                      {item.status === 'draft' && (
                        <ActionBtn icon={CheckCircle} label="Approve" color="#2e7d32"
                          loading={actionLoading[item.id] === 'approve'}
                          onClick={() => doAction(item.id, 'approve')} />
                      )}
                      {item.status === 'draft' && (
                        <ActionBtn icon={XCircle} label="Reject" color="#b91c1c"
                          loading={actionLoading[item.id] === 'reject'}
                          onClick={() => doAction(item.id, 'reject')} />
                      )}
                      {(item.status === 'approved' || item.status === 'draft') && (
                        <ActionBtn icon={Send} label="Send" color="#c8860a"
                          loading={actionLoading[item.id] === 'send'}
                          onClick={() => doAction(item.id, 'send')} />
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview modal */}
      {preview && (
        <PreviewModal item={preview} onClose={() => setPreview(null)} />
      )}
    </div>
  )
}

// ── Preview modal ─────────────────────────────────────────────────────────────

function PreviewModal({ item, onClose }) {
  const hasHtml = item.body_html || item.call_script
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ background: '#2a2a2a', borderRadius: 10, width: '100%', maxWidth: 800,
        maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
        {/* Modal header */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #333',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#e5e5e5' }}>
              {item.subject || item.template_name || item.template_key}
            </span>
            <StatusPill status={item.status} />
          </div>
          <button onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
              fontSize: '1.2rem', color: '#888', lineHeight: 1 }}>✕</button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {item.body_html && (
            <iframe
              srcDoc={item.body_html}
              style={{ width: '100%', height: 480, border: '1px solid #3a3a3a', borderRadius: 6 }}
              title="Email / Mail Preview"
            />
          )}
          {item.body_text && !item.body_html && (
            <pre style={{ fontFamily: 'inherit', fontSize: '0.83rem', color: '#d0d0d0',
              lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f9f7f4',
              padding: 16, borderRadius: 6 }}>
              {item.body_text}
            </pre>
          )}
          {item.call_script && (
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.78rem', color: '#888',
                textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                Call Script
              </div>
              <pre style={{ fontFamily: 'inherit', fontSize: '0.83rem', color: '#d0d0d0',
                lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f9f7f4',
                padding: 16, borderRadius: 6 }}>
                {item.call_script}
              </pre>
              {item.merge_data?.talking_points?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.78rem', color: '#888',
                    textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                    Talking Points
                  </div>
                  <ul style={{ paddingLeft: 16 }}>
                    {item.merge_data.talking_points.map((pt, i) => (
                      <li key={i} style={{ fontSize: '0.83rem', color: '#d0d0d0', marginBottom: 4 }}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Meta */}
        <div style={{ padding: '10px 20px', borderTop: '1px solid #333',
          fontSize: '0.75rem', color: '#888', display: 'flex', gap: 16 }}>
          <span>Channel: {item.channel}</span>
          {item.qr_code && <span>QR: {item.qr_code}</span>}
          {item.sent_at && <span>Sent: {new Date(item.sent_at).toLocaleString()}</span>}
          {item.opened_at && <span>Opened: {new Date(item.opened_at).toLocaleString()}</span>}
          {item.qr_scanned_at && <span style={{ color: '#c8860a', fontWeight: 700 }}>
            QR Scanned: {new Date(item.qr_scanned_at).toLocaleString()}
          </span>}
        </div>
      </div>
    </div>
  )
}

// ── Mini components ───────────────────────────────────────────────────────────

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: color || 'var(--color-paper)', lineHeight: 1 }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontSize: '0.7rem', color: '#999', marginTop: 1 }}>{label}</div>
    </div>
  )
}

function ActionBtn({ icon: Icon, label, onClick, color, loading }) {
  return (
    <button onClick={onClick} disabled={loading} title={label}
      style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '4px 8px',
        borderRadius: 5, border: '1px solid #e0d8cc', background: '#2a2a2a',
        cursor: loading ? 'not-allowed' : 'pointer', color: loading ? '#ccc' : color,
        fontSize: '0.72rem', fontWeight: 600 }}>
      <Icon size={11} />
      {label}
    </button>
  )
}

function Loading() {
  return <div style={{ textAlign: 'center', padding: 40, color: '#aaa' }}>Loading…</div>
}

function ErrorBanner({ msg }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center',
      background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6,
      padding: '10px 14px', marginBottom: 16, fontSize: '0.83rem', color: '#b91c1c' }}>
      <AlertCircle size={14} /> {msg}
    </div>
  )
}

function Empty({ icon: Icon, text }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px',
      background: '#2a2a2a', borderRadius: 8, border: '1px solid #3a3a3a' }}>
      <Icon size={32} style={{ color: '#ddd', marginBottom: 10 }} />
      <p style={{ color: '#999', fontSize: '0.85rem', margin: 0 }}>{text}</p>
    </div>
  )
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputStyle = {
  padding: '8px 10px', borderRadius: 6, border: '1px solid #e0d8cc',
  fontSize: '0.83rem', width: '100%', background: '#2a2a2a',
}

const selectStyle = {
  padding: '6px 8px', borderRadius: 6, border: '1px solid #e0d8cc',
  fontSize: '0.78rem', background: '#2a2a2a', cursor: 'pointer',
}

const td = {
  padding: '9px 12px', borderBottom: '1px solid #f0ede6', verticalAlign: 'middle',
}

const stepCard = {
  display: 'flex', gap: 10, alignItems: 'center',
  background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: 8,
  padding: '12px 16px', flex: '1 1 220px',
}

const stepNum = {
  width: 24, height: 24, borderRadius: '50%', background: '#1f1f1f', color: '#f5c87a',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontSize: '0.78rem', fontWeight: 800, flexShrink: 0,
}

const stepTitle = {
  fontWeight: 700, fontSize: '0.83rem', color: '#e5e5e5', marginBottom: 6,
}

const actionBtn = {
  display: 'inline-flex', alignItems: 'center', gap: 5,
  padding: '5px 12px', borderRadius: 6, border: 'none',
  background: '#1f1f1f', color: '#f5c87a', fontSize: '0.78rem',
  fontWeight: 700, cursor: 'pointer',
}


// ── Main page ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'lists',   label: 'Prospect Lists', icon: Users },
  { id: 'review',  label: 'Review & Send',  icon: Send },
]

export default function Outreach() {
  const [tab, setTab] = useState('lists')
  const [drillList, setDrillList] = useState(null)

  const handleDrillIn = (list) => {
    setDrillList(list)
    setTab('lists') // stay on lists tab, show detail view
  }

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      {/* Page header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#e5e5e5', margin: '0 0 4px' }}>
          Outreach
        </h1>
        <p style={{ margin: 0, fontSize: '0.82rem', color: '#888' }}>
          Import prospects → score → generate → approve → send
        </p>
      </div>

      {/* Tabs */}
      {!drillList && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #333', paddingBottom: 1 }}>
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 16px', background: 'none', border: 'none',
                borderBottom: tab === id ? '2px solid #c8860a' : '2px solid transparent',
                color: tab === id ? '#f5c87a' : '#888',
                fontWeight: tab === id ? 700 : 500,
                fontSize: '0.85rem', cursor: 'pointer', marginBottom: -1,
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {tab === 'lists' && !drillList && (
        <ProspectListsTab onDrillIn={handleDrillIn} />
      )}
      {tab === 'lists' && drillList && (
        <ListDetailTab list={drillList} onBack={() => setDrillList(null)} />
      )}
      {tab === 'review' && <ReviewTab />}
    </div>
  )
}

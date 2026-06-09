/**
 * ContentStudio — Full content production hub.
 *
 * Tabs:
 *   Generate    — create new AI content
 *   Library     — review, inline-edit, run pipeline, publish
 *   Templates   — manage script templates (hooks, CTAs, style guides)
 *   Performance — agent performance analysis + decisions
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../utils/api'
import {
  Sparkles, Copy, CheckCircle, Clock, Send, Mic, Video,
  Pencil, X, Check, ChevronDown, ChevronUp, RefreshCw,
  Plus, Trash2, AlertCircle, Play, Pause, Settings2,
  TrendingUp, TrendingDown, Minus, BarChart3, Globe,
  Image as ImageIcon, Upload, Download, Eye, Loader,
} from 'lucide-react'

// ── Design tokens ────────────────────────────────────────────────────────────
const WARM   = '#c8860a'
const GOLD   = '#f5c87a'
const DARK   = '#1f1f1f'
const MUTED  = '#888'
const PAPER  = '#fffbf5'
const BORDER = '#e8e4dc'

const PLATFORMS = [
  'tiktok','instagram_reel','instagram_carousel',
  'facebook','linkedin','google_business','email_snippet',
]
const CATEGORIES = [
  'dpa_myths','fha_education','heloc_strategy','dscr_investor',
  'refi_triggers','underwriting_mistakes','credit_readiness',
  'realtor_education','open_house','market_update',
]
const TEMPLATE_TYPES = [
  { value: 'style_guide',  label: 'Style Guide'  },
  { value: 'hook',         label: 'Hook Example' },
  { value: 'cta',          label: 'CTA Style'    },
  { value: 'full_script',  label: 'Full Script'  },
  { value: 'objection',    label: 'Objection Handler' },
  { value: 'tone_guide',   label: 'Tone Guide'   },
]

const STATUS_COLORS = {
  pending:     { bg: '#fffbf2', color: WARM      },
  approved:    { bg: '#f0fdf0', color: '#2e7d32' },
  rejected:    { bg: '#fef2f2', color: '#b91c1c' },
  scheduled:   { bg: '#e8f0fe', color: '#1565c0' },
  published:   { bg: '#f0fdf0', color: '#2e7d32' },
  needs_edit:  { bg: '#fafafa', color: '#999'    },
}

const STAGE_LABELS = {
  script_only:       { label: 'Script', color: '#aaa'    },
  voice_ready:       { label: 'Voice ✓', color: '#1565c0' },
  video_processing:  { label: 'Rendering…', color: WARM  },
  video_ready:       { label: 'Video ✓', color: '#2e7d32' },
  assembled:         { label: 'Assembled', color: '#7b1fa2' },
  published:         { label: 'Live', color: '#2e7d32'   },
}

// ── Shared small components ───────────────────────────────────────────────────

function StatusBadge({ status }) {
  const s = STATUS_COLORS[status] || { bg: '#f5f5f5', color: '#999' }
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 10, fontSize: '0.7rem',
      fontWeight: 700, background: s.bg, color: s.color,
    }}>{status?.replace(/_/g, ' ')}</span>
  )
}

function StageBadge({ stage }) {
  const s = STAGE_LABELS[stage] || { label: stage || 'draft', color: '#aaa' }
  return (
    <span style={{
      padding: '2px 7px', borderRadius: 10, fontSize: '0.7rem', fontWeight: 600,
      background: `${s.color}18`, color: s.color, border: `1px solid ${s.color}40`,
    }}>{s.label}</span>
  )
}

function Field({ label, value, onSave, multiline = false, placeholder = 'Click to edit…' }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState(value || '')
  const [saving, setSaving]   = useState(false)
  const taRef = useRef(null)

  useEffect(() => { setDraft(value || '') }, [value])
  useEffect(() => { if (editing && taRef.current) taRef.current.focus() }, [editing])

  const save = async () => {
    if (draft === value) { setEditing(false); return }
    setSaving(true)
    try { await onSave(draft) } finally { setSaving(false); setEditing(false) }
  }

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.07em', color: MUTED, marginBottom: 4 }}>
        {label}
      </div>
      {editing ? (
        <div>
          {multiline
            ? <textarea ref={taRef} value={draft} onChange={e => setDraft(e.target.value)}
                rows={Math.max(3, draft.split('\n').length + 1)}
                style={{ width: '100%', padding: '8px 10px', border: `1px solid ${GOLD}`,
                  borderRadius: 6, fontSize: '0.82rem', fontFamily: 'inherit',
                  resize: 'vertical', background: PAPER, outline: 'none' }} />
            : <input ref={taRef} value={draft} onChange={e => setDraft(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', border: `1px solid ${GOLD}`,
                  borderRadius: 6, fontSize: '0.82rem', background: PAPER, outline: 'none' }} />
          }
          <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
            <button onClick={save} disabled={saving} style={{
              display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
              borderRadius: 5, background: DARK, color: GOLD, border: 'none',
              cursor: 'pointer', fontSize: '0.75rem', fontWeight: 700,
            }}>
              <Check size={11} /> {saving ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => { setDraft(value || ''); setEditing(false) }} style={{
              padding: '4px 8px', borderRadius: 5, background: '#f0ece4',
              color: MUTED, border: 'none', cursor: 'pointer', fontSize: '0.75rem',
            }}>Cancel</button>
          </div>
        </div>
      ) : (
        <div
          onClick={() => setEditing(true)}
          style={{
            padding: '8px 10px', borderRadius: 6, background: '#252525',
            border: `1px solid ${BORDER}`, cursor: 'text', minHeight: 36,
            fontSize: '0.82rem', color: value ? DARK : '#ccc', lineHeight: 1.55,
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            gap: 8,
          }}
        >
          <span style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {value || placeholder}
          </span>
          <Pencil size={11} style={{ color: '#ccc', flexShrink: 0, marginTop: 3 }} />
        </div>
      )}
    </div>
  )
}

function AudioPlayer({ url }) {
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef(null)

  const toggle = () => {
    if (!audioRef.current) return
    if (playing) { audioRef.current.pause(); setPlaying(false) }
    else         { audioRef.current.play();  setPlaying(true)  }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10,
      background: '#e8f0fe', borderRadius: 8, padding: '8px 12px' }}>
      <button onClick={toggle} style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: 30, height: 30, borderRadius: '50%', background: '#1565c0',
        border: 'none', cursor: 'pointer', color: '#fff',
      }}>
        {playing ? <Pause size={13} /> : <Play size={13} />}
      </button>
      <span style={{ fontSize: '0.78rem', color: '#1565c0', fontWeight: 600 }}>Voiceover</span>
      <audio ref={audioRef} src={url} onEnded={() => setPlaying(false)} />
    </div>
  )
}

// ── Post card ─────────────────────────────────────────────────────────────────

function PostCard({ post: initialPost, onUpdated }) {
  const [post, setPost]     = useState(initialPost)
  const [open, setOpen]     = useState(false)
  const [busy, setBusy]     = useState(false)
  const [msg, setMsg]       = useState('')

  const update = async (fields) => {
    const updated = await api.patch(`/content/posts/${post.id}`, fields)
    setPost(updated)
    onUpdated && onUpdated(updated)
    return updated
  }

  const approve = async (action, reason) => {
    const updated = await api.patch(`/content/posts/${post.id}/approve`, { action, rejection_reason: reason })
    setPost(updated)
    onUpdated && onUpdated(updated)
  }

  const runVoice = async () => {
    setBusy(true); setMsg('')
    try {
      await api.post(`/content/posts/${post.id}/generate-voice`)
      const updated = await api.get(`/content/posts?limit=1&platform=${post.platform}`)
      // Refetch this post
      setMsg('Voice generated ✓')
      setTimeout(() => setMsg(''), 3000)
    } catch (e) { setMsg(`Voice failed: ${e.message}`) }
    finally { setBusy(false) }
  }

  const runVideo = async () => {
    setBusy(true); setMsg('')
    try {
      const r = await api.post(`/content/posts/${post.id}/generate-video?test_mode=true`)
      setPost(p => ({
        ...p,
        pipeline_stage: 'video_processing',
        media_asset_ids: [...(p.media_asset_ids || []), { type: 'video_raw', provider_id: r.provider_id, status: 'processing' }]
      }))
      setMsg(`Video submitted (ID: ${r.provider_id}) — check status in a few minutes`)
    } catch (e) { setMsg(`Video failed: ${e.message}`) }
    finally { setBusy(false) }
  }

  const publish = async () => {
    setBusy(true); setMsg('')
    try {
      const r = await api.post(`/content/posts/${post.id}/publish`, {
        platform: post.platform,
        caption_override: post.caption,
      })
      if (r.success) {
        setPost(p => ({ ...p, approval_status: 'published' }))
        setMsg(`Published! ${r.platform_url || ''}`)
      } else {
        setMsg(`Publish failed: ${r.error}`)
      }
    } catch (e) { setMsg(`Publish error: ${e.message}`) }
    finally { setBusy(false) }
  }

  const copy = (text) => navigator.clipboard.writeText(text || '')

  const audioAsset = (post.media_asset_ids || []).find(m => m.type === 'audio')
  const videoAsset = (post.media_asset_ids || []).find(m => ['video_raw','video_final'].includes(m.type))

  return (
    <div style={{
      background: '#2a2a2a', borderRadius: 10, marginBottom: 10,
      border: `1px solid ${BORDER}`, overflow: 'hidden',
    }}>
      {/* Header row */}
      <div onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '12px 16px', cursor: 'pointer', userSelect: 'none',
      }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: MUTED,
          background: '#f0ece4', padding: '2px 7px', borderRadius: 8 }}>
          {post.platform?.replace(/_/g,' ')}
        </span>
        <span style={{ fontSize: '0.72rem', color: '#aaa', background: '#f9f9f9',
          padding: '2px 7px', borderRadius: 8 }}>
          {post.category?.replace(/_/g,' ')}
        </span>
        <span style={{ flex: 1, fontSize: '0.85rem', color: DARK, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {post.hook || '(no hook yet)'}
        </span>
        <StageBadge stage={post.pipeline_stage} />
        <StatusBadge status={post.approval_status} />
        {open ? <ChevronUp size={14} color={MUTED} /> : <ChevronDown size={14} color={MUTED} />}
      </div>

      {open && (
        <div style={{ borderTop: `1px solid ${BORDER}`, padding: '16px' }}>
          {/* Audio / video players */}
          {audioAsset?.url && (
            <div style={{ marginBottom: 14 }}>
              <AudioPlayer url={audioAsset.url} />
            </div>
          )}
          {videoAsset?.url && (
            <div style={{ marginBottom: 14 }}>
              <video
                src={videoAsset.url}
                controls
                style={{ width: '100%', maxWidth: 320, borderRadius: 8, background: '#000' }}
              />
            </div>
          )}

          {/* Editable fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
            <Field label="Hook" value={post.hook} multiline={false}
              onSave={v => update({ hook: v })} />
            <Field label="CTA" value={post.cta} multiline={false}
              onSave={v => update({ cta: v })} />
            <Field label="Script (full)" value={post.script} multiline
              onSave={v => update({ script: v })} />
            <Field label="Voiceover Script" value={post.voiceover_script} multiline
              onSave={v => update({ voiceover_script: v })} />
            <Field label="Caption" value={post.caption} multiline
              onSave={v => update({ caption: v })} />
            <Field label="Visual Concept" value={post.visual_concept} multiline
              onSave={v => update({ visual_concept: v })} />
            <Field label="Video Prompt" value={post.video_prompt} multiline
              onSave={v => update({ video_prompt: v })} />
            <Field label="B-roll Instructions" value={post.broll_instructions} multiline
              onSave={v => update({ broll_instructions: v })} />
          </div>

          {post.compliance_notes && (
            <div style={{ marginTop: 4, padding: '8px 12px', background: '#252525',
              borderRadius: 6, border: `1px solid #f0d58c`, fontSize: '0.78rem', color: '#7a5a00' }}>
              <strong>Compliance:</strong> {post.compliance_notes}
            </div>
          )}

          {msg && (
            <div style={{ marginTop: 10, padding: '8px 12px', borderRadius: 6,
              background: msg.includes('failed') || msg.includes('error') ? '#fef2f2' : '#f0fdf0',
              color:  msg.includes('failed') || msg.includes('error') ? '#b91c1c' : '#2e7d32',
              fontSize: '0.8rem' }}>
              {msg}
            </div>
          )}

          {/* Action bar */}
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap', alignItems: 'center' }}>

            {/* Approval actions */}
            {post.approval_status === 'pending' && (<>
              <button onClick={() => approve('approve')} style={btnStyle('#2e7d32')}>
                <CheckCircle size={12} /> Approve
              </button>
              <button onClick={() => approve('needs_edit', 'needs revision')} style={btnStyle('#555')}>
                Needs Edit
              </button>
              <button onClick={() => approve('reject', '')} style={btnStyle('#b91c1c')}>
                <X size={12} /> Reject
              </button>
            </>)}

            {/* Pipeline actions */}
            {!audioAsset && (
              <button onClick={runVoice} disabled={busy} style={btnStyle('#1565c0')}>
                <Mic size={12} /> {busy ? 'Generating…' : 'Gen Voice'}
              </button>
            )}

            {audioAsset && !videoAsset && (
              <button onClick={runVideo} disabled={busy} style={btnStyle(WARM)}>
                <Video size={12} /> {busy ? 'Submitting…' : 'Gen Video'}
              </button>
            )}

            {/* Publish */}
            {post.approval_status === 'approved' && videoAsset && (
              <button onClick={publish} disabled={busy} style={btnStyle(DARK, GOLD)}>
                <Send size={12} /> {busy ? 'Publishing…' : 'Publish'}
              </button>
            )}

            {/* Copy hook */}
            <button onClick={() => copy(post.hook)} style={btnStyle('#aaa', '#fff')}>
              <Copy size={12} /> Copy Hook
            </button>

            {post.approval_status === 'published' && post.external_post_id && (
              <span style={{ fontSize: '0.75rem', color: '#2e7d32', fontWeight: 700 }}>
                ✓ Live · ID: {post.external_post_id}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const btnStyle = (color, textColor = '#fff') => ({
  display: 'flex', alignItems: 'center', gap: 4,
  padding: '5px 10px', borderRadius: 6, fontSize: '0.75rem',
  fontWeight: 700, cursor: 'pointer', border: 'none',
  background: color, color: textColor,
})


// ── Templates tab ─────────────────────────────────────────────────────────────

function TemplatesTab() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading]     = useState(true)
  const [creating, setCreating]   = useState(false)
  const [editing, setEditing]     = useState(null)
  const [form, setForm]           = useState({
    name: '', template_type: 'style_guide', platform: '', category: '',
    content: '', is_active: true, priority: 0, description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get('/content/script-templates?active_only=false')
      setTemplates(data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    try {
      if (editing) {
        await api.patch(`/content/script-templates/${editing}`, form)
      } else {
        await api.post('/content/script-templates', form)
      }
      setCreating(false); setEditing(null)
      setForm({ name:'', template_type:'style_guide', platform:'', category:'', content:'', is_active:true, priority:0, description:'' })
      load()
    } catch (e) { alert(e.message) }
  }

  const del = async (id) => {
    if (!confirm('Delete this template?')) return
    await api.delete(`/content/script-templates/${id}`)
    load()
  }

  const startEdit = (t) => {
    setForm({ name: t.name, template_type: t.template_type, platform: t.platform || '',
      category: t.category || '', content: t.content, is_active: t.is_active,
      priority: t.priority, description: t.description || '' })
    setEditing(t.id)
    setCreating(true)
  }

  const typeLabel = (v) => TEMPLATE_TYPES.find(t => t.value === v)?.label || v

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>Script Templates</h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: MUTED }}>
            Templates are injected into the AI prompt automatically. Edit here → changes affect all future generation.
          </p>
        </div>
        <button onClick={() => { setEditing(null); setCreating(true) }} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '7px 14px', borderRadius: 8, background: DARK, color: GOLD,
          border: 'none', cursor: 'pointer', fontSize: '0.82rem', fontWeight: 700,
        }}>
          <Plus size={13} /> New Template
        </button>
      </div>

      {/* Create / edit form */}
      {creating && (
        <div style={{ background: '#2a2a2a', border: `1px solid ${BORDER}`, borderRadius: 10,
          padding: 20, marginBottom: 16 }}>
          <h3 style={{ margin: '0 0 14px', fontSize: '0.9rem', fontWeight: 800 }}>
            {editing ? 'Edit Template' : 'New Template'}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div>
              <label style={labelSty}>Name</label>
              <input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))}
                style={inputSty} placeholder="e.g. DPA Hook Bank 1" />
            </div>
            <div>
              <label style={labelSty}>Type</label>
              <select value={form.template_type} onChange={e => setForm(f => ({...f, template_type: e.target.value}))}
                style={inputSty}>
                {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label style={labelSty}>Platform (blank = all)</label>
              <select value={form.platform} onChange={e => setForm(f => ({...f, platform: e.target.value}))}
                style={inputSty}>
                <option value="">All platforms</option>
                {PLATFORMS.map(p => <option key={p} value={p}>{p.replace(/_/g,' ')}</option>)}
              </select>
            </div>
            <div>
              <label style={labelSty}>Category (blank = all)</label>
              <select value={form.category} onChange={e => setForm(f => ({...f, category: e.target.value}))}
                style={inputSty}>
                <option value="">All categories</option>
                {CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g,' ')}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={labelSty}>Content — this is what the AI sees</label>
            <textarea value={form.content} onChange={e => setForm(f => ({...f, content: e.target.value}))}
              rows={6} style={{ ...inputSty, resize: 'vertical', fontFamily: 'inherit' }}
              placeholder="e.g. Always open with a personal story or relatable scenario. Avoid corporate language. The banker speaks like a helpful neighbor, not a salesman..." />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={save} style={btnStyle(DARK, GOLD)}>
              <Check size={12} /> Save Template
            </button>
            <button onClick={() => { setCreating(false); setEditing(null) }} style={btnStyle('#aaa')}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', color: MUTED, padding: 32 }}>Loading templates…</div>
      ) : templates.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 24px', background: '#2a2a2a',
          borderRadius: 10, border: `1px solid ${BORDER}` }}>
          <Settings2 size={28} style={{ color: '#ddd', marginBottom: 10 }} />
          <p style={{ color: MUTED, margin: 0, fontSize: '0.85rem' }}>
            No templates yet. Create your first style guide to start shaping AI output.
          </p>
        </div>
      ) : (
        templates.map(t => (
          <div key={t.id} style={{ background: '#2a2a2a', border: `1px solid ${BORDER}`,
            borderRadius: 8, padding: '12px 16px', marginBottom: 8,
            display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>{t.name}</span>
                <span style={{ fontSize: '0.7rem', color: '#1565c0', background: '#e8f0fe',
                  padding: '2px 6px', borderRadius: 6, fontWeight: 600 }}>
                  {typeLabel(t.template_type)}
                </span>
                {t.platform && (
                  <span style={{ fontSize: '0.7rem', color: WARM, background: '#252525',
                    padding: '2px 6px', borderRadius: 6 }}>{t.platform}</span>
                )}
                {t.category && (
                  <span style={{ fontSize: '0.7rem', color: '#999', background: '#f0ece4',
                    padding: '2px 6px', borderRadius: 6 }}>{t.category.replace(/_/g,' ')}</span>
                )}
                {!t.is_active && (
                  <span style={{ fontSize: '0.7rem', color: '#aaa', background: '#252525',
                    padding: '2px 6px', borderRadius: 6 }}>inactive</span>
                )}
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#999', lineHeight: 1.5,
                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {t.content}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
              <button onClick={() => startEdit(t)} style={{
                padding: '4px 8px', borderRadius: 5, background: '#f0ece4',
                border: 'none', cursor: 'pointer', color: MUTED }}>
                <Pencil size={12} />
              </button>
              <button onClick={() => del(t.id)} style={{
                padding: '4px 8px', borderRadius: 5, background: '#fef2f2',
                border: 'none', cursor: 'pointer', color: '#b91c1c' }}>
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  )
}


// ── Performance tab ───────────────────────────────────────────────────────────

function PerformanceTab() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [days, setDays]     = useState(30)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.post('/agent/analyze-performance', { days })
      setData(r)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [days])

  useEffect(() => { load() }, [load])

  const DecisionCard = ({ d }) => {
    const icons = {
      pause:  { icon: TrendingDown, color: '#b91c1c', bg: '#fef2f2' },
      adjust: { icon: Settings2,    color: WARM,       bg: '#fffbf2' },
      scale:  { icon: TrendingUp,   color: '#2e7d32',  bg: '#f0fdf0' },
      review: { icon: Clock,        color: '#1565c0',  bg: '#e8f0fe' },
      alert:  { icon: AlertCircle,  color: '#999',     bg: '#f5f5f5' },
    }
    const meta  = icons[d.type] || icons.alert
    const Icon  = meta.icon
    return (
      <div style={{ padding: '12px 14px', borderRadius: 8, background: meta.bg,
        border: `1px solid ${meta.color}30`, marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Icon size={14} style={{ color: meta.color }} />
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: meta.color,
            textTransform: 'uppercase', letterSpacing: '0.06em' }}>{d.type}</span>
          <span style={{ fontSize: '0.75rem', color: MUTED }}>
            {d.category || d.platform || d.target}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '0.8rem', color: DARK, lineHeight: 1.5 }}>
          {d.reason}
        </p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>Agent Performance Analysis</h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: MUTED }}>
            What's working, what to pause, what to scale.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 14, 30, 60].map(d => (
            <button key={d} onClick={() => setDays(d)} style={{
              padding: '5px 10px', borderRadius: 20, fontSize: '0.75rem', fontWeight: 600,
              cursor: 'pointer', border: `1px solid ${BORDER}`,
              background: days === d ? DARK : '#fff', color: days === d ? GOLD : '#666',
            }}>{d}d</button>
          ))}
          <button onClick={load} style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '5px 10px', borderRadius: 20, fontSize: '0.75rem',
            cursor: 'pointer', border: `1px solid ${BORDER}`, background: '#2a2a2a', color: MUTED,
          }}><RefreshCw size={12} /></button>
        </div>
      </div>

      {loading && <div style={{ textAlign: 'center', color: MUTED, padding: 40 }}>Analyzing…</div>}

      {data && !loading && (
        <>
          {/* KPI row */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
            {[
              { label: 'Generated', value: data.total_generated },
              { label: 'Approval Rate', value: `${Math.round(data.overall_approval_rate * 100)}%` },
              { label: 'Video Cost Est.', value: `$${data.cost_estimate_usd?.toFixed(2)}` },
              { label: 'Best Category', value: data.best_performing_category?.replace(/_/g,' ') || '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{ flex: 1, minWidth: 120, background: '#2a2a2a',
                border: `1px solid ${BORDER}`, borderRadius: 10, padding: '12px 16px' }}>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase',
                  letterSpacing: '0.07em', color: MUTED, marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 900, color: DARK }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Recommendation */}
          <div style={{ padding: '12px 16px', background: DARK, borderRadius: 10,
            color: GOLD, fontSize: '0.85rem', lineHeight: 1.6, marginBottom: 16 }}>
            <strong>Agent recommendation:</strong> {data.recommendation}
          </div>

          {/* Decisions */}
          {data.decisions?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: '0.82rem', fontWeight: 800, color: MUTED,
                textTransform: 'uppercase', letterSpacing: '0.07em', margin: '0 0 10px' }}>
                Decisions
              </h3>
              {data.decisions.map((d, i) => <DecisionCard key={i} d={d} />)}
            </div>
          )}

          {/* Category breakdown */}
          {Object.keys(data.by_category || {}).length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.82rem', fontWeight: 800, color: MUTED,
                textTransform: 'uppercase', letterSpacing: '0.07em', margin: '0 0 10px' }}>
                By Category
              </h3>
              <div style={{ background: '#2a2a2a', borderRadius: 10, border: `1px solid ${BORDER}`, overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: PAPER }}>
                      {['Category','Generated','Approved','Published','Approval %'].map(h => (
                        <th key={h} style={{ padding: '8px 12px', fontSize: '0.7rem', fontWeight: 700,
                          textTransform: 'uppercase', letterSpacing: '0.06em', color: MUTED,
                          textAlign: h === 'Category' ? 'left' : 'right' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.by_category).map(([cat, s]) => (
                      <tr key={cat} style={{ borderTop: `1px solid ${BORDER}` }}>
                        <td style={{ padding: '9px 12px', fontSize: '0.82rem', fontWeight: 600 }}>
                          {cat.replace(/_/g,' ')}
                        </td>
                        <td style={{ padding: '9px 12px', textAlign: 'right', fontSize: '0.82rem' }}>{s.total}</td>
                        <td style={{ padding: '9px 12px', textAlign: 'right', fontSize: '0.82rem' }}>{s.approved}</td>
                        <td style={{ padding: '9px 12px', textAlign: 'right', fontSize: '0.82rem' }}>{s.published}</td>
                        <td style={{ padding: '9px 12px', textAlign: 'right', fontSize: '0.82rem',
                          fontWeight: 700, color: s.approval_rate >= 0.7 ? '#2e7d32' : s.approval_rate >= 0.5 ? WARM : '#b91c1c' }}>
                          {Math.round(s.approval_rate * 100)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.status === 'no_data' && (
            <div style={{ textAlign: 'center', padding: '40px 24px', color: MUTED, fontSize: '0.85rem' }}>
              No content generated in the last {days} days. Generate some posts first.
            </div>
          )}
        </>
      )}
    </div>
  )
}


// ── Generate tab ──────────────────────────────────────────────────────────────

function GenerateTab({ onGenerated }) {
  const [form, setForm]           = useState({ platform: 'tiktok', category: 'dpa_myths', product_id: '' })
  const [products, setProducts]   = useState([])
  const [generating, setGenerating] = useState(false)
  const [result, setResult]       = useState(null)

  useEffect(() => {
    api.get('/products/').then(setProducts).catch(() => {})
  }, [])

  const generate = async () => {
    setGenerating(true); setResult(null)
    try {
      const r = await api.post('/content/generate', form)
      setResult(r)
      onGenerated && onGenerated(r.post)
    } catch (e) { setResult({ error: e.message }) }
    finally { setGenerating(false) }
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <div style={{ background: '#2a2a2a', borderRadius: 10, border: `1px solid ${BORDER}`, padding: 20, marginBottom: 16 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: '0.9rem', fontWeight: 800 }}>Generate New Post</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={labelSty}>Platform</label>
            <select style={inputSty} value={form.platform} onChange={e => setForm(f => ({...f, platform: e.target.value}))}>
              {PLATFORMS.map(p => <option key={p} value={p}>{p.replace(/_/g,' ')}</option>)}
            </select>
          </div>
          <div>
            <label style={labelSty}>Content Category</label>
            <select style={inputSty} value={form.category} onChange={e => setForm(f => ({...f, category: e.target.value}))}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g,' ')}</option>)}
            </select>
          </div>
          <div>
            <label style={labelSty}>Product Context (optional)</label>
            <select style={inputSty} value={form.product_id} onChange={e => setForm(f => ({...f, product_id: e.target.value}))}>
              <option value="">No specific product</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div style={{ padding: '10px 12px', background: PAPER, borderRadius: 6,
            fontSize: '0.75rem', color: MUTED, borderLeft: `3px solid ${GOLD}` }}>
            Script templates are loaded automatically. Manage them in the Templates tab.
          </div>
          <button onClick={generate} disabled={generating} style={{
            display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center',
            padding: '9px 16px', borderRadius: 8, background: DARK, color: GOLD,
            border: 'none', cursor: generating ? 'not-allowed' : 'pointer',
            fontSize: '0.85rem', fontWeight: 700,
          }}>
            <Sparkles size={14} /> {generating ? 'Generating…' : 'Generate Post'}
          </button>
        </div>
      </div>

      {result?.error && (
        <div style={{ padding: '10px 14px', borderRadius: 8, background: '#fef2f2',
          color: '#b91c1c', fontSize: '0.82rem' }}>
          {result.error}
        </div>
      )}
      {result?.post && (
        <div style={{ padding: '12px 16px', background: '#f0fdf0', borderRadius: 8,
          border: '1px solid #bbf7d0', fontSize: '0.82rem', color: '#2e7d32' }}>
          <strong>Generated!</strong> Switching to Library…
          {result.compliance?.flags?.length > 0 && (
            <p style={{ margin: '6px 0 0', color: WARM }}>
              ⚠ {result.compliance.flags.length} compliance flag(s) — review before approving.
            </p>
          )}
          {result.templates_used && (
            <p style={{ margin: '4px 0 0', color: '#2e7d32', fontSize: '0.75rem' }}>
              ✓ Script templates were applied.
            </p>
          )}
        </div>
      )}
    </div>
  )
}


// ── Campaign Builder tab ──────────────────────────────────────────────────────

const AVATARS = [
  { value: 'declined_buyer',   label: 'Declined Buyer',      desc: 'Was rejected by a bank — needs a new path' },
  { value: 'first_timer',      label: 'First-Time Buyer',    desc: 'Doesn\'t know where to start, fears 20% down' },
  { value: 'equity_prisoner',  label: 'Equity Prisoner',     desc: 'Has equity but can\'t access it' },
  { value: 'realtor_client',   label: 'Realtor\'s Client',   desc: 'Active buyer needing fast close + pre-approval' },
]
const PRODUCTS_AD = [
  { value: 'fha',          label: 'FHA Loan' },
  { value: 'va',           label: 'VA Loan' },
  { value: 'dpa',          label: 'Down Payment Assistance' },
  { value: 'conventional', label: 'Conventional' },
  { value: 'heloc',        label: 'HELOC / Equity Access' },
  { value: 'dscr',         label: 'DSCR Investor' },
  { value: 'refi',         label: 'Refinance' },
]
const BUDGETS = [
  { value: 'low',   label: '$500–1k/mo' },
  { value: 'mid',   label: '$1–3k/mo' },
  { value: 'scale', label: '$3k+/mo' },
]

function CampaignBuilderTab() {
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const [form, setForm] = useState({
    avatar: 'declined_buyer',
    product: 'fha',
    proof: '',
    market: 'MD',
    budget_hint: 'low',
    flyer_id: null,
  })
  const [status, setStatus]         = useState('idle') // idle | running | done | error
  const [result, setResult]         = useState(null)
  const [pages, setPages]           = useState([])
  const [loadingPages, setLoadingPages] = useState(true)
  const [publishing, setPublishing] = useState({})
  const [completedFlyers, setCompletedFlyers] = useState([])
  const [flyerPickerOpen, setFlyerPickerOpen] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const loadPages = () => {
    api.get('/campaigns/pages')
      .then(setPages)
      .catch(() => {})
      .finally(() => setLoadingPages(false))
  }

  useEffect(() => {
    loadPages()
    // Load completed flyers for the creative picker
    api.get('/flyers/?status=complete&limit=30')
      .then(r => setCompletedFlyers(r.flyers || []))
      .catch(() => {})
  }, [])

  const runBuild = async () => {
    setStatus('running')
    setResult(null)
    try {
      // Uses the agent endpoint — must have AGENT_API_KEY set in admin
      // The admin token is used here; agent key is handled server-side for this flow
      const res = await api.post('/content/build-campaign', form)
      setResult(res)
      setStatus('done')
      loadPages()
    } catch (e) {
      setResult({ error: e.message || 'Build failed' })
      setStatus('error')
    }
  }

  const togglePublish = async (slug) => {
    setPublishing(p => ({ ...p, [slug]: true }))
    try {
      await api.patch(`/campaigns/pages/${slug}/publish`, {})
      loadPages()
    } catch {}
    setPublishing(p => ({ ...p, [slug]: false }))
  }

  const avatarInfo = AVATARS.find(a => a.value === form.avatar)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'start' }} className="campaign-builder-grid">

      {/* Left — build form */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ background: '#2a2a2a', border: `1px solid ${BORDER}`, borderRadius: 10, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <Sparkles size={15} color={WARM} />
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, color: DARK }}>Build Ad Campaign</h3>
          </div>
          <p style={{ margin: '0 0 16px', fontSize: '0.78rem', color: MUTED, lineHeight: 1.5 }}>
            Runs the 9-step advertising chain: Avatar → Awareness → Mechanism → Ad Copy → Sales Letter → Emails.
            All assets go to the Approval Queue first.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Avatar */}
            <div>
              <label style={labelSty}>Target Avatar</label>
              <select style={inputSty} value={form.avatar} onChange={e => set('avatar', e.target.value)}>
                {AVATARS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
              </select>
              {avatarInfo && (
                <div style={{ marginTop: 5, fontSize: '0.72rem', color: MUTED, fontStyle: 'italic' }}>
                  {avatarInfo.desc}
                </div>
              )}
            </div>

            {/* Product */}
            <div>
              <label style={labelSty}>Loan Product</label>
              <select style={inputSty} value={form.product} onChange={e => set('product', e.target.value)}>
                {PRODUCTS_AD.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>

            {/* Market */}
            <div>
              <label style={labelSty}>Market</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {['MD', 'DC', 'both'].map(m => (
                  <button
                    key={m}
                    onClick={() => set('market', m)}
                    style={{
                      flex: 1, padding: '7px 0',
                      background: form.market === m ? DARK : '#fff',
                      color: form.market === m ? '#fff' : '#555',
                      border: `1px solid ${form.market === m ? DARK : BORDER}`,
                      borderRadius: 6, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    {m === 'both' ? 'MD & DC' : m}
                  </button>
                ))}
              </div>
            </div>

            {/* Budget */}
            <div>
              <label style={labelSty}>Ad Budget Hint</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {BUDGETS.map(b => (
                  <button
                    key={b.value}
                    onClick={() => set('budget_hint', b.value)}
                    style={{
                      flex: 1, padding: '7px 0',
                      background: form.budget_hint === b.value ? DARK : '#fff',
                      color: form.budget_hint === b.value ? '#fff' : '#555',
                      border: `1px solid ${form.budget_hint === b.value ? DARK : BORDER}`,
                      borderRadius: 6, fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Proof point */}
            <div>
              <label style={labelSty}>Proof Point (optional but powerful)</label>
              <textarea
                rows={2}
                style={{ ...inputSty, resize: 'vertical', fontFamily: 'inherit' }}
                placeholder='e.g. "Closed $390k FHA in 9 days for a buyer in Bowie MD who had been declined twice"'
                value={form.proof}
                onChange={e => set('proof', e.target.value)}
              />
              <div style={{ fontSize: '0.7rem', color: MUTED, marginTop: 4 }}>
                Real results make copy 3× more credible.
              </div>
            </div>

            {/* ── Flyer creative picker ───────────────────────────── */}
            <div>
              <label style={labelSty}>Visual Creative (optional)</label>
              {form.flyer_id ? (
                <div style={{ display: 'flex', gap: 10, alignItems: 'center',
                  border: `1.5px solid ${GOLD}`, borderRadius: 8, padding: '8px 10px', background: '#252525' }}>
                  {(() => {
                    const f = completedFlyers.find(x => x.id === form.flyer_id)
                    return f?.flyer_image_url ? (
                      <img src={f.flyer_image_url} alt="selected flyer"
                           style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6, border: `1px solid ${BORDER}` }} />
                    ) : <ImageIcon size={32} color={BORDER} />
                  })()}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: '0.75rem', fontWeight: 700, color: DARK,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {completedFlyers.find(x => x.id === form.flyer_id)?.headline || `Flyer #${form.flyer_id}`}
                    </p>
                    <p style={{ margin: '2px 0 0', fontSize: '0.68rem', color: MUTED }}>
                      AI copy will be written around this image
                    </p>
                  </div>
                  <button onClick={() => set('flyer_id', null)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTED, padding: 0 }}>
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setFlyerPickerOpen(p => !p)}
                  style={{
                    width: '100%', padding: '8px 12px', border: `1.5px dashed ${BORDER}`,
                    borderRadius: 8, background: '#252525', cursor: 'pointer',
                    fontSize: '0.78rem', color: MUTED, display: 'flex', alignItems: 'center',
                    gap: 6, justifyContent: 'center',
                  }}
                >
                  <ImageIcon size={13} /> Attach a generated flyer →
                </button>
              )}

              {/* Flyer thumbnail grid picker */}
              {flyerPickerOpen && !form.flyer_id && (
                <div style={{ marginTop: 8, border: `1px solid ${BORDER}`, borderRadius: 8,
                  background: '#2a2a2a', padding: 10, maxHeight: 220, overflowY: 'auto' }}>
                  {completedFlyers.length === 0 ? (
                    <p style={{ margin: 0, fontSize: '0.75rem', color: MUTED, textAlign: 'center', padding: '16px 0' }}>
                      No completed flyers yet. Generate one in the Flyers tab first.
                    </p>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                      {completedFlyers.map(f => (
                        <div
                          key={f.id}
                          onClick={() => { set('flyer_id', f.id); setFlyerPickerOpen(false) }}
                          style={{ cursor: 'pointer', borderRadius: 6, overflow: 'hidden',
                            border: `1.5px solid ${BORDER}`, transition: 'border-color 0.15s' }}
                          onMouseEnter={e => e.currentTarget.style.borderColor = WARM}
                          onMouseLeave={e => e.currentTarget.style.borderColor = BORDER}
                        >
                          {f.flyer_image_url ? (
                            <img src={f.flyer_image_url} alt={f.headline}
                                 style={{ width: '100%', height: 70, objectFit: 'cover', display: 'block' }} />
                          ) : (
                            <div style={{ height: 70, background: '#f5f5f0', display: 'flex',
                              alignItems: 'center', justifyContent: 'center' }}>
                              <ImageIcon size={18} color={BORDER} />
                            </div>
                          )}
                          <p style={{ margin: 0, fontSize: '0.62rem', padding: '4px 6px',
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            color: DARK, fontWeight: 600 }}>
                            {f.headline}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: MUTED }}>
                Attach a flyer and the AI writes copy that complements the image. It also embeds in the email sequence.
              </p>
            </div>

            <button
              onClick={runBuild}
              disabled={status === 'running'}
              style={{
                padding: '11px 0', background: status === 'running' ? '#ccc' : DARK,
                color: status === 'running' ? '#888' : GOLD,
                border: 'none', borderRadius: 8, fontWeight: 700, fontSize: '0.9rem',
                cursor: status === 'running' ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <Sparkles size={14} />
              {status === 'running' ? 'Building campaign… (this takes ~30–60s)' : 'Build Full Campaign →'}
            </button>
          </div>
        </div>

        {/* Result */}
        {status === 'done' && result && !result.error && (
          <div style={{ background: '#f0fdf0', border: '1px solid #bbf7d0', borderRadius: 10, padding: 16 }}>
            <div style={{ fontWeight: 800, color: '#2e7d32', fontSize: '0.875rem', marginBottom: 10 }}>
              ✅ Campaign built successfully
            </div>
            {result.flyer_image_url && (
              <div style={{ marginBottom: 12 }}>
                <img src={result.flyer_image_url} alt="Campaign flyer"
                     style={{ width: '100%', borderRadius: 8, border: `1px solid #bbf7d0` }} />
                <p style={{ margin: '4px 0 0', fontSize: '0.68rem', color: '#999' }}>
                  ↑ Flyer embedded in email sequence
                </p>
              </div>
            )}
            <div style={{ fontSize: '0.8rem', color: '#bbb', display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div>🎯 <strong>3 ad copy units</strong> generated</div>
              <div>📄 <strong>Sales letter</strong> saved as{' '}
                <code style={{ background: '#2a2a2a', padding: '1px 5px', borderRadius: 4, fontSize: '0.75rem' }}>
                  /campaign/{result.campaign_page_slug}
                </code>
              </div>
              <div>✉️ <strong>3-email follow-up sequence</strong> ready{result.flyer_image_url ? ' (with flyer image)' : ''}</div>
              <div style={{ marginTop: 6 }}>
                Everything is in{' '}
                <a href="/approvals" style={{ color: WARM, fontWeight: 700 }}>Approval Queue</a>{' '}
                — review and publish before going live.
              </div>
            </div>
          </div>
        )}
        {status === 'error' && result?.error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: 14, fontSize: '0.82rem', color: '#b91c1c' }}>
            ⚠ {result.error}
          </div>
        )}
      </div>

      {/* Right — campaign pages list */}
      <div>
        <div style={{ background: '#2a2a2a', border: `1px solid ${BORDER}`, borderRadius: 10, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, color: DARK }}>Campaign Pages</h3>
            <button onClick={loadPages} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTED, padding: 4 }}>
              <RefreshCw size={13} />
            </button>
          </div>
          {loadingPages ? (
            <div style={{ color: MUTED, fontSize: '0.82rem', textAlign: 'center', padding: '20px 0' }}>Loading…</div>
          ) : pages.length === 0 ? (
            <div style={{ color: MUTED, fontSize: '0.82rem', textAlign: 'center', padding: '20px 0', fontStyle: 'italic' }}>
              No campaign pages yet. Build your first one →
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {pages.map(p => (
                <div key={p.slug} style={{
                  border: `1px solid ${p.is_published ? '#bbf7d0' : BORDER}`,
                  borderRadius: 8, padding: '12px 14px',
                  background: p.is_published ? '#f0fdf0' : '#fafafa',
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: '0.82rem', color: DARK, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.headline || p.slug}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: MUTED }}>
                        {p.avatar?.replace(/_/g,' ')} · {p.product?.toUpperCase()} · {p.market}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: p.is_published ? '#2e7d32' : MUTED, marginTop: 3, fontWeight: p.is_published ? 700 : 400 }}>
                        {p.is_published ? '● Live' : '○ Draft'} · /campaign/{p.slug}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      {p.is_published && (
                        <a
                          href={`${window.location.origin.replace('5174','5173')}/campaign/${p.slug}`}
                          target="_blank" rel="noopener noreferrer"
                          style={{ padding: '4px 8px', background: '#e0f2fe', color: '#0369a1', borderRadius: 5, fontSize: '0.7rem', fontWeight: 600, textDecoration: 'none' }}
                        >
                          View ↗
                        </a>
                      )}
                      <button
                        onClick={() => togglePublish(p.slug)}
                        disabled={!!publishing[p.slug]}
                        style={{
                          padding: '4px 10px',
                          background: p.is_published ? '#fef2f2' : '#f0fdf0',
                          color: p.is_published ? '#b91c1c' : '#2e7d32',
                          border: `1px solid ${p.is_published ? '#fecaca' : '#bbf7d0'}`,
                          borderRadius: 5, fontSize: '0.7rem', fontWeight: 700,
                          cursor: publishing[p.slug] ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {publishing[p.slug] ? '…' : p.is_published ? 'Unpublish' : 'Publish'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media (max-width: 700px) {
          .campaign-builder-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}


// ── Library tab ───────────────────────────────────────────────────────────────

function LibraryTab({ newPost }) {
  const [posts, setPosts]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [statusFilter, setStatus] = useState('')
  const [platFilter, setPlat]   = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = []
      if (statusFilter) params.push(`status=${statusFilter}`)
      if (platFilter)   params.push(`platform=${platFilter}`)
      params.push('limit=60')
      const data = await api.get(`/content/posts?${params.join('&')}`)
      setPosts(data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [statusFilter, platFilter])

  useEffect(() => { load() }, [load])

  // Prepend newly generated post
  useEffect(() => {
    if (newPost) {
      setPosts(p => [newPost, ...p.filter(x => x.id !== newPost.id)])
    }
  }, [newPost])

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={statusFilter} onChange={e => setStatus(e.target.value)} style={{...inputSty, width: 140}}>
          <option value="">All statuses</option>
          {['pending','approved','needs_edit','rejected','scheduled','published'].map(s => (
            <option key={s} value={s}>{s.replace(/_/g,' ')}</option>
          ))}
        </select>
        <select value={platFilter} onChange={e => setPlat(e.target.value)} style={{...inputSty, width: 160}}>
          <option value="">All platforms</option>
          {PLATFORMS.map(p => <option key={p} value={p}>{p.replace(/_/g,' ')}</option>)}
        </select>
        <button onClick={load} style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
          borderRadius: 20, fontSize: '0.75rem', cursor: 'pointer',
          border: `1px solid ${BORDER}`, background: '#2a2a2a', color: MUTED,
        }}>
          <RefreshCw size={12} /> Refresh
        </button>
        <span style={{ fontSize: '0.75rem', color: MUTED, marginLeft: 4 }}>
          {posts.length} post{posts.length !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', color: MUTED, padding: 40 }}>Loading…</div>
      ) : posts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 24px', background: '#2a2a2a',
          borderRadius: 10, border: `1px solid ${BORDER}` }}>
          <Sparkles size={28} style={{ color: '#ddd', marginBottom: 10 }} />
          <p style={{ color: MUTED, margin: 0 }}>No posts yet. Go to Generate to create your first.</p>
        </div>
      ) : (
        posts.map(post => (
          <PostCard
            key={post.id}
            post={post}
            onUpdated={(updated) => setPosts(prev =>
              prev.map(p => p.id === updated.id ? updated : p)
            )}
          />
        ))
      )}
    </div>
  )
}


// ── Calendar tab ─────────────────────────────────────────────────────────────

const PLATFORM_COLORS = {
  tiktok:             '#69C9D0',
  instagram_reel:     '#E1306C',
  instagram_carousel: '#C13584',
  facebook:           '#1877F2',
  linkedin:           '#0A66C2',
  google_business:    '#4285F4',
  email_snippet:      '#6B7280',
}

function CalendarTab() {
  const [posts, setPosts]     = useState([])
  const [loading, setLoading] = useState(true)
  const [month, setMonth]     = useState(() => {
    const now = new Date(); return { year: now.getFullYear(), month: now.getMonth() }
  })
  const [preview, setPreview] = useState(null)
  const [scheduling, setScheduling] = useState(null) // post being rescheduled

  useEffect(() => {
    api.get('/content/posts?limit=200').then(setPosts).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const firstDay = new Date(month.year, month.month, 1)
  const daysInMonth = new Date(month.year, month.month + 1, 0).getDate()
  const startDow = firstDay.getDay() // 0=Sun

  const byDate = {}
  posts.forEach(p => {
    if (!p.scheduled_date) return
    const d = p.scheduled_date.slice(0, 10)
    if (!byDate[d]) byDate[d] = []
    byDate[d].push(p)
  })

  const unscheduled = posts.filter(p => !p.scheduled_date && p.approval_status !== 'published')

  const prevMonth = () => setMonth(m => {
    if (m.month === 0) return { year: m.year - 1, month: 11 }
    return { ...m, month: m.month - 1 }
  })
  const nextMonth = () => setMonth(m => {
    if (m.month === 11) return { year: m.year + 1, month: 0 }
    return { ...m, month: m.month + 1 }
  })

  const schedulePost = async (postId, date) => {
    try {
      await api.patch(`/content/posts/${postId}/approve`, {
        action: 'schedule',
        scheduled_date: new Date(date + 'T12:00:00').toISOString(),
      })
      const updated = await api.get('/content/posts?limit=200')
      setPosts(updated)
      setScheduling(null)
      toast && toast.success('Post scheduled')
    } catch (e) { console.error(e) }
  }

  const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']
  const today = new Date().toISOString().slice(0, 10)

  const cells = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div>
      {/* Month nav */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <button onClick={prevMonth} style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: MUTED }}>‹</button>
        <span style={{ fontWeight: 800, fontSize: '0.95rem', color: DARK }}>
          {MONTH_NAMES[month.month]} {month.year}
        </span>
        <button onClick={nextMonth} style={{ background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: MUTED }}>›</button>
      </div>

      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 2, marginBottom: 4 }}>
        {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
          <div key={d} style={{ textAlign: 'center', fontSize: '0.68rem', color: MUTED, fontWeight: 700, padding: '4px 0', letterSpacing: '0.05em' }}>{d}</div>
        ))}
      </div>

      {/* Calendar grid */}
      {loading ? (
        <div style={{ textAlign: 'center', color: MUTED, padding: 40 }}>Loading…</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 2 }}>
          {cells.map((day, idx) => {
            if (!day) return <div key={`empty-${idx}`} />
            const dateStr = `${month.year}-${String(month.month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`
            const dayPosts = byDate[dateStr] || []
            const isToday  = dateStr === today
            return (
              <div
                key={dateStr}
                onClick={() => scheduling && schedulePost(scheduling.id, dateStr)}
                style={{
                  minHeight: 70, padding: '4px 5px',
                  border: `1px solid ${isToday ? '#c8860a' : BORDER}`,
                  borderRadius: 6, background: scheduling ? '#fffbf2' : '#fff',
                  cursor: scheduling ? 'pointer' : 'default',
                  transition: 'background 0.12s',
                }}
                onMouseEnter={e => { if (scheduling) e.currentTarget.style.background = '#fef3c7' }}
                onMouseLeave={e => { if (scheduling) e.currentTarget.style.background = '#fffbf2' }}
              >
                <div style={{
                  fontSize: '0.72rem', fontWeight: isToday ? 800 : 500,
                  color: isToday ? '#c8860a' : '#888', marginBottom: 3,
                }}>{day}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {dayPosts.slice(0, 3).map(p => (
                    <div
                      key={p.id}
                      onClick={e => { e.stopPropagation(); setPreview(p) }}
                      style={{
                        fontSize: '0.65rem', fontWeight: 600,
                        padding: '2px 5px', borderRadius: 4,
                        background: PLATFORM_COLORS[p.platform] || GOLD,
                        color: '#fff', cursor: 'pointer',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        opacity: p.approval_status === 'published' ? 0.5 : 1,
                      }}
                    >
                      {p.platform?.replace(/_/g,' ')}
                    </div>
                  ))}
                  {dayPosts.length > 3 && (
                    <div style={{ fontSize: '0.6rem', color: MUTED }}>+{dayPosts.length - 3} more</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Unscheduled queue */}
      {unscheduled.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h4 style={{ margin: '0 0 10px', fontSize: '0.8rem', fontWeight: 700, color: MUTED }}>
            UNSCHEDULED ({unscheduled.length}) — click a post, then click a date to schedule
          </h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {unscheduled.slice(0, 12).map(p => (
              <div
                key={p.id}
                onClick={() => setScheduling(scheduling?.id === p.id ? null : p)}
                style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: '0.72rem', fontWeight: 600,
                  background: scheduling?.id === p.id ? DARK : '#f5f5f5',
                  color: scheduling?.id === p.id ? GOLD : '#555',
                  border: `1px solid ${scheduling?.id === p.id ? DARK : BORDER}`,
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                {p.platform?.replace(/_/g,' ')} · {p.category?.replace(/_/g,' ')}
              </div>
            ))}
          </div>
          {scheduling && (
            <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: '#c8860a' }}>
              ← Now click a date on the calendar to schedule "{scheduling.platform?.replace(/_/g,' ')}"
            </p>
          )}
        </div>
      )}

      {/* Preview modal */}
      {preview && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setPreview(null)}
        >
          <div
            style={{ background: '#2a2a2a', borderRadius: 12, padding: 24, maxWidth: 480, width: '90%', boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: PLATFORM_COLORS[preview.platform] || GOLD }} />
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: DARK }}>{preview.platform?.replace(/_/g,' ')}</span>
                <StatusBadge status={preview.approval_status} />
              </div>
              <button onClick={() => setPreview(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTED, fontSize: '1.1rem' }}>×</button>
            </div>
            {preview.hook && <p style={{ margin: '0 0 8px', fontWeight: 700, fontSize: '0.9rem', color: DARK }}>{preview.hook}</p>}
            {preview.caption && <p style={{ margin: '0 0 8px', fontSize: '0.82rem', color: '#999', lineHeight: 1.6 }}>{preview.caption}</p>}
            {preview.cta && <p style={{ margin: '0 0 8px', fontSize: '0.78rem', color: '#c8860a', fontWeight: 600 }}>CTA: {preview.cta}</p>}
            {preview.scheduled_date && <p style={{ margin: 0, fontSize: '0.72rem', color: MUTED }}>Scheduled: {new Date(preview.scheduled_date).toLocaleDateString()}</p>}
            <StageBadge stage={preview.pipeline_stage} />
          </div>
        </div>
      )}
    </div>
  )
}


// ── Flyer Builder ─────────────────────────────────────────────────────────────

const USE_CASES = [
  { value: 'purchase',  label: 'Home Purchase' },
  { value: 'dpa',       label: 'Down Payment Assist' },
  { value: 'refi',      label: 'Refinance' },
  { value: 'realtor',   label: 'Realtor Partner' },
  { value: 'generic',   label: 'Generic / Brand' },
]

const FLYER_FORMATS = [
  { value: 'social_square',   label: 'Social Square (1080×1080)' },
  { value: 'facebook_banner', label: 'Facebook Banner (1200×628)' },
  { value: 'story',           label: 'Story (1080×1920)' },
  { value: 'wide_banner',     label: 'Wide Banner (1500×500)' },
]

const STYLE_KEYS = [
  { value: 'suit_headshot',   label: 'Professional Suit' },
  { value: 'casual_expert',   label: 'Casual Expert' },
  { value: 'outdoor_realtor', label: 'Outdoor / Home' },
  { value: 'dark_brand',      label: 'Dark Brand' },
  { value: 'community',       label: 'Community / Neighborhood' },
]

function FlyerBuilderTab() {
  const [refPhoto, setRefPhoto]         = useState(null)   // { uploaded, file_url }
  const [uploading, setUploading]       = useState(false)
  const [form, setForm]                 = useState({
    use_case: 'purchase',
    flyer_format: 'social_square',
    headline: 'Get Pre-Approved Today',
    subheadline: 'Same-day results. No pressure.',
    cta_text: 'Book a Free Call →',
    style_preset: 'suit_headshot',
    skip_ai: false,
  })
  const [generating, setGenerating]     = useState(false)
  const [pollId, setPollId]             = useState(null)
  const [activeFlyer, setActiveFlyer]   = useState(null)   // currently generating / last result
  const [flyers, setFlyers]             = useState([])
  const [flyersLoading, setFlyersLoading] = useState(true)
  const [error, setError]               = useState(null)
  const [lightbox, setLightbox]         = useState(null)
  const pollRef                         = useRef(null)
  const fileRef                         = useRef(null)

  // Load reference photo + flyer gallery on mount
  useEffect(() => {
    api.get('/flyers/reference-photo').then(r => setRefPhoto(r)).catch(() => {})
    loadFlyers()
  }, [])

  async function loadFlyers() {
    setFlyersLoading(true)
    try {
      const r = await api.get('/flyers/?limit=20')
      setFlyers(r.flyers || [])
    } catch {}
    setFlyersLoading(false)
  }

  // Poll for flyer completion
  useEffect(() => {
    if (!pollId) return
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.get(`/flyers/${pollId}`)
        setActiveFlyer(r)
        if (r.status === 'complete' || r.status === 'failed') {
          clearInterval(pollRef.current)
          setGenerating(false)
          setPollId(null)
          loadFlyers()
        }
      } catch {}
    }, 3000)
    return () => clearInterval(pollRef.current)
  }, [pollId])

  async function handlePhotoUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await api.upload('/flyers/reference-photo', fd)
      setRefPhoto({ uploaded: true, file_url: r.file_url })
    } catch (err) {
      setError(err.message || 'Upload failed')
    }
    setUploading(false)
    e.target.value = ''
  }

  async function handleGenerate() {
    if (!refPhoto?.uploaded) { setError('Upload a reference photo first.'); return }
    setGenerating(true)
    setActiveFlyer(null)
    setError(null)
    try {
      const r = await api.post('/flyers/generate', form)
      setPollId(r.flyer_id)
      setActiveFlyer({ id: r.flyer_id, status: 'pending' })
    } catch (err) {
      setError(err.message || 'Generation failed')
      setGenerating(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this flyer?')) return
    try {
      await api.delete(`/flyers/${id}`)
      setFlyers(prev => prev.filter(f => f.id !== id))
      if (activeFlyer?.id === id) setActiveFlyer(null)
    } catch (err) {
      setError(err.message || 'Delete failed')
    }
  }

  const card = {
    background: '#2a2a2a', border: `1px solid ${BORDER}`,
    borderRadius: 10, padding: '16px 18px', marginBottom: 14,
  }

  const statusColor = s => ({ complete: '#16a34a', failed: '#dc2626', pending: WARM, avatar_ready: '#2563eb' })[s] || MUTED

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, alignItems: 'start' }}>

      {/* ── Left panel: controls ── */}
      <div>
        {/* Reference photo */}
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontWeight: 800, fontSize: '0.85rem', color: DARK }}>Your Face Photo</span>
            {refPhoto?.uploaded && (
              <span style={{ fontSize: '0.7rem', color: '#16a34a', fontWeight: 700 }}>✓ Uploaded</span>
            )}
          </div>

          {refPhoto?.uploaded && refPhoto.file_url ? (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 10 }}>
              <img
                src={refPhoto.file_url}
                alt="reference"
                style={{ width: 64, height: 64, borderRadius: 8, objectFit: 'cover', border: `2px solid ${BORDER}` }}
              />
              <div>
                <p style={{ margin: 0, fontSize: '0.75rem', color: MUTED }}>
                  This photo anchors your face in every generated avatar.
                </p>
              </div>
            </div>
          ) : (
            <p style={{ margin: '0 0 10px', fontSize: '0.75rem', color: MUTED }}>
              Upload a clear, frontal face photo. Used to put your face on AI-generated avatars.
            </p>
          )}

          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }} onChange={handlePhotoUpload} />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '8px 12px', borderRadius: 7, border: `1.5px dashed ${BORDER}`,
              background: uploading ? '#f9f9f9' : '#fffbf5', cursor: uploading ? 'default' : 'pointer',
              fontSize: '0.8rem', color: WARM, fontWeight: 700, justifyContent: 'center',
            }}
          >
            {uploading ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Upload size={14} />}
            {refPhoto?.uploaded ? 'Replace Photo' : 'Upload Photo'}
          </button>
        </div>

        {/* Generation form */}
        <div style={card}>
          <p style={{ margin: '0 0 14px', fontWeight: 800, fontSize: '0.85rem', color: DARK }}>Flyer Settings</p>

          <label style={labelSty}>Use Case</label>
          <select style={{ ...inputSty, marginBottom: 10 }} value={form.use_case} onChange={e => setForm(p => ({ ...p, use_case: e.target.value }))}>
            {USE_CASES.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
          </select>

          <label style={labelSty}>Format</label>
          <select style={{ ...inputSty, marginBottom: 10 }} value={form.flyer_format} onChange={e => setForm(p => ({ ...p, flyer_format: e.target.value }))}>
            {FLYER_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>

          <label style={labelSty}>Avatar Style</label>
          <select style={{ ...inputSty, marginBottom: 10 }} value={form.style_preset} onChange={e => setForm(p => ({ ...p, style_preset: e.target.value }))}>
            {STYLE_KEYS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>

          <label style={labelSty}>Headline</label>
          <input style={{ ...inputSty, marginBottom: 10 }} value={form.headline} onChange={e => setForm(p => ({ ...p, headline: e.target.value }))} placeholder="Get Pre-Approved Today" />

          <label style={labelSty}>Subheadline</label>
          <input style={{ ...inputSty, marginBottom: 10 }} value={form.subheadline} onChange={e => setForm(p => ({ ...p, subheadline: e.target.value }))} placeholder="Same-day results. No pressure." />

          <label style={labelSty}>CTA Button Text</label>
          <input style={{ ...inputSty, marginBottom: 14 }} value={form.cta_text} onChange={e => setForm(p => ({ ...p, cta_text: e.target.value }))} placeholder="Book a Free Call →" />

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.78rem', color: MUTED, cursor: 'pointer', marginBottom: 14 }}>
            <input type="checkbox" checked={form.skip_ai} onChange={e => setForm(p => ({ ...p, skip_ai: e.target.checked }))} />
            Skip AI avatar (use photo directly — faster, no credits)
          </label>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 7, padding: '8px 12px', marginBottom: 12, fontSize: '0.78rem', color: '#dc2626', display: 'flex', gap: 6, alignItems: 'flex-start' }}>
              <AlertCircle size={13} style={{ marginTop: 1, flexShrink: 0 }} /> {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating || !refPhoto?.uploaded}
            style={{
              width: '100%', padding: '10px 0', borderRadius: 8, border: 'none',
              background: generating || !refPhoto?.uploaded ? '#ddd' : WARM,
              color: generating || !refPhoto?.uploaded ? MUTED : '#fff',
              fontWeight: 800, fontSize: '0.85rem', cursor: generating || !refPhoto?.uploaded ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
          >
            {generating
              ? <><Loader size={15} style={{ animation: 'spin 1s linear infinite' }} /> Generating…</>
              : <><Sparkles size={15} /> Generate Flyer</>
            }
          </button>
        </div>
      </div>

      {/* ── Right panel: result + gallery ── */}
      <div>
        {/* Active job status */}
        {activeFlyer && (
          <div style={{ ...card, borderLeft: `4px solid ${statusColor(activeFlyer.status)}`, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 800, fontSize: '0.85rem', color: DARK }}>
                {activeFlyer.status === 'pending' && '⏳ Generating avatar…'}
                {activeFlyer.status === 'avatar_ready' && '🎨 Compositing flyer…'}
                {activeFlyer.status === 'complete' && '✅ Flyer ready!'}
                {activeFlyer.status === 'failed' && '❌ Generation failed'}
              </span>
              <span style={{ fontSize: '0.72rem', color: statusColor(activeFlyer.status), fontWeight: 700, textTransform: 'uppercase' }}>
                {activeFlyer.status}
              </span>
            </div>

            {(activeFlyer.status === 'pending' || activeFlyer.status === 'avatar_ready') && (
              <p style={{ margin: '6px 0 0', fontSize: '0.75rem', color: MUTED }}>
                {activeFlyer.status === 'pending' ? 'AI is generating your avatar (20–90 sec)…' : 'Avatar ready. Building branded flyer…'}
              </p>
            )}

            {activeFlyer.status === 'complete' && activeFlyer.flyer_image_url && (
              <div style={{ marginTop: 12 }}>
                <img
                  src={activeFlyer.flyer_image_url}
                  alt="Generated flyer"
                  style={{ width: '100%', maxHeight: 420, objectFit: 'contain', borderRadius: 8, border: `1px solid ${BORDER}`, cursor: 'zoom-in', background: '#252525' }}
                  onClick={() => setLightbox(activeFlyer.flyer_image_url)}
                />
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <a
                    href={activeFlyer.flyer_image_url}
                    download
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5, padding: '7px 14px',
                      background: WARM, color: '#fff', borderRadius: 7, textDecoration: 'none',
                      fontSize: '0.78rem', fontWeight: 700,
                    }}
                  >
                    <Download size={13} /> Download
                  </a>
                  {activeFlyer.avatar_image_url && (
                    <a
                      href={activeFlyer.avatar_image_url}
                      download
                      style={{
                        display: 'flex', alignItems: 'center', gap: 5, padding: '7px 14px',
                        background: '#2a2a2a', color: DARK, border: `1px solid ${BORDER}`, borderRadius: 7,
                        textDecoration: 'none', fontSize: '0.78rem', fontWeight: 700,
                      }}
                    >
                      <Download size={13} /> Avatar only
                    </a>
                  )}
                </div>
                {activeFlyer.provider && (
                  <p style={{ margin: '8px 0 0', fontSize: '0.7rem', color: MUTED }}>
                    Generated by: <strong>{activeFlyer.provider}</strong>
                  </p>
                )}
              </div>
            )}

            {activeFlyer.status === 'failed' && (
              <p style={{ margin: '6px 0 0', fontSize: '0.75rem', color: '#dc2626' }}>
                {activeFlyer.error || 'Unknown error. Check server logs.'}
              </p>
            )}
          </div>
        )}

        {/* Gallery */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontWeight: 800, fontSize: '0.85rem', color: DARK }}>Generated Flyers</span>
          <button onClick={loadFlyers} style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTED }}>
            <RefreshCw size={14} />
          </button>
        </div>

        {flyersLoading ? (
          <p style={{ color: MUTED, fontSize: '0.8rem' }}>Loading…</p>
        ) : flyers.length === 0 ? (
          <div style={{ ...card, textAlign: 'center', padding: '32px 20px' }}>
            <ImageIcon size={32} color={BORDER} style={{ marginBottom: 10 }} />
            <p style={{ margin: 0, color: MUTED, fontSize: '0.82rem' }}>No flyers yet. Generate one above!</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
            {flyers.map(f => (
              <div
                key={f.id}
                style={{
                  background: '#2a2a2a', border: `1px solid ${BORDER}`, borderRadius: 9,
                  overflow: 'hidden', position: 'relative',
                  opacity: f.status === 'failed' ? 0.55 : 1,
                }}
              >
                {/* Thumbnail */}
                {f.flyer_image_url ? (
                  <div
                    style={{ cursor: 'zoom-in', background: '#252525' }}
                    onClick={() => setLightbox(f.flyer_image_url)}
                  >
                    <img
                      src={f.flyer_image_url}
                      alt={f.headline}
                      style={{ width: '100%', height: 130, objectFit: 'cover', display: 'block' }}
                    />
                  </div>
                ) : (
                  <div style={{
                    height: 130, background: '#f5f5f0', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6,
                  }}>
                    {f.status === 'pending' || f.status === 'avatar_ready'
                      ? <Loader size={22} color={WARM} style={{ animation: 'spin 1s linear infinite' }} />
                      : <ImageIcon size={22} color={BORDER} />
                    }
                    <span style={{ fontSize: '0.65rem', color: MUTED, textTransform: 'uppercase' }}>{f.status}</span>
                  </div>
                )}

                {/* Info */}
                <div style={{ padding: '8px 10px' }}>
                  <p style={{ margin: '0 0 2px', fontSize: '0.72rem', fontWeight: 700, color: DARK,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.headline}
                  </p>
                  <p style={{ margin: 0, fontSize: '0.65rem', color: MUTED }}>
                    {f.flyer_format?.replace('_', ' ')} · {f.use_case}
                  </p>

                  <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                    {f.flyer_image_url && (
                      <a
                        href={f.flyer_image_url}
                        download
                        title="Download"
                        style={{ color: WARM, display: 'flex', alignItems: 'center' }}
                        onClick={e => e.stopPropagation()}
                      >
                        <Download size={13} />
                      </a>
                    )}
                    {f.flyer_image_url && (
                      <button
                        title="Preview"
                        onClick={() => setLightbox(f.flyer_image_url)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: MUTED, padding: 0 }}
                      >
                        <Eye size={13} />
                      </button>
                    )}
                    <button
                      title="Delete"
                      onClick={() => handleDelete(f.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', padding: 0, marginLeft: 'auto' }}
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

      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.82)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, cursor: 'zoom-out',
          }}
        >
          <img
            src={lightbox}
            alt="Flyer preview"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 10, objectFit: 'contain' }}
            onClick={e => e.stopPropagation()}
          />
          <button
            onClick={() => setLightbox(null)}
            style={{
              position: 'absolute', top: 20, right: 24, background: 'none', border: 'none',
              cursor: 'pointer', color: '#fff',
            }}
          >
            <X size={28} />
          </button>
        </div>
      )}

      {/* Spinner keyframe */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}


// ── Main page ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'campaigns',   label: 'Ad Campaigns', icon: TrendingUp  },
  { id: 'generate',    label: 'Generate',     icon: Sparkles    },
  { id: 'flyers',      label: 'Flyers',       icon: ImageIcon   },
  { id: 'library',     label: 'Library',      icon: BarChart3   },
  { id: 'calendar',    label: 'Calendar',     icon: Globe       },
  { id: 'templates',   label: 'Templates',    icon: Settings2   },
  { id: 'performance', label: 'Performance',  icon: TrendingUp  },
]

export default function ContentStudio() {
  const [tab, setTab]         = useState('campaigns')
  const [latestPost, setLatestPost] = useState(null)

  const handleGenerated = (post) => {
    setLatestPost(post)
    setTab('library')
  }

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 900, color: DARK }}>Content Studio</h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: MUTED }}>
            Ad campaigns · Social content · Voice · Video · Publish. All in one place.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20,
        borderBottom: `1px solid ${BORDER}`, paddingBottom: 0, flexWrap: 'wrap' }}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 14px', background: 'none', border: 'none', cursor: 'pointer',
              fontSize: '0.82rem', fontWeight: tab === id ? 800 : 500,
              color: tab === id ? (id === 'campaigns' ? WARM : DARK) : MUTED,
              borderBottom: tab === id ? `2px solid ${id === 'campaigns' ? WARM : DARK}` : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            <Icon size={13} />
            {label}
            {id === 'campaigns' && (
              <span style={{ background: GOLD, color: DARK, fontSize: '0.6rem', fontWeight: 900, padding: '1px 5px', borderRadius: 99, marginLeft: 2 }}>
                NEW
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'campaigns'   && <CampaignBuilderTab />}
      {tab === 'generate'    && <GenerateTab onGenerated={handleGenerated} />}
      {tab === 'flyers'      && <FlyerBuilderTab />}
      {tab === 'library'     && <LibraryTab newPost={latestPost} />}
      {tab === 'calendar'    && <CalendarTab />}
      {tab === 'templates'   && <TemplatesTab />}
      {tab === 'performance' && <PerformanceTab />}
    </div>
  )
}

const labelSty = {
  display: 'block', fontSize: '0.68rem', color: MUTED,
  marginBottom: 5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
}
const inputSty = {
  width: '100%', padding: '7px 10px', border: `1px solid ${BORDER}`,
  borderRadius: 6, fontSize: '0.82rem', background: '#2a2a2a', outline: 'none', boxSizing: 'border-box',
}

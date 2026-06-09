import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import { Plus, Megaphone, Zap, Mail, MessageSquare, Phone, ChevronRight,
         RefreshCw, Pencil, Check, X, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

const STATUS_BADGE = {
  draft:     'badge-gray',
  active:    'badge-green',
  paused:    'badge-warm',
  completed: 'badge-blue',
  archived:  'badge-gray',
}
const CHANNEL_ICON = { email: Mail, sms: MessageSquare, call_task: Phone }
const TYPES  = ['realtor_partnership','title_refi','dpa_buyer','dscr_investor','heloc_homeowner','open_house_qr','social_content','past_lead_nurture']
const GOALS  = ['book_call','drive_ai_intake','promote_dpa','promote_dscr','promote_heloc','promote_refi','recruit_realtor','open_house_tool']
const CHANNELS = ['email','sms','linkedin','instagram','tiktok','facebook','google_business','manual']

const lbl = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '5px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px' }

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [selected, setSelected]   = useState(null)
  const [detail, setDetail]       = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [products, setProducts]   = useState([])
  const [form, setForm]           = useState({
    name: '', campaign_type: 'dpa_buyer', goal: 'book_call',
    channel: 'email', sequence_length: 3, follow_up_days: 3, requires_approval: true,
  })

  const load = useCallback(async () => {
    const [c, p] = await Promise.allSettled([api.get('/campaigns/'), api.get('/products/')])
    if (c.status === 'fulfilled') setCampaigns(c.value)
    if (p.status === 'fulfilled') setProducts(p.value)
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const openDetail = useCallback(async (campaign) => {
    setSelected(campaign)
    setDetailLoading(true)
    setDetail(null)
    try {
      const d = await api.get(`/campaigns/${campaign.id}`)
      setDetail(d)
    } catch (e) { toast.error('Could not load campaign') }
    finally { setDetailLoading(false) }
  }, [])

  const save = async () => {
    try {
      const c = await api.post('/campaigns/', form)
      toast.success('Campaign created')
      setShowForm(false)
      load()
      openDetail(c)
    } catch (e) { toast.error(e.message) }
  }

  const generateSteps = async (campaignId, overwrite = false) => {
    try {
      toast.loading('Generating steps with AI…', { id: 'gen-steps' })
      const r = await api.post(`/campaigns/${campaignId}/generate-steps`, { overwrite })
      toast.success(`${r.created || 0} steps generated`, { id: 'gen-steps' })
      const updated = await api.get(`/campaigns/${campaignId}`)
      setDetail(updated)
    } catch (e) { toast.error(e.message, { id: 'gen-steps' }) }
  }

  const setStatus = async (campaignId, status) => {
    try {
      await api.patch(`/campaigns/${campaignId}/status?status=${status}`)
      load()
      if (selected?.id === campaignId) setSelected(s => ({ ...s, status }))
    } catch (e) { toast.error(e.message) }
  }

  return (
    <div className="fade-in" style={{ display: 'flex', gap: '20px', height: '100%' }}>

      {/* ── Left: campaign list ──────────────────────────────────────────── */}
      <div style={{ width: '320px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: '0 0 3px', fontSize: '1.15rem', fontWeight: 700 }}>Campaigns</h1>
            <p style={{ margin: 0, color: '#666', fontSize: '0.8rem' }}>{campaigns.length} sequences</p>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm(s => !s)}>
            <Plus size={12} /> New
          </button>
        </div>

        {showForm && (
          <div className="card fade-in" style={{ padding: '14px' }}>
            <h3 style={{ margin: '0 0 14px', fontSize: '0.85rem', fontWeight: 700 }}>New Campaign</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <label style={lbl}>Name</label>
                <input className="input" placeholder="Q3 DPA Buyer" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <Sel label="Type"    value={form.campaign_type} options={TYPES}    onChange={v => setForm(f => ({ ...f, campaign_type: v }))} />
                <Sel label="Goal"    value={form.goal}          options={GOALS}    onChange={v => setForm(f => ({ ...f, goal: v }))} />
                <Sel label="Channel" value={form.channel}       options={CHANNELS} onChange={v => setForm(f => ({ ...f, channel: v }))} />
                <div>
                  <label style={lbl}>Steps</label>
                  <input className="input" type="number" min={1} max={10} value={form.sequence_length}
                    onChange={e => setForm(f => ({ ...f, sequence_length: +e.target.value }))} />
                </div>
                <div>
                  <label style={lbl}>Follow-up Days</label>
                  <input className="input" type="number" min={1} max={30} value={form.follow_up_days}
                    onChange={e => setForm(f => ({ ...f, follow_up_days: +e.target.value }))} />
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '7px', cursor: 'pointer', fontSize: '0.8rem', color: '#ccc' }}>
                <input type="checkbox" className="checkbox-warm" checked={form.requires_approval}
                  onChange={e => setForm(f => ({ ...f, requires_approval: e.target.checked }))} />
                Require approval before sending
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary btn-sm" onClick={save}>Create</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', overflowY: 'auto', flex: 1 }}>
          {loading ? <p style={{ color: '#555', fontSize: '0.8rem' }}>Loading…</p>
          : campaigns.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '32px 16px' }}>
              <Megaphone size={24} color="#555" style={{ marginBottom: '8px' }} />
              <p style={{ color: '#888', fontSize: '0.8rem', margin: 0 }}>No campaigns yet</p>
            </div>
          ) : campaigns.map(c => (
            <div
              key={c.id}
              className="card card-sm"
              onClick={() => openDetail(c)}
              style={{
                cursor: 'pointer',
                borderColor: selected?.id === c.id ? 'var(--color-warm)' : undefined,
                borderWidth: selected?.id === c.id ? '1px' : undefined,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`badge ${STATUS_BADGE[c.status] || 'badge-gray'}`} style={{ fontSize: '0.65rem' }}>{c.status}</span>
                <span style={{ flex: 1, fontWeight: 600, fontSize: '0.82rem', color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.name}
                </span>
                <ChevronRight size={12} color="#555" />
              </div>
              <div style={{ display: 'flex', gap: '6px', marginTop: '5px' }}>
                <span className="badge badge-gray" style={{ fontSize: '0.65rem' }}>{c.channel}</span>
                <span className="badge badge-gray" style={{ fontSize: '0.65rem' }}>{c.campaign_type?.replace(/_/g,' ')}</span>
                <span style={{ fontSize: '0.65rem', color: '#555' }}>{c.contact_count} contacts</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: sequence builder ──────────────────────────────────────── */}
      {!selected && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444' }}>
          <div style={{ textAlign: 'center' }}>
            <Megaphone size={32} color="#333" style={{ marginBottom: '10px' }} />
            <p style={{ margin: 0, fontSize: '0.875rem' }}>Select a campaign to view its sequence</p>
          </div>
        </div>
      )}

      {selected && (
        <div className="fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>
          {/* Campaign header */}
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h2 style={{ margin: '0 0 4px', fontSize: '1.05rem', fontWeight: 700 }}>{selected.name}</h2>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  <span className={`badge ${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
                  <span className="badge badge-gray">{selected.campaign_type?.replace(/_/g,' ')}</span>
                  <span className="badge badge-gray">{selected.channel}</span>
                  <span className="badge badge-gray">{selected.goal?.replace(/_/g,' ')}</span>
                  {selected.requires_approval && <span style={{ fontSize: '0.65rem', color: '#f5c87a' }}>🔒 approval</span>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '7px' }}>
                {selected.status === 'draft'  && <button className="btn btn-primary btn-sm" onClick={() => setStatus(selected.id, 'active')}>Activate</button>}
                {selected.status === 'active' && <button className="btn btn-ghost btn-sm" onClick={() => setStatus(selected.id, 'paused')}>Pause</button>}
                {selected.status === 'paused' && <button className="btn btn-primary btn-sm" onClick={() => setStatus(selected.id, 'active')}>Resume</button>}
                <button className="btn btn-ghost btn-sm" onClick={() => { setSelected(null); setDetail(null) }}>✕</button>
              </div>
            </div>
          </div>

          {/* Steps section */}
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>
                Sequence Steps {detail ? `(${detail.steps?.length || 0})` : ''}
              </h3>
              <div style={{ display: 'flex', gap: '7px' }}>
                {detail?.steps?.length === 0 && (
                  <button className="btn btn-primary btn-sm" onClick={() => generateSteps(selected.id)}>
                    <Zap size={11} /> Generate with AI
                  </button>
                )}
                {detail?.steps?.length > 0 && (
                  <button className="btn btn-ghost btn-sm" onClick={() => generateSteps(selected.id, true)}>
                    <RefreshCw size={11} /> Regenerate
                  </button>
                )}
              </div>
            </div>

            {detailLoading && <div style={{ color: '#555', fontSize: '0.8rem', padding: '20px 0' }}>Loading steps…</div>}

            {detail && !detailLoading && (
              detail.steps.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px', color: '#555', fontSize: '0.8rem' }}>
                  <Zap size={22} color="#333" style={{ marginBottom: '8px' }} />
                  <p style={{ margin: 0 }}>No steps yet. Click "Generate with AI" to create the sequence.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                  {detail.steps.map((step, idx) => (
                    <StepCard
                      key={step.id}
                      step={step}
                      campaignId={selected.id}
                      isLast={idx === detail.steps.length - 1}
                      onUpdated={(updated) => {
                        setDetail(d => ({
                          ...d,
                          steps: d.steps.map(s => s.id === updated.id ? updated : s),
                        }))
                      }}
                    />
                  ))}
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Step card with inline template editing ────────────────────────────────────
function StepCard({ step, campaignId, isLast, onUpdated }) {
  const [editing, setEditing]   = useState(false)
  const [saving, setSaving]     = useState(false)
  const [draft, setDraft]       = useState({
    subject: step.template?.subject || '',
    body:    step.template?.body    || '',
    cta:     step.template?.cta     || '',
  })

  const ChanIcon = CHANNEL_ICON[step.channel] || Mail

  const save = async () => {
    setSaving(true)
    try {
      await api.patch(`/campaigns/${campaignId}/steps/${step.id}/template`, draft)
      onUpdated({ ...step, template: { ...step.template, ...draft } })
      setEditing(false)
      toast.success('Step saved')
    } catch (e) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const cancel = () => {
    setDraft({ subject: step.template?.subject || '', body: step.template?.body || '', cta: step.template?.cta || '' })
    setEditing(false)
  }

  return (
    <div style={{ display: 'flex', gap: '0' }}>
      {/* Timeline spine */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '32px', flexShrink: 0 }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: step.is_approved ? '#14532d22' : '#2a2a2a',
          border: `2px solid ${step.is_approved ? '#4ade80' : '#3a3a3a'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: step.is_approved ? '#4ade80' : '#666', fontSize: '0.72rem', fontWeight: 800,
        }}>
          {step.is_approved ? <CheckCircle size={13} /> : step.step_order}
        </div>
        {!isLast && <div style={{ flex: 1, width: 2, background: '#2a2a2a', minHeight: 24 }} />}
      </div>

      {/* Step content */}
      <div style={{
        flex: 1, marginLeft: 12, marginBottom: 14,
        background: 'var(--color-carbon-mid)', borderRadius: 8, padding: '12px 14px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            <ChanIcon size={13} color="var(--color-warm)" />
            <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#ddd' }}>{step.name}</span>
            {step.delay_days > 0 && (
              <span style={{ fontSize: '0.68rem', color: '#555' }}>Day {step.delay_days}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#555', padding: '2px' }}
              >
                <Pencil size={12} />
              </button>
            )}
            {editing && (
              <>
                <button onClick={save} disabled={saving} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4ade80', padding: '2px' }}>
                  <Check size={13} />
                </button>
                <button onClick={cancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', padding: '2px' }}>
                  <X size={13} />
                </button>
              </>
            )}
          </div>
        </div>

        {step.template ? (
          editing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {step.channel === 'email' && (
                <div>
                  <label style={{ fontSize: '0.65rem', color: '#666', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '3px' }}>Subject</label>
                  <input
                    className="input"
                    value={draft.subject}
                    onChange={e => setDraft(d => ({ ...d, subject: e.target.value }))}
                    style={{ fontSize: '0.82rem' }}
                  />
                </div>
              )}
              <div>
                <label style={{ fontSize: '0.65rem', color: '#666', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '3px' }}>Message Body</label>
                <textarea
                  className="input"
                  rows={5}
                  value={draft.body}
                  onChange={e => setDraft(d => ({ ...d, body: e.target.value }))}
                  style={{ resize: 'vertical', fontSize: '0.8rem' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.65rem', color: '#666', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '3px' }}>CTA</label>
                <input
                  className="input"
                  value={draft.cta}
                  onChange={e => setDraft(d => ({ ...d, cta: e.target.value }))}
                  placeholder="e.g. Book your free consultation →"
                  style={{ fontSize: '0.82rem' }}
                />
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {step.template.subject && (
                <div style={{ fontSize: '0.78rem', color: '#aaa', fontWeight: 600 }}>
                  📧 {step.template.subject}
                </div>
              )}
              {step.template.body && (
                <p style={{ margin: 0, fontSize: '0.78rem', color: '#888', lineHeight: 1.5,
                  maxHeight: '3.9em', overflow: 'hidden', display: '-webkit-box',
                  WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                  {step.template.body}
                </p>
              )}
              {step.template.cta && (
                <div style={{ fontSize: '0.72rem', color: '#c8860a', fontStyle: 'italic' }}>
                  → {step.template.cta}
                </div>
              )}
              {!step.template.body && (
                <p style={{ margin: 0, fontSize: '0.78rem', color: '#555', fontStyle: 'italic' }}>No content yet. Click ✏ to edit.</p>
              )}
            </div>
          )
        ) : (
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#555' }}>No template — regenerate steps.</p>
        )}
      </div>
    </div>
  )
}

function Sel({ label, value, options, onChange }) {
  return (
    <div>
      <label style={lbl}>{label}</label>
      <select className="select" value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{o.replace(/_/g,' ')}</option>)}
      </select>
    </div>
  )
}

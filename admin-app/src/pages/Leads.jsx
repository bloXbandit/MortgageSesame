import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'
import {
  Bell, Phone, Mail, MapPin, Clock, DollarSign, CreditCard,
  Home, User, CheckCircle, XCircle, AlertCircle, MessageSquare,
  ExternalLink, Plus, ChevronRight, Filter, X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { CALCOM } from '../config'

const SCORE_BADGE = {
  hot:             { bg: '#dcfce7', color: '#15803d', dot: '#4ade80' },
  warm:            { bg: '#fefce8', color: '#92400e', dot: '#f5c87a' },
  long_term:       { bg: '#eff6ff', color: '#1e40af', dot: '#60a5fa' },
  bad_fit:         { bg: '#f3f4f6', color: '#4b5563', dot: '#9ca3af' },
  compliance_risk: { bg: '#fef2f2', color: '#b91c1c', dot: '#f87171' },
  unscored:        { bg: '#1e1e1e', color: '#666',    dot: '#444'    },
}

const FILTER_LABELS = ['all', 'hot', 'warm', 'long_term', 'bad_fit']

const PIPELINE_STATUS_OPTS = [
  { value: 'new',              label: 'New',              color: '#6b7280' },
  { value: 'contacted',        label: 'Contacted',        color: '#3b82f6' },
  { value: 'appointment_set',  label: 'Appointment Set',  color: '#f5c87a' },
  { value: 'pre_approved',     label: 'Pre-Approved',     color: '#22c55e' },
  { value: 'closed',           label: 'Closed ✓',         color: '#16a34a' },
  { value: 'lost',             label: 'Lost',             color: '#ef4444' },
]

const LOAN_TYPE_OPTS = [
  { value: 'purchase',       label: '🏠 Buy a Home' },
  { value: 'dpa',            label: '💰 Down Payment Assistance' },
  { value: 'dscr_investor',  label: '📈 DSCR Investor Loan' },
  { value: 'heloc',          label: '🔑 HELOC / Cash-Out' },
  { value: 'refinance',      label: '🔄 Refinance' },
  { value: 'realtor',        label: '🤝 Realtor Partnership' },
]
const CREDIT_OPTS = [
  { value: 'below_580', label: 'Below 580' },
  { value: '580_619',   label: '580–619' },
  { value: '620_659',   label: '620–659' },
  { value: '660_699',   label: '660–699' },
  { value: '700_739',   label: '700–739' },
  { value: '740_plus',  label: '740+' },
  { value: 'unknown',   label: 'Not sure' },
]
const INCOME_OPTS = [
  { value: 'below_30k',  label: 'Under $30K' },
  { value: '30k_50k',    label: '$30K–$50K' },
  { value: '50k_75k',    label: '$50K–$75K' },
  { value: '75k_100k',   label: '$75K–$100K' },
  { value: '100k_150k',  label: '$100K–$150K' },
  { value: '150k_plus',  label: '$150K+' },
]
const TIMELINE_OPTS = [
  { value: 'asap',           label: 'ASAP — Ready now' },
  { value: 'within_30_days', label: 'Within 30 days' },
  { value: 'within_90_days', label: '1–3 months' },
  { value: 'within_6_months',label: '3–6 months' },
  { value: 'within_1_year',  label: '6–12 months' },
  { value: 'just_exploring', label: 'Just exploring' },
]
const PROPERTY_GOAL_OPTS = [
  { value: 'primary_residence',  label: 'Primary Home' },
  { value: 'investment',         label: 'Investment Property' },
  { value: 'vacation',           label: 'Vacation Home' },
  { value: 'refinance_existing', label: 'Refinance Existing' },
]
const CASH_OPTS = [
  { value: 'under_1k',  label: 'Under $1,000' },
  { value: '1k_5k',     label: '$1K–$5K' },
  { value: '5k_15k',    label: '$5K–$15K' },
  { value: '15k_30k',   label: '$15K–$30K' },
  { value: '30k_plus',  label: '$30K+' },
]

const BLANK_FORM = {
  first_name: '', last_name: '', email: '', phone: '',
  state: '', county: '', city: '',
  loan_interest_type: '', timeline: '', credit_score_range: '',
  income_range: '', cash_available: '', current_rent_mortgage: '',
  property_goal: '',
  consent_email: true, consent_sms: false, consent_call: false,
  notes: '',   // → utm_campaign (admin context notes)
  source: 'admin_manual',
}

export default function Leads() {
  const [leads, setLeads]           = useState([])
  const [selected, setSelected]     = useState(null)
  const [detail, setDetail]         = useState(null)
  const [loading, setLoading]       = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [filter, setFilter]         = useState('all')
  const [notes, setNotes]           = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [prospectLists, setProspectLists] = useState([])

  // Pipeline status update
  const [savingStatus, setSavingStatus] = useState(false)

  const updateStatus = async (leadId, newStatus) => {
    setSavingStatus(true)
    try {
      await api.patch(`/leads/${leadId}/status`, { pipeline_status: newStatus })
      setLeads(prev => prev.map(l => l.id === leadId ? { ...l, pipeline_status: newStatus } : l))
      if (detail?.id === leadId) setDetail(d => ({ ...d, pipeline_status: newStatus }))
      toast.success(`Status → ${newStatus.replace(/_/g, ' ')}`)
    } catch (e) { toast.error(e.message) }
    finally { setSavingStatus(false) }
  }

  // Manual add-lead modal
  const [showAddLead, setShowAddLead] = useState(false)
  const [addForm, setAddForm]         = useState(BLANK_FORM)
  const [addLoading, setAddLoading]   = useState(false)

  const loadLeads = useCallback(() =>
    api.get('/leads/').then(setLeads).catch(e => toast.error(e.message)).finally(() => setLoading(false))
  , [])

  useEffect(() => {
    loadLeads()
    api.get('/outreach/prospect-lists').then(setProspectLists).catch(() => {})
  }, [loadLeads])

  const openDetail = useCallback(async (lead) => {
    setSelected(lead)
    setDetailLoading(true)
    setDetail(null)
    try {
      const d = await api.get(`/leads/${lead.id}`)
      setDetail(d)
      setNotes(d.notes || '')
    } catch { toast.error('Could not load full lead profile') }
    finally { setDetailLoading(false) }
  }, [])

  const saveNotes = async () => {
    if (!detail) return
    setSavingNotes(true)
    try {
      await api.patch(`/leads/${detail.id}/notes`, { notes })
      toast.success('Notes saved')
    } catch { toast.error('Save failed') }
    finally { setSavingNotes(false) }
  }

  const submitManualLead = async () => {
    if (!addForm.first_name || !addForm.email) {
      toast.error('First name and email are required')
      return
    }
    setAddLoading(true)
    try {
      const payload = { ...addForm }
      // Strip empty strings so backend doesn't choke on blank enums
      Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k] })
      const res = await api.post('/leads/intake', payload)
      toast.success(`Lead added · AI scoring in progress…`)
      setShowAddLead(false)
      setAddForm(BLANK_FORM)
      // Refresh list then auto-open new lead
      await loadLeads()
      if (res.intake_id) {
        const newLead = { id: res.intake_id, name: `${addForm.first_name} ${addForm.last_name}`.trim(), created_at: new Date().toISOString() }
        openDetail(newLead)
      }
    } catch (e) { toast.error(e.message || 'Failed to add lead') }
    finally { setAddLoading(false) }
  }

  const filtered = filter === 'all' ? leads : leads.filter(l => l.score?.label === filter)

  return (
    <div className="fade-in" style={{ display: 'flex', gap: '20px', height: '100%', minHeight: 0 }}>

      {/* ── Left: list ─────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '14px', minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Leads</h1>
            <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
              {leads.length} total · {leads.filter(l => l.score?.label === 'hot').length} hot
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {FILTER_LABELS.map(s => (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ fontSize: '0.73rem', padding: '4px 10px' }}
                >
                  {s.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
            {/* ← ADD LEAD button */}
            <button
              onClick={() => { setAddForm(BLANK_FORM); setShowAddLead(true) }}
              className="btn btn-primary btn-sm"
              style={{ gap: '5px', fontSize: '0.78rem', display: 'flex', alignItems: 'center' }}
            >
              <Plus size={13} /> Add Lead
            </button>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden', flex: 1, minHeight: 0 }}>
          <div style={{ overflowY: 'auto', height: '100%' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th><th>Loan Type</th><th>Location</th>
                  <th>Timeline</th><th>Score</th><th>Status</th><th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>Loading…</td></tr>
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>
                    {filter !== 'all' ? `No ${filter.replace(/_/g, ' ')} leads.` : 'No leads yet — use "Add Lead" or share your intake link.'}
                  </td></tr>
                ) : filtered.map(lead => {
                  const sc = SCORE_BADGE[lead.score?.label] || SCORE_BADGE.unscored
                  return (
                    <tr
                      key={lead.id}
                      onClick={() => openDetail(lead)}
                      style={{ cursor: 'pointer', background: selected?.id === lead.id ? 'rgba(245,200,122,0.06)' : undefined }}
                    >
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: 6, height: 6, borderRadius: '50%', background: sc.dot, flexShrink: 0 }} />
                          <span style={{ color: '#ddd', fontWeight: 500 }}>
                            {lead.name || lead.email || 'Anonymous'}
                          </span>
                        </div>
                      </td>
                      <td><span className="badge badge-gray">{lead.loan_interest_type || '—'}</span></td>
                      <td style={{ color: '#aaa', fontSize: '0.8rem' }}>{lead.state || '—'}</td>
                      <td style={{ color: '#aaa', fontSize: '0.8rem' }}>{lead.timeline?.replace(/_/g, ' ') || '—'}</td>
                      <td>
                        <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: '0.7rem', fontWeight: 700, background: sc.bg, color: sc.color }}>
                          {lead.score?.label || 'unscored'}
                          {lead.score?.value ? ` · ${lead.score.value.toFixed(0)}` : ''}
                        </span>
                      </td>
                      <td onClick={e => e.stopPropagation()}>
                        {(() => {
                          const ps = PIPELINE_STATUS_OPTS.find(o => o.value === (lead.pipeline_status || 'new'))
                          return (
                            <select
                              value={lead.pipeline_status || 'new'}
                              onChange={e => updateStatus(lead.id, e.target.value)}
                              disabled={savingStatus}
                              style={{
                                background: '#1a1a1a', border: `1px solid ${ps?.color || '#444'}`,
                                color: ps?.color || '#888', borderRadius: '6px',
                                padding: '2px 6px', fontSize: '0.7rem', fontWeight: 600,
                                cursor: 'pointer', outline: 'none',
                              }}
                            >
                              {PIPELINE_STATUS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                          )
                        })()}
                      </td>
                      <td style={{ color: '#666', fontSize: '0.8rem' }}>
                        {new Date(lead.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Right: detail ──────────────────────────────────────────────────── */}
      {selected && (
        <div className="fade-in" style={{
          width: '380px', flexShrink: 0, overflowY: 'auto', maxHeight: '100%',
          display: 'flex', flexDirection: 'column', gap: '12px',
        }}>
          {/* Header card */}
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <h3 style={{ margin: '0 0 3px', fontSize: '1rem', fontWeight: 700, color: '#eee' }}>
                  {selected.name || selected.email || 'Anonymous'}
                </h3>
                <p style={{ margin: 0, fontSize: '0.75rem', color: '#666' }}>
                  Submitted {new Date(selected.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => { setSelected(null); setDetail(null) }}
                style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}
              >×</button>
            </div>

            {/* Score badge */}
            {selected.score && (() => {
              const sc = SCORE_BADGE[selected.score.label] || SCORE_BADGE.unscored
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <span style={{ padding: '4px 12px', borderRadius: 20, fontSize: '0.8rem', fontWeight: 700, background: sc.bg, color: sc.color }}>
                    {selected.score.label.replace(/_/g, ' ').toUpperCase()}
                    {selected.score.value ? ` · ${selected.score.value.toFixed(0)}/100` : ''}
                  </span>
                </div>
              )
            })()}

            {/* Pipeline status selector */}
            {detail && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.65rem', color: '#555', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Stage</span>
                <select
                  value={detail.pipeline_status || 'new'}
                  onChange={e => updateStatus(detail.id, e.target.value)}
                  disabled={savingStatus}
                  style={{
                    background: '#1a1a1a', border: `1px solid ${PIPELINE_STATUS_OPTS.find(o => o.value === (detail.pipeline_status || 'new'))?.color || '#444'}`,
                    color: PIPELINE_STATUS_OPTS.find(o => o.value === (detail.pipeline_status || 'new'))?.color || '#888',
                    borderRadius: '6px', padding: '4px 10px', fontSize: '0.78rem', fontWeight: 700,
                    cursor: 'pointer', outline: 'none',
                  }}
                >
                  {PIPELINE_STATUS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {detail?.phone && (
                <a href={`tel:${detail.phone}`} className="btn btn-ghost btn-sm" style={{ gap: '5px', fontSize: '0.75rem' }}>
                  <Phone size={12} /> Call
                </a>
              )}
              {detail?.email && (
                <a href={`mailto:${detail.email}`} className="btn btn-ghost btn-sm" style={{ gap: '5px', fontSize: '0.75rem' }}>
                  <Mail size={12} /> Email
                </a>
              )}
              <a
                href={CALCOM}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary btn-sm"
                style={{ gap: '5px', fontSize: '0.75rem' }}
              >
                <ExternalLink size={11} /> Book Call
              </a>
            </div>
          </div>

          {detailLoading && (
            <div className="card" style={{ textAlign: 'center', color: '#555', padding: '20px' }}>Loading profile…</div>
          )}

          {detail && (
            <>
              {/* AI Score breakdown */}
              {detail.score && (
                <div className="card" style={{ padding: '14px' }}>
                  <SectionTitle icon={TrendingIcon} label="AI Score Breakdown" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {detail.score.readiness_score != null && (
                      <Row label="Readiness" val={
                        <ReadinessBar value={detail.score.readiness_score} />
                      } />
                    )}
                    {detail.score.recommended_product && (
                      <Row label="Recommended Product" val={
                        <span className="badge badge-warm">{detail.score.recommended_product}</span>
                      } />
                    )}
                    {detail.score.summary && (
                      <div>
                        <LabelText>AI Summary</LabelText>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#bbb', lineHeight: 1.6 }}>
                          {detail.score.summary}
                        </p>
                      </div>
                    )}
                    {detail.score.recommended_cta && (
                      <div>
                        <LabelText>Suggested CTA</LabelText>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#c8860a', fontStyle: 'italic' }}>
                          "{detail.score.recommended_cta}"
                        </p>
                      </div>
                    )}
                    {detail.score.questions_for_call?.length > 0 && (
                      <div>
                        <LabelText>Questions for Call</LabelText>
                        <ul style={{ margin: '4px 0 0', paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {detail.score.questions_for_call.map((q, i) => (
                            <li key={i} style={{ fontSize: '0.78rem', color: '#aaa', lineHeight: 1.5 }}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Loan + Financial */}
              <div className="card" style={{ padding: '14px' }}>
                <SectionTitle icon={HomeIcon2} label="Loan & Financial" />
                <Grid2>
                  <Row label="Loan Type" val={<Badge>{detail.loan_interest_type?.replace(/_/g,' ')}</Badge>} />
                  <Row label="Goal" val={<Badge>{detail.property_goal?.replace(/_/g,' ')}</Badge>} />
                  <Row label="Timeline" val={detail.timeline?.replace(/_/g,' ')} />
                  <Row label="Credit Range" val={detail.credit_score_range?.replace(/_/g,' ')} />
                  <Row label="Income Range" val={detail.income_range?.replace(/k/g,'K').replace(/_/g,' ')} />
                  <Row label="Cash Available" val={detail.cash_available} />
                  <Row label="Rent / Mortgage" val={detail.current_rent_mortgage} />
                </Grid2>
              </div>

              {/* Contact & Consent */}
              <div className="card" style={{ padding: '14px' }}>
                <SectionTitle icon={UserIcon} label="Contact & Consent" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <Row label="Email" val={detail.email} />
                  <Row label="Phone" val={detail.phone} />
                  <Row label="Location" val={[detail.city, detail.county, detail.state].filter(Boolean).join(', ')} />
                  <Row label="Source" val={detail.utm_source} />
                  <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                    <ConsentChip label="Email" granted={detail.consent_email} />
                    <ConsentChip label="SMS"   granted={detail.consent_sms} />
                    <ConsentChip label="Call"  granted={detail.consent_call} />
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div className="card" style={{ padding: '14px' }}>
                <SectionTitle icon={NoteIcon} label="Notes" />
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Add private notes about this lead…"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  style={{ resize: 'vertical', fontSize: '0.82rem' }}
                />
                <button
                  className="btn btn-primary btn-sm"
                  onClick={saveNotes}
                  disabled={savingNotes}
                  style={{ marginTop: '8px' }}
                >
                  {savingNotes ? 'Saving…' : 'Save Notes'}
                </button>
              </div>

              {/* Add to Outreach List */}
              {prospectLists.length > 0 && (
                <div className="card" style={{ padding: '14px' }}>
                  <SectionTitle icon={PlusIcon} label="Add to Outreach List" />
                  <AddToList lead={detail} lists={prospectLists} />
                </div>
              )}

              {/* Compliance note */}
              {detail.score?.compliance_response && (
                <div className="card" style={{ padding: '12px', background: 'rgba(245,200,122,0.04)', border: '1px solid rgba(245,200,122,0.15)' }}>
                  <LabelText>AI Compliance Note</LabelText>
                  <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#aaa', lineHeight: 1.5, fontStyle: 'italic' }}>
                    "{detail.score.compliance_response}"
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Add Lead Modal ───────────────────────────────────────────────────── */}
      {showAddLead && (
        <AddLeadModal
          form={addForm}
          setForm={setAddForm}
          onSubmit={submitManualLead}
          onClose={() => setShowAddLead(false)}
          loading={addLoading}
        />
      )}
    </div>
  )
}

// ── Add Lead Modal ───────────────────────────────────────────────────────────
function AddLeadModal({ form, setForm, onSubmit, onClose, loading }) {
  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))
  const F = form

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(3px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px',
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        background: '#1a1a1a', border: '1px solid #333', borderRadius: '12px',
        width: '100%', maxWidth: '680px', maxHeight: '90vh', overflowY: 'auto',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Modal header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '18px 22px', borderBottom: '1px solid #2a2a2a', flexShrink: 0,
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Add Lead Manually</h2>
            <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#666' }}>
              Enters as source: admin_manual · AI scores automatically
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        {/* Form body */}
        <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '18px' }}>

          {/* Contact */}
          <FieldGroup label="Contact Info">
            <Row2>
              <Field label="First Name *">
                <input className="input" placeholder="Jane" value={F.first_name} onChange={e => set('first_name', e.target.value)} />
              </Field>
              <Field label="Last Name">
                <input className="input" placeholder="Smith" value={F.last_name} onChange={e => set('last_name', e.target.value)} />
              </Field>
            </Row2>
            <Row2>
              <Field label="Email *">
                <input className="input" type="email" placeholder="jane@example.com" value={F.email} onChange={e => set('email', e.target.value)} />
              </Field>
              <Field label="Phone">
                <input className="input" type="tel" placeholder="(555) 000-0000" value={F.phone} onChange={e => set('phone', e.target.value)} />
              </Field>
            </Row2>
          </FieldGroup>

          {/* Location */}
          <FieldGroup label="Location">
            <Row3>
              <Field label="State">
                <input className="input" placeholder="MD" value={F.state} onChange={e => set('state', e.target.value)} />
              </Field>
              <Field label="County">
                <input className="input" placeholder="Prince George's" value={F.county} onChange={e => set('county', e.target.value)} />
              </Field>
              <Field label="City">
                <input className="input" placeholder="Bowie" value={F.city} onChange={e => set('city', e.target.value)} />
              </Field>
            </Row3>
          </FieldGroup>

          {/* Loan info */}
          <FieldGroup label="Loan Details">
            <Row2>
              <Field label="Loan Type">
                <select className="select" value={F.loan_interest_type} onChange={e => set('loan_interest_type', e.target.value)}>
                  <option value="">— Select —</option>
                  {LOAN_TYPE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Property Goal">
                <select className="select" value={F.property_goal} onChange={e => set('property_goal', e.target.value)}>
                  <option value="">— Select —</option>
                  {PROPERTY_GOAL_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </Row2>
            <Row2>
              <Field label="Credit Score Range">
                <select className="select" value={F.credit_score_range} onChange={e => set('credit_score_range', e.target.value)}>
                  <option value="">— Select —</option>
                  {CREDIT_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Income Range">
                <select className="select" value={F.income_range} onChange={e => set('income_range', e.target.value)}>
                  <option value="">— Select —</option>
                  {INCOME_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </Row2>
            <Row2>
              <Field label="Timeline">
                <select className="select" value={F.timeline} onChange={e => set('timeline', e.target.value)}>
                  <option value="">— Select —</option>
                  {TIMELINE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Cash Available">
                <select className="select" value={F.cash_available} onChange={e => set('cash_available', e.target.value)}>
                  <option value="">— Select —</option>
                  {CASH_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
            </Row2>
            <Field label="Current Rent or Mortgage / mo">
              <input className="input" placeholder="$1,800" value={F.current_rent_mortgage} onChange={e => set('current_rent_mortgage', e.target.value)} />
            </Field>
          </FieldGroup>

          {/* Consent */}
          <FieldGroup label="Contact Consent">
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              {[
                { key: 'consent_email', label: '📧 Email' },
                { key: 'consent_sms',   label: '📱 SMS' },
                { key: 'consent_call',  label: '📞 Call' },
              ].map(({ key, label }) => (
                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '7px', cursor: 'pointer', fontSize: '0.85rem', color: F[key] ? '#f5c87a' : '#888' }}>
                  <input type="checkbox" checked={F[key]} onChange={e => set(key, e.target.checked)} style={{ accentColor: '#f5c87a' }} />
                  {label}
                </label>
              ))}
            </div>
          </FieldGroup>

          {/* Notes */}
          <FieldGroup label="Admin Notes">
            <textarea
              className="input"
              rows={3}
              placeholder="How did you meet them? What did they say? Any context for the AI scorer…"
              value={F.notes}
              onChange={e => set('notes', e.target.value)}
              style={{ resize: 'vertical', fontSize: '0.82rem' }}
            />
          </FieldGroup>
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 22px', borderTop: '1px solid #2a2a2a', flexShrink: 0,
          display: 'flex', justifyContent: 'flex-end', gap: '10px',
        }}>
          <button onClick={onClose} className="btn btn-ghost" disabled={loading}>Cancel</button>
          <button onClick={onSubmit} className="btn btn-primary" disabled={loading}>
            {loading ? 'Adding…' : 'Add Lead + Score with AI'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Add-to-list sub-component ────────────────────────────────────────────────
function AddToList({ lead, lists }) {
  const [listId, setListId] = useState(lists[0]?.id || '')
  const [adding, setAdding] = useState(false)

  const add = async () => {
    if (!listId || !lead.email) { toast.error('Lead needs an email address to be added to a list'); return }
    setAdding(true)
    try {
      await api.post(`/outreach/prospect-lists/${listId}/prospects`, [{
        email: lead.email,
        first_name: lead.first_name || '',
        last_name:  lead.last_name  || '',
        phone:      lead.phone      || '',
        state:      lead.state      || '',
        source:     'lead_intake',
        tags:       [lead.loan_interest_type || 'intake', lead.score?.label || 'unscored'],
      }])
      toast.success('Added to outreach list')
    } catch (e) { toast.error(e.message) }
    finally { setAdding(false) }
  }

  return (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
      <select
        className="select"
        value={listId}
        onChange={e => setListId(e.target.value)}
        style={{ flex: 1, fontSize: '0.8rem' }}
      >
        {lists.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
      </select>
      <button className="btn btn-primary btn-sm" onClick={add} disabled={adding}>
        {adding ? '…' : <Plus size={13} />}
      </button>
    </div>
  )
}

// ── Modal form helpers ───────────────────────────────────────────────────────
function FieldGroup({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#555', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '10px' }}>
        {label}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {children}
      </div>
    </div>
  )
}
function Row2({ children }) { return <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>{children}</div> }
function Row3({ children }) { return <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>{children}</div> }
function Field({ label, children }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '0.72rem', color: '#777', marginBottom: '5px', fontWeight: 500 }}>{label}</label>
      {children}
    </div>
  )
}

// ── Small shared components ──────────────────────────────────────────────────
function SectionTitle({ icon: Icon, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
      {Icon && <Icon size={13} color="var(--color-warm)" />}
      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
        {label}
      </span>
    </div>
  )
}

function Grid2({ children }) {
  return <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>{children}</div>
}

function Row({ label, val }) {
  if (!val && val !== 0) return null
  return (
    <div>
      <LabelText>{label}</LabelText>
      <div style={{ fontSize: '0.82rem', color: '#ccc' }}>{val}</div>
    </div>
  )
}

function Badge({ children }) {
  if (!children) return null
  return (
    <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: '0.72rem', fontWeight: 600, background: '#2a2a2a', color: '#aaa' }}>
      {children}
    </span>
  )
}

function LabelText({ children }) {
  return <p style={{ margin: '0 0 2px', fontSize: '0.65rem', color: '#555', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>{children}</p>
}

function ConsentChip({ label, granted }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: granted ? '#4ade80' : '#555' }}>
      {granted ? <CheckCircle size={11} /> : <XCircle size={11} />}
      {label}
    </div>
  )
}

function ReadinessBar({ value }) {
  const pct = Math.min(100, Math.max(0, value || 0))
  const color = pct >= 70 ? '#4ade80' : pct >= 45 ? '#f5c87a' : '#f87171'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '6px', background: '#2a2a2a', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.4s' }} />
      </div>
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color }}>{pct}/100</span>
    </div>
  )
}

// Inline icon shims
const TrendingIcon  = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
const HomeIcon2     = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
const UserIcon      = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
const NoteIcon      = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
const PlusIcon      = ({ size }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>

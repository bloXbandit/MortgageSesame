import { useState, useEffect, useRef } from 'react'
import { api } from '../utils/api'
import { Upload, Search, UserX, UserPlus, X } from 'lucide-react'
import toast from 'react-hot-toast'

const TYPES = ['', 'consumer', 'realtor', 'title_agent', 'investor', 'business_owner', 'homeowner', 'past_client', 'referral_partner']
const TYPE_LABELS = {
  consumer: 'Consumer', realtor: 'Realtor', title_agent: 'Title Agent',
  investor: 'Investor', business_owner: 'Business Owner', homeowner: 'Homeowner',
  past_client: 'Past Client', referral_partner: 'Referral Partner',
}
const SCORE_COLORS = { hot: '#4ade80', warm: '#f5c87a', long_term: '#60a5fa', bad_fit: '#9ca3af', compliance_risk: '#f87171', unscored: '#555' }

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', phone: '',
  company: '', role_title: '', city: '', state: '',
  contact_type: 'consumer', source: 'manual', notes: '',
  consent_email: false, consent_sms: false, consent_call: false,
}

export default function Contacts() {
  const [contacts, setContacts]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [importing, setImporting] = useState(false)
  const [showAdd, setShowAdd]     = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const fileRef = useRef()

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (typeFilter) params.set('contact_type', typeFilter)
      const data = await api.get(`/contacts/?${params}`)
      setContacts(data)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search, typeFilter])

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('source_name', file.name)
    fd.append('contact_type', typeFilter || 'consumer')
    setImporting(true)
    try {
      const result = await api.upload('/contacts/import/csv', fd)
      toast.success(`Imported ${result.created} contacts (${result.skipped} skipped)`)
      load()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setImporting(false)
      fileRef.current.value = ''
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const body = { ...form }
      // Strip empty strings → null
      ;['email', 'phone', 'company', 'role_title', 'city', 'state', 'notes'].forEach(k => {
        if (body[k] === '') body[k] = null
      })
      await api.post('/contacts/', body)
      toast.success('Contact added ✓')
      setForm(EMPTY_FORM)
      setShowAdd(false)
      load()
    } catch (e) {
      toast.error(e.message || 'Failed to add contact')
    } finally {
      setSaving(false)
    }
  }

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const markDnc = async (id) => {
    try {
      await api.patch(`/contacts/${id}/dnc`)
      toast.success('Marked as DNC')
      setContacts(c => c.filter(x => x.id !== id))
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Contacts</h1>
          <p style={{ margin: 0, color: '#888', fontSize: '0.875rem' }}>{contacts.length} contacts loaded</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleFileUpload} />
          <button className="btn btn-ghost" onClick={() => fileRef.current.click()} disabled={importing}>
            <Upload size={13} /> {importing ? 'Importing…' : 'Import CSV'}
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(v => !v)}>
            <UserPlus size={13} /> Add Contact
          </button>
        </div>
      </div>

      {/* ── Manual Add Form ─────────────────────────────────────────────────── */}
      {showAdd && (
        <div style={{ background: '#2a2a2a', border: '1px solid #333', borderRadius: 10, padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0, color: '#fff', fontSize: '0.9375rem', fontWeight: 700 }}>New Contact</h3>
            <button onClick={() => setShowAdd(false)} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', padding: 4 }}>
              <X size={16} />
            </button>
          </div>
          <form onSubmit={handleAdd}>
            {/* Type selector — prominently at top */}
            <div style={{ marginBottom: 14 }}>
              <label style={labelSt}>Contact Type</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {TYPES.filter(Boolean).map(t => (
                  <button key={t} type="button"
                    onClick={() => set('contact_type', t)}
                    style={{
                      padding: '5px 12px', borderRadius: 99, border: '1px solid',
                      fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                      background: form.contact_type === t ? '#f5c87a' : 'transparent',
                      borderColor: form.contact_type === t ? '#f5c87a' : '#444',
                      color: form.contact_type === t ? '#1f1f1f' : '#888',
                    }}>
                    {TYPE_LABELS[t] || t}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 10 }}>
              <CField label="First Name" value={form.first_name} onChange={v => set('first_name', v)} />
              <CField label="Last Name"  value={form.last_name}  onChange={v => set('last_name', v)} />
              <CField label="Email"      value={form.email}      onChange={v => set('email', v)} type="email" />
              <CField label="Phone"      value={form.phone}      onChange={v => set('phone', v)} type="tel" />
              <CField label="Company / Brokerage" value={form.company}     onChange={v => set('company', v)} />
              <CField label="Role / Title"        value={form.role_title}  onChange={v => set('role_title', v)} placeholder="e.g. REALTOR®, Listing Agent" />
              <CField label="City"   value={form.city}  onChange={v => set('city', v)} />
              <CField label="State"  value={form.state} onChange={v => set('state', v)} placeholder="MD" />
              <CField label="Source" value={form.source} onChange={v => set('source', v)} placeholder="manual, referral, open house…" />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={labelSt}>Notes</label>
              <textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2}
                style={{ width: '100%', padding: '8px 12px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.875rem', resize: 'vertical', boxSizing: 'border-box' }} />
            </div>

            <div style={{ display: 'flex', gap: 16, marginBottom: 14, flexWrap: 'wrap' }}>
              {[['consent_email', 'Email consent'], ['consent_sms', 'SMS consent'], ['consent_call', 'Call consent']].map(([k, lbl]) => (
                <label key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#ccc', fontSize: '0.825rem' }}>
                  <input type="checkbox" checked={form[k]} onChange={e => set(k, e.target.checked)}
                    style={{ accentColor: '#f5c87a', width: 14, height: 14 }} />
                  {lbl}
                </label>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button type="submit" disabled={saving}
                style={{ padding: '8px 20px', background: saving ? '#444' : '#f5c87a', color: '#e5e5e5', border: 'none', borderRadius: 6, fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer', fontSize: '0.875rem' }}>
                {saving ? 'Saving…' : 'Add Contact'}
              </button>
              <button type="button" onClick={() => setShowAdd(false)}
                style={{ padding: '8px 14px', background: 'transparent', color: '#888', border: '1px solid #444', borderRadius: 6, cursor: 'pointer', fontSize: '0.875rem' }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={13} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
          <input className="input" placeholder="Search name, email, company..." value={search}
            onChange={e => setSearch(e.target.value)} style={{ paddingLeft: '32px' }} />
        </div>
        <select className="select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ width: 'auto' }}>
          <option value="">All Types</option>
          {TYPES.filter(Boolean).map(t => <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Type</th>
              <th>Company</th>
              <th>Score</th>
              <th>Consent</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: '#999', padding: '32px' }}>Loading…</td></tr>
            ) : contacts.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: '#999', padding: '32px' }}>No contacts found.</td></tr>
            ) : contacts.map(c => (
              <tr key={c.id}>
                <td style={{ color: '#ddd', fontWeight: 500 }}>{c.full_name || '—'}</td>
                <td style={{ color: '#aaa' }}>{c.email || '—'}</td>
                <td style={{ color: '#aaa' }}>{c.phone || '—'}</td>
                <td>
                  <span className="badge badge-gray" style={{
                    background: c.contact_type === 'realtor' ? '#f5c87a22' : undefined,
                    color: c.contact_type === 'realtor' ? '#f5c87a' : undefined,
                  }}>
                    {TYPE_LABELS[c.contact_type] || c.contact_type}
                  </span>
                </td>
                <td style={{ color: '#888', fontSize: '0.75rem' }}>{c.company || c.source || '—'}</td>
                <td>
                  <span style={{
                    fontSize: '0.7rem', fontWeight: 600,
                    color: SCORE_COLORS[c.lead_score] || '#666',
                    textTransform: 'uppercase', letterSpacing: '0.5px',
                  }}>
                    {c.lead_score || 'unscored'}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {c.consent_email && <span className="badge badge-green" style={{ padding: '1px 5px', fontSize: '0.65rem' }}>E</span>}
                    {c.consent_sms   && <span className="badge badge-blue"  style={{ padding: '1px 5px', fontSize: '0.65rem' }}>S</span>}
                  </div>
                </td>
                <td>
                  <button className="btn btn-danger btn-sm" onClick={() => markDnc(c.id)} title="Mark DNC">
                    <UserX size={11} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const labelSt = { display: 'block', fontSize: '0.73rem', color: '#888', fontWeight: 500, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }

function CField({ label, value, onChange, type = 'text', placeholder }) {
  return (
    <div>
      <label style={labelSt}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{ width: '100%', padding: '8px 10px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
    </div>
  )
}

import { useState, useEffect, useRef } from 'react'
import { api } from '../utils/api'
import { Upload, Search, UserX, Filter } from 'lucide-react'
import toast from 'react-hot-toast'

const TYPES = ['', 'consumer', 'realtor', 'title_agent', 'investor', 'business_owner', 'homeowner', 'past_client', 'referral_partner']
const SCORE_COLORS = { hot: '#4ade80', warm: '#f5c87a', long_term: '#60a5fa', bad_fit: '#9ca3af', compliance_risk: '#f87171', unscored: '#555' }

export default function Contacts() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [importing, setImporting] = useState(false)
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
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>{contacts.length} contacts loaded</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleFileUpload} />
          <button className="btn btn-ghost" onClick={() => fileRef.current.click()} disabled={importing}>
            <Upload size={13} /> {importing ? 'Importing...' : 'Import CSV'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={13} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#555' }} />
          <input className="input" placeholder="Search name, email, company..." value={search}
            onChange={e => setSearch(e.target.value)} style={{ paddingLeft: '32px' }} />
        </div>
        <select className="select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ width: 'auto' }}>
          <option value="">All Types</option>
          {TYPES.filter(Boolean).map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
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
              <th>Source</th>
              <th>Score</th>
              <th>Consent</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>Loading...</td></tr>
            ) : contacts.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>No contacts found.</td></tr>
            ) : contacts.map(c => (
              <tr key={c.id}>
                <td style={{ color: '#ddd', fontWeight: 500 }}>{c.full_name || '—'}</td>
                <td style={{ color: '#aaa' }}>{c.email || '—'}</td>
                <td style={{ color: '#aaa' }}>{c.phone || '—'}</td>
                <td><span className="badge badge-gray">{c.contact_type}</span></td>
                <td style={{ color: '#666', fontSize: '0.75rem' }}>{c.source || '—'}</td>
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

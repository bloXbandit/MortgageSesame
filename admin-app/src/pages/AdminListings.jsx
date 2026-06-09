import { useState, useEffect } from 'react'
import { api } from '../utils/api'

const EMPTY_FORM = {
  address: '', city: '', state: 'MD', county: '', zip_code: '',
  list_price: '', bedrooms: '', bathrooms: '', sqft: '',
  property_type: '', photo_url: '', zillow_url: '',
  description: '', status: 'active', is_featured: true,
  hoa_monthly: '', annual_taxes: '', annual_insurance: '',
  // Listing agent
  listing_agent_contact_id: '',
  listing_agent_name: '',
  listing_agent_phone: '',
  listing_agent_email: '',
}

const STATUS_LABELS = {
  active: 'Active', coming_soon: 'Coming Soon', under_contract: 'Under Contract', sold: 'Sold',
}

export default function AdminListings() {
  const [listings, setListings]   = useState([])
  const [realtors, setRealtors]   = useState([])   // realtor contacts for picker
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [saving, setSaving]       = useState(false)
  const [msg, setMsg]             = useState(null)
  const [editId, setEditId]       = useState(null)
  const [uploading, setUploading] = useState(false)

  const load = async () => {
    try {
      const [data, rdata] = await Promise.all([
        api.get('/listings/'),
        api.get('/listings/realtors').catch(() => []),
      ])
      setListings(data)
      setRealtors(rdata || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const data = await api.upload('/agent/write/listing/upload-image/file', fd)
      set('photo_url', data.url)
    } catch (err) {
      setMsg({ type: 'error', text: `Photo upload failed: ${err.message}` })
    }
    setUploading(false)
    e.target.value = ''
  }

  // When a realtor is picked from the dropdown, auto-fill the freeform fields
  const handleRealtorPick = (contactId) => {
    set('listing_agent_contact_id', contactId)
    if (!contactId) return
    const r = realtors.find(r => r.id === contactId)
    if (r) {
      set('listing_agent_name',  r.name  || '')
      set('listing_agent_phone', r.phone || '')
      set('listing_agent_email', r.email || '')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMsg(null)
    try {
      const body = { ...form }
      // Convert numeric strings
      ;['list_price', 'bedrooms', 'bathrooms', 'sqft', 'hoa_monthly', 'annual_taxes', 'annual_insurance'].forEach(k => {
        if (body[k] === '') body[k] = null
        else if (body[k] !== null) body[k] = parseFloat(body[k])
      })
      ;['county', 'zip_code', 'property_type', 'photo_url', 'zillow_url', 'description',
        'listing_agent_contact_id', 'listing_agent_name', 'listing_agent_phone', 'listing_agent_email',
      ].forEach(k => {
        if (body[k] === '') body[k] = null
      })

      if (editId) {
        await api.patch(`/listings/${editId}`, body)
        setMsg({ type: 'success', text: 'Listing updated ✓' })
      } else {
        await api.post('/listings/', body)
        setMsg({ type: 'success', text: 'Listing created ✓' })
      }
      setForm(EMPTY_FORM)
      setShowForm(false)
      setEditId(null)
      load()
    } catch {
      setMsg({ type: 'error', text: 'Save failed — check all required fields.' })
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this listing?')) return
    try {
      await api.delete(`/listings/${id}`)
      load()
    } catch {}
  }

  const handleEdit = (l) => {
    setEditId(l.id)
    setForm({
      address: l.address || '', city: l.city || '', state: l.state || 'MD',
      county: l.county || '', zip_code: l.zip_code || '',
      list_price: l.list_price?.toString() || '',
      bedrooms: l.bedrooms?.toString() || '',
      bathrooms: l.bathrooms?.toString() || '',
      sqft: l.sqft?.toString() || '',
      property_type: l.property_type || '',
      photo_url: l.photo_url || '', zillow_url: l.zillow_url || '',
      description: l.description || '', status: l.status || 'active',
      is_featured: l.is_featured ?? true,
      hoa_monthly: l.hoa_monthly?.toString() || '',
      annual_taxes: l.annual_taxes?.toString() || '',
      annual_insurance: l.annual_insurance?.toString() || '',
      listing_agent_contact_id: l.listing_agent_contact_id || '',
      listing_agent_name:       l.listing_agent_name  || '',
      listing_agent_phone:      l.listing_agent_phone || '',
      listing_agent_email:      l.listing_agent_email || '',
    })
    setShowForm(true)
  }

  const fmt = (n) => n ? '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, color: 'var(--color-paper)', fontSize: '1.4rem', fontWeight: 800 }}>Listings</h1>
          <p style={{ margin: '2px 0 0', color: '#888', fontSize: '0.875rem' }}>Manage properties shown on the public hub.</p>
        </div>
        <button
          onClick={() => { setEditId(null); setForm(EMPTY_FORM); setShowForm(true) }}
          style={{ padding: '9px 18px', background: '#f5c87a', color: '#e5e5e5', border: 'none', borderRadius: 6, fontWeight: 700, cursor: 'pointer', fontSize: '0.875rem' }}
        >
          + Add Listing
        </button>
      </div>

      {msg && (
        <div style={{
          marginBottom: 14, padding: '10px 14px', borderRadius: 7,
          background: msg.type === 'success' ? '#14532d22' : '#7f1d1d22',
          color: msg.type === 'success' ? '#4ade80' : '#f87171',
          fontSize: '0.875rem',
        }}>
          {msg.text}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div style={{ background: '#2a2a2a', border: '1px solid #333', borderRadius: 10, padding: '22px', marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 16px', color: '#fff', fontSize: '1rem', fontWeight: 700 }}>
            {editId ? 'Edit Listing' : 'New Listing'}
          </h3>
          <form onSubmit={handleSubmit}>
            {/* Property details */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 12 }}>
              <Field label="Address *" value={form.address} onChange={v => set('address', v)} required />
              <Field label="City *" value={form.city} onChange={v => set('city', v)} required />
              <Field label="State" value={form.state} onChange={v => set('state', v)} />
              <Field label="County" value={form.county} onChange={v => set('county', v)} />
              <Field label="ZIP Code" value={form.zip_code} onChange={v => set('zip_code', v)} />
              <Field label="List Price *" value={form.list_price} onChange={v => set('list_price', v)} type="number" required />
              <Field label="Bedrooms" value={form.bedrooms} onChange={v => set('bedrooms', v)} type="number" />
              <Field label="Bathrooms" value={form.bathrooms} onChange={v => set('bathrooms', v)} type="number" step="0.5" />
              <Field label="Sq Ft" value={form.sqft} onChange={v => set('sqft', v)} type="number" />
              <Field label="Property Type" value={form.property_type} onChange={v => set('property_type', v)} placeholder="single family, condo…" />
              <Field label="Annual Taxes ($)" value={form.annual_taxes} onChange={v => set('annual_taxes', v)} type="number" />
              <Field label="Annual Insurance ($)" value={form.annual_insurance} onChange={v => set('annual_insurance', v)} type="number" />
              <Field label="HOA Monthly ($)" value={form.hoa_monthly} onChange={v => set('hoa_monthly', v)} type="number" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              {/* Photo — upload button or paste URL */}
              <div>
                <label style={labelStyle}>Hero Photo</label>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {/* upload button */}
                  <label style={{
                    padding: '8px 14px', background: uploading ? '#2a2a2a' : '#1f1f1f',
                    border: '1px solid #3a3a3a', borderRadius: 6, color: uploading ? '#888' : '#f5c87a',
                    fontSize: '0.8rem', fontWeight: 600, cursor: uploading ? 'not-allowed' : 'pointer',
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}>
                    {uploading ? 'Uploading…' : '⬆ Upload'}
                    <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handlePhotoUpload} disabled={uploading} />
                  </label>
                  {/* URL field — auto-filled after upload, or paste manually */}
                  <input
                    value={form.photo_url}
                    onChange={e => set('photo_url', e.target.value)}
                    placeholder="or paste URL…"
                    style={{ flex: 1, padding: '8px 10px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.8rem', minWidth: 0 }}
                  />
                </div>
                {/* Preview thumbnail */}
                {form.photo_url && (
                  <img src={form.photo_url} alt="preview" style={{ marginTop: 8, width: '100%', height: 80, objectFit: 'cover', borderRadius: 6, border: '1px solid #3a3a3a' }} />
                )}
              </div>
              <Field label="Zillow URL" value={form.zillow_url} onChange={v => set('zillow_url', v)} placeholder="https://zillow.com/…" />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Description</label>
              <textarea
                value={form.description}
                onChange={e => set('description', e.target.value)}
                rows={3}
                style={{ width: '100%', padding: '9px 12px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.875rem', resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            {/* ── Listing Agent ─────────────────────────────────────────── */}
            <div style={{ borderTop: '1px solid #333', paddingTop: 16, marginBottom: 16 }}>
              <p style={{ margin: '0 0 12px', color: '#f5c87a', fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                Listing Agent <span style={{ color: '#999', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(optional)</span>
              </p>

              {/* Pick from realtor contacts */}
              <div style={{ marginBottom: 10 }}>
                <label style={labelStyle}>Pick from your realtor contacts</label>
                <select
                  value={form.listing_agent_contact_id}
                  onChange={e => handleRealtorPick(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: form.listing_agent_contact_id ? '#fff' : '#666', fontSize: '0.875rem' }}
                >
                  <option value="">— Select a realtor contact or enter manually below —</option>
                  {realtors.map(r => (
                    <option key={r.id} value={r.id}>
                      {r.name}{r.company ? ` · ${r.company}` : ''}
                    </option>
                  ))}
                </select>
                {realtors.length === 0 && (
                  <p style={{ margin: '4px 0 0', color: '#999', fontSize: '0.75rem' }}>
                    No realtor contacts yet — add them under Contacts → Realtor type, or enter manually below.
                  </p>
                )}
              </div>

              {/* Freeform agent fields (editable even when linked — link is just a convenience) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                <Field label="Agent Name" value={form.listing_agent_name} onChange={v => set('listing_agent_name', v)} placeholder="Jane Smith" />
                <Field label="Agent Phone" value={form.listing_agent_phone} onChange={v => set('listing_agent_phone', v)} placeholder="(301) 555-0100" />
                <Field label="Agent Email" value={form.listing_agent_email} onChange={v => set('listing_agent_email', v)} placeholder="jane@brokerage.com" />
              </div>
            </div>

            {/* Status + featured */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
              <div>
                <label style={labelStyle}>Status</label>
                <select
                  value={form.status}
                  onChange={e => set('status', e.target.value)}
                  style={{ padding: '8px 12px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.875rem' }}
                >
                  {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 20 }}>
                <input type="checkbox" checked={form.is_featured} onChange={e => set('is_featured', e.target.checked)} style={{ accentColor: '#f5c87a', width: 16, height: 16 }} />
                <span style={{ color: '#ccc', fontSize: '0.875rem' }}>Featured on home page</span>
              </label>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button type="submit" disabled={saving}
                style={{ padding: '9px 20px', background: saving ? '#444' : '#f5c87a', color: '#e5e5e5', border: 'none', borderRadius: 6, fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer', fontSize: '0.875rem' }}>
                {saving ? 'Saving…' : editId ? 'Update Listing' : 'Create Listing'}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setEditId(null) }}
                style={{ padding: '9px 16px', background: 'transparent', color: '#888', border: '1px solid #444', borderRadius: 6, cursor: 'pointer', fontSize: '0.875rem' }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div style={{ color: '#999' }}>Loading…</div>
      ) : listings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: '#999' }}>No listings yet. Add your first one above.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {listings.map(l => (
            <div key={l.id} style={{ background: '#2a2a2a', border: '1px solid #333', borderRadius: 8, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              {l.photo_url && (
                <img src={l.photo_url} alt="" style={{ width: 56, height: 44, borderRadius: 5, objectFit: 'cover', flexShrink: 0 }} />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.9375rem' }}>{fmt(l.list_price)}</div>
                <div style={{ color: '#888', fontSize: '0.8125rem', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {l.address}, {l.city}, {l.state}
                  {l.bedrooms && ` · ${l.bedrooms}bd`}
                  {l.bathrooms && `/${l.bathrooms}ba`}
                </div>
                {/* Agent badge */}
                {l.listing_agent_name && (
                  <div style={{ marginTop: 3, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ fontSize: '0.7rem', color: '#f5c87a', fontWeight: 600 }}>🏠</span>
                    <span style={{ fontSize: '0.75rem', color: '#aaa' }}>{l.listing_agent_name}</span>
                    {l.listing_agent_phone && (
                      <span style={{ fontSize: '0.72rem', color: '#888' }}>· {l.listing_agent_phone}</span>
                    )}
                  </div>
                )}
              </div>
              <span style={{
                padding: '2px 10px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600, flexShrink: 0,
                background: l.status === 'active' ? '#14532d33' : '#44444433',
                color: l.status === 'active' ? '#4ade80' : '#888',
              }}>
                {STATUS_LABELS[l.status] || l.status}
              </span>
              {l.is_featured && <span style={{ padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', background: '#f5c87a22', color: '#f5c87a', flexShrink: 0 }}>Featured</span>}
              <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                <button onClick={() => handleEdit(l)}
                  style={{ padding: '5px 12px', background: 'transparent', color: '#888', border: '1px solid #444', borderRadius: 5, cursor: 'pointer', fontSize: '0.8rem' }}>
                  Edit
                </button>
                <button onClick={() => handleDelete(l.id)}
                  style={{ padding: '5px 12px', background: 'transparent', color: '#f87171', border: '1px solid #7f1d1d44', borderRadius: 5, cursor: 'pointer', fontSize: '0.8rem' }}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: '0.73rem', color: '#888', fontWeight: 500, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }

function Field({ label, value, onChange, type = 'text', required, placeholder, step }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        step={step}
        style={{ width: '100%', padding: '9px 12px', background: '#1f1f1f', border: '1px solid #3a3a3a', borderRadius: 6, color: '#fff', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }}
      />
    </div>
  )
}

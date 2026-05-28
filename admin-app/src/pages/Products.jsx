import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Plus, Package, ChevronDown, ChevronUp, ToggleLeft, ToggleRight } from 'lucide-react'
import toast from 'react-hot-toast'

const TYPES = ['dpa','fha','conventional','va','usda','dscr','heloc','cashout_refi','rate_term_refi','bank_statement','itin','investor','jumbo']

export default function Products() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [form, setForm] = useState({ name: '', product_type: 'fha', audience: '', basic_eligibility: '', benefits: '', risks_limitations: '', cta_language: '', prohibited_claims: '', source_notes: '', is_active: true })

  const load = () => api.get('/products/?active_only=false').then(setProducts).catch(e => toast.error(e.message)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const save = async () => {
    try {
      await api.post('/products/', form)
      toast.success('Product created')
      setShowForm(false)
      setForm({ name: '', product_type: 'fha', audience: '', basic_eligibility: '', benefits: '', risks_limitations: '', cta_language: '', prohibited_claims: '', source_notes: '', is_active: true })
      load()
    } catch (e) { toast.error(e.message) }
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Product Library</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>Mortgage programs your agent uses for outreach and content.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
          <Plus size={13} /> Add Product
        </button>
      </div>

      {showForm && (
        <div className="card fade-in" style={{ maxWidth: '640px' }}>
          <h3 style={{ margin: '0 0 20px', fontSize: '0.9rem', fontWeight: 600 }}>New Product</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={lbl}>Product Name</label>
              <input className="input" placeholder="e.g. Texas DPA Advantage" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label style={lbl}>Type</label>
              <select className="select" value={form.product_type} onChange={e => setForm(f => ({ ...f, product_type: e.target.value }))}>
                {TYPES.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Audience</label>
              <input className="input" placeholder="First-time buyers in TX" value={form.audience} onChange={e => setForm(f => ({ ...f, audience: e.target.value }))} />
            </div>
            {[
              { key: 'basic_eligibility', label: 'Basic Eligibility', ph: 'Credit 620+, income limits apply...' },
              { key: 'benefits', label: 'Benefits', ph: 'Up to $15K DPA, no repayment...' },
              { key: 'risks_limitations', label: 'Risks / Limitations', ph: 'Income cap, primary residence only...' },
              { key: 'cta_language', label: 'CTA Language', ph: 'Book a free DPA check...' },
              { key: 'prohibited_claims', label: 'Prohibited Claims', ph: 'Do not guarantee approval...' },
            ].map(({ key, label, ph }) => (
              <div key={key} style={{ gridColumn: '1 / -1' }}>
                <label style={lbl}>{label}</label>
                <textarea className="input" placeholder={ph} value={form[key]} rows={2}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary" onClick={save}>Save Product</button>
            <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {loading ? <p style={{ color: '#555' }}>Loading...</p> : products.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <Package size={28} color="#555" style={{ marginBottom: '12px' }} />
            <p style={{ color: '#ccc', margin: '0 0 4px', fontWeight: 600 }}>No products yet</p>
            <p style={{ color: '#555', fontSize: '0.8125rem', margin: 0 }}>Add your first mortgage product to get started.</p>
          </div>
        ) : products.map(p => (
          <div key={p.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div onClick={() => setExpanded(expanded === p.id ? null : p.id)} style={{
              display: 'flex', alignItems: 'center', gap: '14px', padding: '13px 18px', cursor: 'pointer',
            }}>
              <span className="badge badge-blue" style={{ textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>{p.product_type}</span>
              <span style={{ flex: 1, fontSize: '0.875rem', fontWeight: 500, color: '#ddd' }}>{p.name}</span>
              <span style={{ fontSize: '0.75rem', color: p.is_active ? '#4ade80' : '#666' }}>
                {p.is_active ? '● Active' : '○ Inactive'}
              </span>
              {expanded === p.id ? <ChevronUp size={14} color="#666" /> : <ChevronDown size={14} color="#666" />}
            </div>
            {expanded === p.id && (
              <div style={{ borderTop: '1px solid var(--color-carbon-border)', padding: '16px 18px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  {[
                    { label: 'Audience', val: p.audience },
                    { label: 'Basic Eligibility', val: p.basic_eligibility },
                    { label: 'Benefits', val: p.benefits },
                    { label: 'Risks', val: p.risks_limitations },
                    { label: 'CTA Language', val: p.cta_language },
                    { label: 'Prohibited Claims', val: p.prohibited_claims },
                  ].filter(f => f.val).map(({ label, val }) => (
                    <div key={label}>
                      <p style={lbl}>{label}</p>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#bbb', lineHeight: 1.5 }}>{val}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const lbl = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '5px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px' }

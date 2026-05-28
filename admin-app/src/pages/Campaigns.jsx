import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Plus, Megaphone } from 'lucide-react'
import toast from 'react-hot-toast'

const STATUS_BADGE = { draft: 'badge-gray', active: 'badge-green', paused: 'badge-warm', completed: 'badge-blue', archived: 'badge-gray' }
const TYPES = ['realtor_partnership','title_refi','dpa_buyer','dscr_investor','heloc_homeowner','open_house_qr','social_content','past_lead_nurture']
const GOALS = ['book_call','drive_ai_intake','promote_dpa','promote_dscr','promote_heloc','promote_refi','recruit_realtor','open_house_tool']
const CHANNELS = ['email','sms','linkedin','instagram','tiktok','facebook','google_business','manual']

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', campaign_type: 'dpa_buyer', goal: 'book_call', channel: 'email', sequence_length: 3, follow_up_days: 3, requires_approval: true })
  const [products, setProducts] = useState([])

  const load = async () => {
    const [c, p] = await Promise.allSettled([api.get('/campaigns/'), api.get('/products/')])
    if (c.status === 'fulfilled') setCampaigns(c.value)
    if (p.status === 'fulfilled') setProducts(p.value)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const save = async () => {
    try {
      await api.post('/campaigns/', form)
      toast.success('Campaign created')
      setShowForm(false)
      load()
    } catch (e) { toast.error(e.message) }
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Campaigns</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>Outreach sequences — all require approval before sending.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
          <Plus size={13} /> New Campaign
        </button>
      </div>

      {showForm && (
        <div className="card fade-in" style={{ maxWidth: '560px' }}>
          <h3 style={{ margin: '0 0 20px', fontSize: '0.9rem', fontWeight: 600 }}>New Campaign</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={lbl}>Campaign Name</label>
              <input className="input" placeholder="Q3 DPA Buyer Outreach" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <Sel label="Type" value={form.campaign_type} options={TYPES} onChange={v => setForm(f => ({ ...f, campaign_type: v }))} />
              <Sel label="Goal" value={form.goal} options={GOALS} onChange={v => setForm(f => ({ ...f, goal: v }))} />
              <Sel label="Channel" value={form.channel} options={CHANNELS} onChange={v => setForm(f => ({ ...f, channel: v }))} />
              <div>
                <label style={lbl}>Product (optional)</label>
                <select className="select" value={form.product_id || ''} onChange={e => setForm(f => ({ ...f, product_id: e.target.value || undefined }))}>
                  <option value="">None</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
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
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" className="checkbox-warm" checked={form.requires_approval}
                onChange={e => setForm(f => ({ ...f, requires_approval: e.target.checked }))} />
              <span style={{ fontSize: '0.8125rem', color: '#ccc' }}>Require approval before sending (recommended)</span>
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn btn-primary" onClick={save}>Create Campaign</button>
              <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {loading ? <p style={{ color: '#555' }}>Loading...</p> : campaigns.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <Megaphone size={28} color="#555" style={{ marginBottom: '12px' }} />
            <p style={{ color: '#ccc', fontWeight: 600, margin: '0 0 4px' }}>No campaigns yet</p>
          </div>
        ) : campaigns.map(c => (
          <div key={c.id} className="card card-sm">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className={`badge ${STATUS_BADGE[c.status] || 'badge-gray'}`}>{c.status}</span>
              <span style={{ flex: 1, fontWeight: 500, fontSize: '0.875rem', color: '#ddd' }}>{c.name}</span>
              <span className="badge badge-gray">{c.campaign_type?.replace(/_/g, ' ')}</span>
              <span className="badge badge-gray">{c.channel}</span>
              <span style={{ fontSize: '0.75rem', color: '#555' }}>{c.contact_count} contacts</span>
              <span style={{ fontSize: '0.7rem', color: c.requires_approval ? '#f5c87a' : '#666' }}>
                {c.requires_approval ? '🔒 approval' : '⚡ auto'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Sel({ label, value, options, onChange }) {
  return (
    <div>
      <label style={lbl}>{label}</label>
      <select className="select" value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
      </select>
    </div>
  )
}

const lbl = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '5px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px' }

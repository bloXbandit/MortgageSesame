import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export default function DpaPrograms() {
  const [programs, setPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [seedMsg, setSeedMsg] = useState(null)
  const [stateFilter, setStateFilter] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ active_only: 'false' })
      if (stateFilter) params.set('state', stateFilter)
      const data = await api.get(`/dpa/?${params}`)
      setPrograms(data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [stateFilter])

  const handleSeed = async () => {
    if (!window.confirm('Seed MD/DC DPA programs? Skips any that already exist.')) return
    setSeeding(true)
    setSeedMsg(null)
    try {
      const data = await api.post('/dpa/admin/seed-md-dc', {})
      setSeedMsg({ type: 'success', text: data.message })
      load()
    } catch {
      setSeedMsg({ type: 'error', text: 'Seed failed — check connection.' })
    }
    setSeeding(false)
  }

  const handleToggle = async (id, field, current) => {
    try {
      await api.patch(`/dpa/${id}`, { [field]: !current })
      load()
    } catch {}
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this program?')) return
    try {
      await api.delete(`/dpa/${id}`)
      load()
    } catch {}
  }

  const TYPE_LABELS = {
    grant: 'Grant', forgivable: 'Forgivable', deferred: 'Deferred',
    repayable: 'Repayable', second_lien: 'Second Lien',
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, color: 'var(--color-paper)', fontSize: '1.4rem', fontWeight: 800 }}>DPA Programs</h1>
          <p style={{ margin: '4px 0 0', color: '#666', fontSize: '0.875rem' }}>
            Manage down payment assistance programs shown on the public hub.
          </p>
        </div>
        <button
          onClick={handleSeed}
          disabled={seeding}
          style={{ padding: '9px 18px', background: seeding ? '#444' : '#2a2a2a', color: '#f5c87a', border: '1px solid #444', borderRadius: 6, fontWeight: 600, cursor: seeding ? 'not-allowed' : 'pointer', fontSize: '0.875rem', flexShrink: 0 }}
        >
          {seeding ? 'Seeding…' : '↻ Seed MD/DC Programs'}
        </button>
      </div>

      {seedMsg && (
        <div style={{
          marginBottom: 14, padding: '10px 14px', borderRadius: 7,
          background: seedMsg.type === 'success' ? '#14532d22' : '#7f1d1d22',
          color: seedMsg.type === 'success' ? '#4ade80' : '#f87171',
          fontSize: '0.875rem',
        }}>
          {seedMsg.text}
        </div>
      )}

      {/* State filter */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['', 'MD', 'DC'].map(s => (
          <button key={s}
            onClick={() => setStateFilter(s)}
            style={{
              padding: '5px 14px', borderRadius: 99,
              border: '1px solid', borderColor: stateFilter === s ? '#f5c87a' : '#444',
              background: stateFilter === s ? '#f5c87a22' : 'transparent',
              color: stateFilter === s ? '#f5c87a' : '#888',
              fontSize: '0.8rem', fontWeight: 500, cursor: 'pointer',
            }}
          >
            {s || 'All States'}
          </button>
        ))}
        {programs.length > 0 && <span style={{ marginLeft: 'auto', color: '#555', fontSize: '0.8rem', alignSelf: 'center' }}>{programs.length} programs</span>}
      </div>

      {loading ? (
        <div style={{ color: '#555' }}>Loading…</div>
      ) : programs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 0', color: '#555' }}>
          No programs yet.
          <button onClick={handleSeed} disabled={seeding} style={{ display: 'block', margin: '12px auto 0', padding: '9px 18px', background: '#f5c87a', color: '#1f1f1f', border: 'none', borderRadius: 6, fontWeight: 700, cursor: seeding ? 'not-allowed' : 'pointer' }}>
            {seeding ? 'Seeding…' : 'Seed MD/DC Programs'}
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {programs.map(p => (
            <div key={p.id} style={{
              background: '#2a2a2a', border: '1px solid #333', borderRadius: 8,
              padding: '14px 18px',
              opacity: p.is_active ? 1 : 0.5,
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                    <span style={{ background: '#333', color: '#aaa', padding: '1px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600 }}>
                      {p.state}{p.county ? ` · ${p.county}` : ' · Statewide'}
                    </span>
                    <span style={{ background: '#1e3a5f44', color: '#93c5fd', padding: '1px 8px', borderRadius: 99, fontSize: '0.7rem' }}>
                      {TYPE_LABELS[p.dpa_type] || p.dpa_type}
                    </span>
                    {p.is_featured && <span style={{ background: '#f5c87a22', color: '#f5c87a', padding: '1px 8px', borderRadius: 99, fontSize: '0.7rem' }}>Featured</span>}
                  </div>
                  <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.9375rem' }}>{p.program_name}</div>
                  {p.assistance_amount && (
                    <div style={{ color: '#f5c87a', fontWeight: 600, fontSize: '0.875rem', marginTop: 2 }}>{p.assistance_amount}</div>
                  )}
                  {p.administering_agency && (
                    <div style={{ color: '#666', fontSize: '0.78rem', marginTop: 2 }}>{p.administering_agency}</div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0, alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => handleToggle(p.id, 'is_active', p.is_active)}
                    style={{ padding: '4px 12px', background: 'transparent', color: p.is_active ? '#4ade80' : '#666', border: `1px solid ${p.is_active ? '#14532d' : '#444'}`, borderRadius: 5, cursor: 'pointer', fontSize: '0.78rem' }}
                  >
                    {p.is_active ? 'Active' : 'Inactive'}
                  </button>
                  <button
                    onClick={() => handleToggle(p.id, 'is_featured', p.is_featured)}
                    style={{ padding: '4px 12px', background: 'transparent', color: p.is_featured ? '#f5c87a' : '#666', border: `1px solid ${p.is_featured ? '#f5c87a44' : '#444'}`, borderRadius: 5, cursor: 'pointer', fontSize: '0.78rem' }}
                  >
                    {p.is_featured ? '★ Featured' : '☆ Feature'}
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    style={{ padding: '4px 10px', background: 'transparent', color: '#f87171', border: '1px solid #7f1d1d44', borderRadius: 5, cursor: 'pointer', fontSize: '0.78rem' }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 16, fontSize: '0.73rem', color: '#444', lineHeight: 1.5 }}>
        Programs are shown on the public DPA Hub page. Toggle Featured to surface them on the home page.
        Use "Seed MD/DC Programs" to load the built-in program database (idempotent — safe to re-run).
      </div>
    </div>
  )
}

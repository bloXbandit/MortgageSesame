import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Bell, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'

const SCORE_BADGE = {
  hot: 'badge-green', warm: 'badge-warm', long_term: 'badge-blue',
  bad_fit: 'badge-gray', compliance_risk: 'badge-red', unscored: 'badge-gray',
}

export default function Leads() {
  const [leads, setLeads] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/leads/').then(setLeads).catch(e => toast.error(e.message)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="fade-in" style={{ display: 'flex', gap: '20px', height: '100%' }}>
      {/* List */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Leads</h1>
            <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>All public intake submissions, AI-scored.</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['all', 'hot', 'warm', 'long_term', 'bad_fit'].map(s => (
              <button key={s} className="btn btn-ghost btn-sm" style={{ fontSize: '0.75rem' }}>
                {s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden', flex: 1 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th><th>Loan Type</th><th>State</th><th>Timeline</th><th>Score</th><th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>Loading...</td></tr>
              ) : leads.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#555', padding: '32px' }}>
                  No leads yet. Share your intake link at <code style={{ background: '#2a2a2a', padding: '1px 5px', borderRadius: '3px' }}>public-site/</code>
                </td></tr>
              ) : leads.map(lead => (
                <tr key={lead.id} onClick={() => setSelected(lead)} style={{ cursor: 'pointer' }}>
                  <td style={{ color: '#ddd', fontWeight: 500 }}>{lead.name || lead.email || 'Anonymous'}</td>
                  <td><span className="badge badge-gray">{lead.loan_interest_type || '—'}</span></td>
                  <td style={{ color: '#aaa' }}>{lead.state || '—'}</td>
                  <td style={{ color: '#aaa', fontSize: '0.8rem' }}>{lead.timeline?.replace(/_/g, ' ') || '—'}</td>
                  <td>
                    {lead.score ? (
                      <span className={`badge ${SCORE_BADGE[lead.score.label] || 'badge-gray'}`}>
                        {lead.score.label}
                      </span>
                    ) : <span className="badge badge-gray">unscored</span>}
                  </td>
                  <td style={{ color: '#666', fontSize: '0.8rem' }}>{new Date(lead.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="card fade-in" style={{ width: '320px', flexShrink: 0, alignSelf: 'flex-start', position: 'sticky', top: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>{selected.name || selected.email}</h3>
            <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '1rem' }}>×</button>
          </div>
          {selected.score && (
            <>
              <span className={`badge ${SCORE_BADGE[selected.score.label]}`} style={{ marginBottom: '12px' }}>
                {selected.score.label} · {selected.score.value?.toFixed(0)}/100
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <Info label="Recommended Product" val={selected.score.recommended_product} />
                <div>
                  <p style={infoLabel}>AI Summary</p>
                  <p style={{ fontSize: '0.8rem', color: '#bbb', lineHeight: 1.6, margin: 0 }}>{selected.score.summary}</p>
                </div>
              </div>
            </>
          )}
          {!selected.score && <p style={{ color: '#555', fontSize: '0.8rem' }}>No AI score available.</p>}
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--color-carbon-border)' }}>
            <p style={infoLabel}>Loan Type</p>
            <p style={{ margin: '0 0 10px', color: '#ccc', fontSize: '0.8rem' }}>{selected.loan_interest_type}</p>
            <p style={infoLabel}>State · Timeline</p>
            <p style={{ margin: 0, color: '#ccc', fontSize: '0.8rem' }}>{selected.state} · {selected.timeline?.replace(/_/g, ' ')}</p>
          </div>
        </div>
      )}
    </div>
  )
}

function Info({ label, val }) {
  if (!val) return null
  return (
    <div>
      <p style={infoLabel}>{label}</p>
      <p style={{ margin: 0, color: '#ccc', fontSize: '0.8rem' }}>{val}</p>
    </div>
  )
}

const infoLabel = { margin: '0 0 2px', fontSize: '0.65rem', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }

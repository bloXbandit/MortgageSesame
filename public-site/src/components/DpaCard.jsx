import { useState } from 'react'
import MicroIntake from './MicroIntake'

const TYPE_STYLES = {
  grant:       { bg: '#dcfce7', color: '#166534', label: 'Grant' },
  forgivable:  { bg: '#d1fae5', color: '#065f46', label: 'Forgivable' },
  deferred:    { bg: '#e0f2fe', color: '#075985', label: 'Deferred Loan' },
  repayable:   { bg: '#fef9c3', color: '#713f12', label: 'Repayable' },
  second_lien: { bg: '#ede9fe', color: '#5b21b6', label: 'Second Lien' },
}

export default function DpaCard({ program }) {
  const [expanded, setExpanded] = useState(false)
  const [showIntake, setShowIntake] = useState(false)
  const typeStyle = TYPE_STYLES[program.dpa_type] || TYPE_STYLES.deferred

  return (
    <>
      <div style={{
        background: '#fff',
        border: '1px solid #ede8e0',
        borderRadius: 10,
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div
          style={{ padding: '18px 20px 16px', cursor: 'pointer' }}
          onClick={() => setExpanded(e => !e)}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span style={{
                  background: typeStyle.bg, color: typeStyle.color,
                  padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600,
                }}>
                  {typeStyle.label}
                </span>
                {program.is_featured && (
                  <span style={{ background: '#fff3dc', color: '#92520b', padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600 }}>
                    Featured
                  </span>
                )}
                <span style={{ fontSize: '0.7rem', color: '#999', marginLeft: 'auto' }}>
                  {program.state}{program.county ? ` · ${program.county}` : ' · Statewide'}
                </span>
              </div>

              <h3 style={{ margin: '0 0 4px', fontSize: '1rem', fontWeight: 700, color: '#1f1f1f', lineHeight: 1.3 }}>
                {program.program_name}
              </h3>
              <p style={{ margin: 0, fontSize: '0.8125rem', color: '#666' }}>
                {program.administering_agency}
              </p>
            </div>

            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#1f1f1f' }}>
                {program.assistance_amount || '—'}
              </div>
              <div style={{ color: '#888', transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'none', marginTop: 4 }}>
                <svg width="14" height="8" viewBox="0 0 14 8" fill="none"><path d="M1 1l6 6 6-6" stroke="#999" strokeWidth="1.5" strokeLinecap="round"/></svg>
              </div>
            </div>
          </div>
        </div>

        {/* Expandable details */}
        {expanded && (
          <div style={{ padding: '0 20px 18px', borderTop: '1px solid #f0ece4' }}>
            <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
              {program.target_buyer && (
                <DetailRow label="Who qualifies" value={program.target_buyer} />
              )}
              {program.income_limit_notes && (
                <DetailRow label="Income limits" value={program.income_limit_notes} />
              )}
              {program.credit_score_min && (
                <DetailRow label="Min credit score" value={`${program.credit_score_min}+`} />
              )}
              {program.eligible_loan_types && (
                <DetailRow label="Eligible loans" value={program.eligible_loan_types} />
              )}
              {program.repayment_notes && (
                <DetailRow label="Repayment" value={program.repayment_notes} />
              )}
              {program.education_required && (
                <DetailRow label="Education" value="Homebuyer education course required" />
              )}
              {program.other_requirements && (
                <DetailRow label="Other requirements" value={program.other_requirements} />
              )}
              {program.notes && (
                <div style={{ marginTop: 4, padding: '10px 12px', background: '#fffbf5', borderRadius: 6, border: '1px solid #ede8e0', fontSize: '0.8125rem', color: '#555', lineHeight: 1.5 }}>
                  💡 {program.notes}
                </div>
              )}
            </div>

            <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                onClick={() => setShowIntake(true)}
                style={{
                  padding: '9px 16px',
                  background: '#1f1f1f',
                  color: '#f5c87a',
                  border: 'none',
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                }}
              >
                Am I eligible?
              </button>
              {program.program_url && (
                <a
                  href={program.program_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    padding: '9px 16px',
                    background: 'transparent',
                    color: '#555',
                    border: '1px solid #ddd',
                    borderRadius: 6,
                    fontWeight: 500,
                    fontSize: '0.8125rem',
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 5,
                  }}
                >
                  Official site ↗
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {showIntake && (
        <MicroIntake
          trigger={`Do I qualify for ${program.program_name}?`}
          contextNote={program.assistance_amount ? `Up to ${program.assistance_amount} available` : undefined}
          onClose={() => setShowIntake(false)}
        />
      )}
    </>
  )
}

function DetailRow({ label, value }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 8, alignItems: 'start' }}>
      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '0.04em', paddingTop: 1 }}>
        {label}
      </span>
      <span style={{ fontSize: '0.8125rem', color: '#333', lineHeight: 1.5 }}>
        {value}
      </span>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import RateTicker from '../components/RateTicker'
import MicroIntake from '../components/MicroIntake'

import { API, CALCOM, APP_1003, BANKER_NMLS, SERVICE_STATES } from '../config'

function StarRow({ count = 5 }) {
  return (
    <span style={{ display: 'inline-flex', gap: 2 }}>
      {Array.from({ length: count }).map((_, i) => (
        <svg key={i} width={18} height={18} viewBox="0 0 20 20" fill="#f5c87a">
          <path d="M10 1l2.39 4.84 5.34.78-3.87 3.77.91 5.32L10 13.27l-4.77 2.44.91-5.32L2.27 6.62l5.34-.78L10 1z"/>
        </svg>
      ))}
    </span>
  )
}

export default function CampaignPage() {
  const { slug }  = useParams()
  const [page, setPage]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [showIntake, setShowIntake] = useState(false)

  useEffect(() => {
    if (!slug) return
    fetch(`${API}/api/v1/campaigns/pages/public/${slug}`)
      .then(r => {
        if (r.status === 404) { setNotFound(true); return null }
        if (!r.ok) throw new Error('fetch error')
        return r.json()
      })
      .then(data => { if (data) setPage(data) })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fffbf5' }}>
      <div style={{ color: '#888', fontSize: '0.9rem' }}>Loading…</div>
    </div>
  )

  if (notFound) return (
    <div style={{ minHeight: '100vh', background: '#fffbf5', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 24px', textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: 16 }}>🏠</div>
        <h1 style={{ margin: '0 0 12px', color: '#1f1f1f', fontWeight: 900 }}>Page not found</h1>
        <p style={{ color: '#888', margin: '0 0 28px' }}>This campaign link may have expired or moved.</p>
        <Link to="/" style={{ padding: '11px 24px', background: '#1f1f1f', color: '#fff', borderRadius: 7, fontWeight: 600, textDecoration: 'none' }}>
          Go to Homepage →
        </Link>
      </div>
      <Footer />
    </div>
  )

  const steps = page.method_steps || []

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#fffbf5' }}>
      <RateTicker />
      <Nav />

      {/* ── Hero / Headline ─────────────────────────────────────────────── */}
      <section style={{ background: '#1f1f1f', padding: 'clamp(56px,9vw,96px) 24px', textAlign: 'center' }}>
        <div style={{ maxWidth: 760, margin: '0 auto' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 20,
            background: 'rgba(245,200,122,0.12)', color: '#f5c87a',
            padding: '4px 14px', borderRadius: 99, fontSize: '0.75rem', fontWeight: 600,
            border: '1px solid rgba(245,200,122,0.2)',
          }}>
            {SERVICE_STATES} · NMLS #{BANKER_NMLS}
          </span>
          <h1 style={{
            fontSize: 'clamp(1.9rem, 5vw, 3.2rem)',
            fontWeight: 900, color: '#fff', lineHeight: 1.1,
            letterSpacing: '-0.025em', margin: '0 0 18px',
          }}>
            {page.headline}
          </h1>
          {page.subheadline && (
            <p style={{ fontSize: 'clamp(1rem, 2vw, 1.15rem)', color: '#999', lineHeight: 1.65, margin: '0 0 36px', maxWidth: 600, marginLeft: 'auto', marginRight: 'auto' }}>
              {page.subheadline}
            </p>
          )}
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a
              href={CALCOM}
              target="_blank" rel="noopener noreferrer"
              style={{ padding: '13px 28px', background: '#f5c87a', color: '#1f1f1f', borderRadius: 7, fontWeight: 700, fontSize: '1rem', textDecoration: 'none' }}
            >
              Book a Free Call →
            </a>
            <button
              onClick={() => setShowIntake(true)}
              style={{ padding: '13px 24px', background: 'transparent', color: '#ccc', border: '1px solid #444', borderRadius: 7, fontWeight: 500, fontSize: '1rem', cursor: 'pointer' }}
            >
              See My Numbers
            </button>
          </div>
        </div>
      </section>

      {/* ── Lead / Opening ──────────────────────────────────────────────── */}
      {page.lead_opening && (
        <section style={{ padding: 'clamp(48px,7vw,80px) 24px', background: '#fffbf5' }}>
          <div style={{ maxWidth: 720, margin: '0 auto' }}>
            {page.lead_opening.split('\n').filter(Boolean).map((para, i) => (
              <p key={i} style={{ fontSize: '1.0625rem', color: '#333', lineHeight: 1.8, margin: '0 0 18px' }}>
                {para}
              </p>
            ))}
          </div>
        </section>
      )}

      {/* ── Villain ─────────────────────────────────────────────────────── */}
      {page.villain_paragraph && (
        <section style={{ padding: 'clamp(40px,6vw,64px) 24px', background: '#fff8ee', borderTop: '1px solid #ede8e0', borderBottom: '1px solid #ede8e0' }}>
          <div style={{ maxWidth: 720, margin: '0 auto' }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <span style={{ fontSize: '1.75rem', flexShrink: 0, marginTop: 2 }}>⚠️</span>
              <p style={{ margin: 0, fontSize: '1.0625rem', color: '#333', lineHeight: 1.8, fontStyle: 'italic' }}>
                {page.villain_paragraph}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ── Method Steps ────────────────────────────────────────────────── */}
      {steps.length > 0 && (
        <section style={{ padding: 'clamp(56px,8vw,88px) 24px', background: '#1f1f1f' }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 44 }}>
              <div style={{ fontSize: '0.7rem', color: '#f5c87a', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 8 }}>
                How It Works
              </div>
              <h2 style={{ margin: 0, fontSize: 'clamp(1.5rem, 3vw, 2.1rem)', fontWeight: 900, color: '#fff', letterSpacing: '-0.02em' }}>
                Here's exactly what happens next.
              </h2>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {steps.map((step, i) => (
                <div key={i} style={{
                  background: '#2a2a2a', border: '1px solid #333', borderRadius: 12,
                  padding: '24px 28px', display: 'flex', gap: 20, alignItems: 'flex-start',
                }}>
                  <div style={{
                    width: 36, height: 36, background: '#f5c87a', borderRadius: 8,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 900, fontSize: '0.9rem', color: '#1f1f1f', flexShrink: 0,
                  }}>
                    {step.step || i + 1}
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: '#fff', fontSize: '1rem', marginBottom: 6 }}>
                      {step.title}
                    </div>
                    <div style={{ color: '#888', fontSize: '0.9rem', lineHeight: 1.65 }}>
                      {step.body}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Proof block ─────────────────────────────────────────────────── */}
      {page.proof_block && (
        <section style={{ padding: 'clamp(48px,7vw,72px) 24px', background: '#fffbf5' }}>
          <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
            <StarRow count={5} />
            <div style={{ margin: '20px 0', background: '#fff', border: '1px solid #ede8e0', borderRadius: 12, padding: '28px 32px' }}>
              {page.proof_block.split('\n').filter(Boolean).map((line, i) => (
                <p key={i} style={{ margin: '0 0 10px', color: '#444', fontSize: '0.9375rem', lineHeight: 1.7, fontStyle: i === 0 ? 'italic' : 'normal' }}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Primary CTA ─────────────────────────────────────────────────── */}
      <section style={{ padding: 'clamp(56px,8vw,88px) 24px', background: '#141414', textAlign: 'center' }}>
        <div style={{ maxWidth: 560, margin: '0 auto' }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 'clamp(1.7rem, 3.5vw, 2.4rem)', fontWeight: 900, color: '#fff', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
            Ready to find out where you actually stand?
          </h2>
          <p style={{ margin: '0 0 32px', color: '#888', fontSize: '1rem', lineHeight: 1.65 }}>
            Free call. No credit pull. No paperwork. Just real answers.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
            <a
              href={CALCOM}
              target="_blank" rel="noopener noreferrer"
              style={{
                padding: '15px 40px', background: '#f5c87a', color: '#1f1f1f',
                borderRadius: 7, fontWeight: 700, fontSize: '1.0625rem',
                textDecoration: 'none', display: 'inline-block', width: '100%', maxWidth: 360, textAlign: 'center',
              }}
            >
              📅 Book a Free 15-Min Call
            </a>
            <button
              onClick={() => setShowIntake(true)}
              style={{
                padding: '13px 40px', background: 'transparent', color: '#ccc',
                border: '1px solid #3a3a3a', borderRadius: 7, fontWeight: 500,
                fontSize: '1rem', cursor: 'pointer', width: '100%', maxWidth: 360,
              }}
            >
              Get My Numbers Instead
            </button>
          </div>

          {/* Secondary — 1003 for already-sold prospects */}
          <div style={{ marginTop: 32, padding: '20px 24px', background: '#1e1e1e', borderRadius: 10, border: '1px solid #2a2a2a' }}>
            <p style={{ margin: '0 0 10px', color: '#555', fontSize: '0.8rem', lineHeight: 1.5 }}>
              Already spoke with us and ready to move forward?
            </p>
            <a
              href={APP_1003}
              target="_blank" rel="noopener noreferrer"
              style={{ color: '#f5c87a', fontSize: '0.875rem', fontWeight: 600, textDecoration: 'none' }}
            >
              Start your full mortgage application (1003) →
            </a>
          </div>

          <p style={{ margin: '24px 0 0', color: '#3a3a3a', fontSize: '0.7rem', lineHeight: 1.6 }}>
            {page.compliance_footer || `NMLS #${BANKER_NMLS} · ${SERVICE_STATES} · Equal Housing Opportunity · Not a commitment to lend. All loans subject to credit approval.`}
          </p>
        </div>
      </section>

      <Footer />

      {showIntake && (
        <MicroIntake
          trigger={page.headline || 'Get your real numbers'}
          contextNote="Free. No credit pull. I'll walk through your options."
          onClose={() => setShowIntake(false)}
        />
      )}
    </div>
  )
}

import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const links = [
  { to: '/rates',    label: 'Rates' },
  { to: '/homes',    label: 'Homes' },
  { to: '/dpa',      label: 'DPA Programs' },
  { to: '/learn',    label: 'Learn' },
]

const REALTOR_LINK = { to: '/realtors', label: 'For Realtors' }

export default function Nav() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  return (
    <nav style={{
      background: 'rgba(255,237,210,0.96)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid rgba(0,0,0,0.07)',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <div style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '0 24px',
        height: 58,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28, height: 28, background: '#1f1f1f', borderRadius: 6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
              <path d="M8 1L1 7H3V13H7V9H9V13H13V7H15L8 1Z" fill="#f5c87a"/>
            </svg>
          </div>
          <span style={{ fontWeight: 700, fontSize: '1rem', color: '#1f1f1f', letterSpacing: '-0.02em' }}>
            MortgageSesame
          </span>
        </Link>

        {/* Desktop links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} className="nav-desktop">
          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                fontSize: '0.875rem',
                fontWeight: 500,
                textDecoration: 'none',
                color: pathname.startsWith(l.to) ? '#1f1f1f' : '#555',
                background: pathname.startsWith(l.to) ? 'rgba(0,0,0,0.06)' : 'transparent',
                transition: 'all 0.15s',
              }}
            >
              {l.label}
            </Link>
          ))}
          {/* Realtor partner link — visually distinct */}
          <Link
            to={REALTOR_LINK.to}
            style={{
              padding: '5px 13px',
              borderRadius: 6,
              fontSize: '0.8125rem',
              fontWeight: 600,
              textDecoration: 'none',
              color: pathname.startsWith('/realtors') ? '#92520b' : '#c8860a',
              background: pathname.startsWith('/realtors') ? 'rgba(200,134,10,0.15)' : 'rgba(200,134,10,0.08)',
              border: '1px solid rgba(200,134,10,0.25)',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(200,134,10,0.18)'}
            onMouseLeave={e => e.currentTarget.style.background = pathname.startsWith('/realtors') ? 'rgba(200,134,10,0.15)' : 'rgba(200,134,10,0.08)'}
          >
            {REALTOR_LINK.label}
          </Link>
          <Link
            to="/get-started"
            style={{
              marginLeft: 8,
              padding: '7px 18px',
              background: '#1f1f1f',
              color: '#fff',
              borderRadius: 6,
              fontSize: '0.875rem',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'background 0.15s',
            }}
          >
            Get Started
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            display: 'none',
            background: 'none', border: 'none', cursor: 'pointer', padding: 8,
          }}
          className="nav-mobile-btn"
          aria-label="Toggle menu"
        >
          {open ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 4L16 16M16 4L4 16" stroke="#1f1f1f" strokeWidth="2" strokeLinecap="round"/></svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 6h14M3 10h14M3 14h14" stroke="#1f1f1f" strokeWidth="2" strokeLinecap="round"/></svg>
          )}
        </button>
      </div>

      {/* Mobile dropdown */}
      {open && (
        <div style={{
          background: '#ffedd2',
          borderTop: '1px solid rgba(0,0,0,0.07)',
          padding: '12px 24px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
        }}>
          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              style={{
                padding: '10px 14px',
                borderRadius: 6,
                fontSize: '0.9375rem',
                fontWeight: 500,
                textDecoration: 'none',
                color: '#1f1f1f',
              }}
            >
              {l.label}
            </Link>
          ))}
          <Link
            to={REALTOR_LINK.to}
            onClick={() => setOpen(false)}
            style={{
              padding: '10px 14px',
              borderRadius: 6,
              fontSize: '0.9375rem',
              fontWeight: 600,
              textDecoration: 'none',
              color: '#c8860a',
            }}
          >
            {REALTOR_LINK.label}
          </Link>
          <Link
            to="/get-started"
            onClick={() => setOpen(false)}
            style={{
              marginTop: 8,
              padding: '12px 14px',
              background: '#1f1f1f',
              color: '#fff',
              borderRadius: 6,
              fontSize: '0.9375rem',
              fontWeight: 600,
              textDecoration: 'none',
              textAlign: 'center',
            }}
          >
            Get Started
          </Link>
        </div>
      )}

      <style>{`
        @media (max-width: 640px) {
          .nav-desktop { display: none !important; }
          .nav-mobile-btn { display: block !important; }
        }
      `}</style>
    </nav>
  )
}

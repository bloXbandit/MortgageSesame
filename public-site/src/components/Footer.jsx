import { CALCOM, BANKER_NMLS, SERVICE_STATES } from '../config'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer style={{
      background: '#1a1a1a',
      color: '#888',
      padding: '40px 24px 28px',
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 32,
          marginBottom: 36,
        }}>
          {/* Brand */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <div style={{
                width: 26, height: 26, background: '#2a2a2a', borderRadius: 5,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <svg width="14" height="12" viewBox="0 0 14 12" fill="none">
                  <path d="M7 1L1 6H3V11H5V8H9V11H11V6H13L7 1Z" fill="#f5c87a"/>
                </svg>
              </div>
              <span style={{ color: '#fff', fontWeight: 700, fontSize: '0.9375rem' }}>MortgageSesame</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', lineHeight: 1.6 }}>
              Maryland & DC mortgage expertise for first-time buyers and investors.
            </p>
            <p style={{ margin: '8px 0 0', fontSize: '0.75rem', color: '#555' }}>
              NMLS #{BANKER_NMLS}
            </p>
          </div>

          {/* Navigate */}
          <div>
            <div style={{ color: '#ccc', fontWeight: 600, fontSize: '0.8rem', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Navigate
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {[
                ['/rates', 'Today\'s Rates'],
                ['/homes', 'Homes'],
                ['/dpa', 'DPA Programs'],
                ['/learn', 'Learn'],
                ['/get-started', 'Get Started'],
              ].map(([to, label]) => (
                <Link key={to} to={to} style={{ color: '#666', fontSize: '0.875rem', textDecoration: 'none', transition: 'color 0.15s' }}
                  onMouseEnter={e => e.target.style.color = '#ccc'}
                  onMouseLeave={e => e.target.style.color = '#666'}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Loan Types */}
          <div>
            <div style={{ color: '#ccc', fontWeight: 600, fontSize: '0.8rem', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Loan Types
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {[
                ['/learn/fha', 'FHA Loans'],
                ['/learn/conventional', 'Conventional'],
                ['/learn/va', 'VA Loans'],
                ['/learn/dscr', 'DSCR Investor'],
                ['/learn/heloc', 'HELOC'],
                ['/learn/dpa', 'Down Payment Help'],
              ].map(([to, label]) => (
                <Link key={to} to={to} style={{ color: '#666', fontSize: '0.875rem', textDecoration: 'none', transition: 'color 0.15s' }}
                  onMouseEnter={e => e.target.style.color = '#ccc'}
                  onMouseLeave={e => e.target.style.color = '#666'}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Contact */}
          <div>
            <div style={{ color: '#ccc', fontWeight: 600, fontSize: '0.8rem', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Contact
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <a
                href={CALCOM}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: '9px 14px',
                  background: '#f5c87a',
                  color: '#1f1f1f',
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  textDecoration: 'none',
                  display: 'inline-block',
                  textAlign: 'center',
                }}
              >
                Book a Free Consultation
              </a>
              <Link
                to="/get-started"
                style={{
                  padding: '8px 14px',
                  background: 'transparent',
                  color: '#888',
                  border: '1px solid #333',
                  borderRadius: 6,
                  fontWeight: 500,
                  fontSize: '0.8125rem',
                  textDecoration: 'none',
                  display: 'inline-block',
                  textAlign: 'center',
                }}
              >
                Quick Intake Form
              </Link>
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{
          borderTop: '1px solid #2a2a2a',
          paddingTop: 20,
        }}>
          <p style={{ margin: 0, fontSize: '0.7rem', lineHeight: 1.7, color: '#444' }}>
            All rates, loan scenarios, closing cost estimates, and down payment assistance program information
            displayed on this site are for <strong style={{ color: '#555' }}>educational purposes only</strong>.
            They do not constitute a rate lock, commitment to lend, or guarantee of program availability.
            Actual rates, costs, and eligibility depend on credit score, debt-to-income ratio, property type,
            lender fees, title costs, property taxes, homeowner's insurance, and other factors.
            DPA program details are subject to change — verify current requirements directly with the administering agency.
            Equal Housing Opportunity. NMLS #{BANKER_NMLS}. Licensed in Maryland and Washington DC.
          </p>
          <p style={{ margin: '10px 0 0', fontSize: '0.7rem', color: '#333' }}>
            © {new Date().getFullYear()} MortgageSesame · Equal Housing Lender
          </p>
        </div>
      </div>
    </footer>
  )
}

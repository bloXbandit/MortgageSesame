import { CALCOM, APP_1003 } from '../config'
import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Plus, ExternalLink, Download, Copy, QrCode, TrendingUp, X } from 'lucide-react'
import toast from 'react-hot-toast'

// Preset destinations for quick creation
const PRESETS = [
  { label: '📅 Book a Call',             url: CALCOM },
  { label: '🏠 Intake Form',             url: `${window.location.origin.replace('5174','5173')}/apply` },
  { label: '💰 DPA Programs',            url: `${window.location.origin.replace('5174','5173')}/dpa` },
  { label: '📋 Start Application (1003)',url: APP_1003 },
  { label: '🏡 Home Listings',           url: `${window.location.origin.replace('5174','5173')}/homes` },
]

export default function QRCodes() {
  const [links, setLinks]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm]         = useState({ label: '', destination_url: '', campaign_tag: '' })
  const [preview, setPreview]   = useState(null)   // { code, qr_image, tracking_url, label }
  const [imgLoading, setImgLoading] = useState(false)

  useEffect(() => {
    api.get('/track/links').then(setLinks).catch(e => toast.error(e.message)).finally(() => setLoading(false))
  }, [])

  const createLink = async () => {
    if (!form.label || !form.destination_url) { toast.error('Label and destination URL are required'); return }
    setCreating(true)
    try {
      const created = await api.post('/track/links', {
        label: form.label,
        destination_url: form.destination_url,
        campaign_tag: form.campaign_tag || undefined,
      })
      setLinks(prev => [created, ...prev])
      setForm({ label: '', destination_url: '', campaign_tag: '' })
      toast.success('QR link created')
      // Auto-open preview for the new link
      openPreview(created)
    } catch (e) { toast.error(e.message) }
    finally { setCreating(false) }
  }

  const openPreview = async (link) => {
    setPreview({ ...link, qr_image: null })
    setImgLoading(true)
    try {
      const data = await api.get(`/track/qr-image/${link.code}`)
      setPreview(data)
    } catch { toast.error('Could not load QR image') }
    finally { setImgLoading(false) }
  }

  const copyTrackingUrl = (url) => {
    navigator.clipboard.writeText(url).then(() => toast.success('Copied!'))
  }

  const downloadQR = (dataUri, label) => {
    if (!dataUri) return
    const a = document.createElement('a')
    a.href = dataUri
    a.download = `qr-${label.toLowerCase().replace(/\s+/g, '-')}.png`
    a.click()
  }

  return (
    <div className="fade-in" style={{ display: 'flex', gap: '20px', height: '100%', minHeight: 0 }}>

      {/* ── Left: form + list ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>QR Codes</h1>
          <p style={{ margin: 0, color: '#888', fontSize: '0.875rem' }}>
            Trackable links for business cards, flyers, yard signs, and mailers. Every scan is logged.
          </p>
        </div>

        {/* Create form */}
        <div className="card" style={{ padding: '16px' }}>
          <p style={{ margin: '0 0 12px', fontSize: '0.7rem', fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
            Create New QR Link
          </p>

          {/* Quick presets */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {PRESETS.map(p => (
              <button
                key={p.label}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                onClick={() => setForm(f => ({ ...f, label: p.label.replace(/^[^\w]+/, '').trim(), destination_url: p.url }))}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
            <div>
              <label style={labelSt}>Label (what it is)</label>
              <input
                className="input"
                placeholder="Business Card — Front"
                value={form.label}
                onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              />
            </div>
            <div>
              <label style={labelSt}>Campaign Tag (optional)</label>
              <input
                className="input"
                placeholder="q1_mailer, open_house_may"
                value={form.campaign_tag}
                onChange={e => setForm(f => ({ ...f, campaign_tag: e.target.value }))}
              />
            </div>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={labelSt}>Destination URL</label>
            <input
              className="input"
              value={form.destination_url}
              onChange={e => setForm(f => ({ ...f, destination_url: e.target.value }))}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={createLink}
            disabled={creating}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={14} />
            {creating ? 'Creating…' : 'Create QR Link'}
          </button>
        </div>

        {/* Links table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', flex: 1, minHeight: 0 }}>
          <div style={{ overflowY: 'auto', height: '100%' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Destination</th>
                  <th style={{ textAlign: 'center' }}>Scans</th>
                  <th>Last Scan</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} style={{ textAlign: 'center', color: '#999', padding: '32px' }}>Loading…</td></tr>
                ) : links.length === 0 ? (
                  <tr><td colSpan={5} style={{ textAlign: 'center', color: '#999', padding: '32px' }}>
                    No QR links yet — create your first one above.
                  </td></tr>
                ) : links.map(link => (
                  <tr key={link.id}
                    onClick={() => openPreview(link)}
                    style={{ cursor: 'pointer', background: preview?.code === link.code ? 'rgba(245,200,122,0.06)' : undefined }}
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <QrCode size={13} color="#f5c87a" />
                        <span style={{ fontWeight: 500, color: '#ddd', fontSize: '0.875rem' }}>{link.label}</span>
                        {link.campaign_id && (
                          <span className="badge badge-gray" style={{ fontSize: '0.65rem' }}>{link.campaign_id}</span>
                        )}
                      </div>
                    </td>
                    <td style={{ color: '#888', fontSize: '0.8rem', maxWidth: '180px' }}>
                      <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {link.destination_url}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: '4px',
                        fontWeight: 700, fontSize: '0.875rem',
                        color: link.scan_count > 0 ? '#f5c87a' : '#444',
                      }}>
                        {link.scan_count > 0 && <TrendingUp size={11} />}
                        {link.scan_count || 0}
                      </span>
                    </td>
                    <td style={{ color: '#999', fontSize: '0.8rem' }}>
                      {link.last_scanned_at ? new Date(link.last_scanned_at).toLocaleDateString() : '—'}
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                        onClick={() => copyTrackingUrl(link.tracking_url || `${window.location.origin.replace('5174','8000')}/r/${link.code}`)}
                      >
                        <Copy size={11} /> Copy URL
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Right: QR preview panel ───────────────────────────────────────── */}
      {preview && (
        <div className="fade-in" style={{
          width: '300px', flexShrink: 0,
          display: 'flex', flexDirection: 'column', gap: '12px',
        }}>
          <div className="card" style={{ padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#ddd' }}>{preview.label}</span>
              <button onClick={() => setPreview(null)} style={{ background: 'none', border: 'none', color: '#999', cursor: 'pointer' }}>
                <X size={16} />
              </button>
            </div>

            {/* QR Image */}
            <div style={{
              background: '#2a2a2a', borderRadius: '8px', padding: '16px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '14px', minHeight: '200px',
            }}>
              {imgLoading ? (
                <div style={{ color: '#999', fontSize: '0.8rem' }}>Generating…</div>
              ) : preview.qr_image ? (
                <img src={preview.qr_image} alt="QR Code" style={{ width: '100%', maxWidth: '200px', height: 'auto' }} />
              ) : (
                <QrCode size={80} color="#ccc" />
              )}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
              <button
                className="btn btn-primary"
                style={{ flex: 1, gap: '5px', fontSize: '0.78rem', justifyContent: 'center' }}
                onClick={() => downloadQR(preview.qr_image, preview.label || preview.code)}
                disabled={!preview.qr_image}
              >
                <Download size={13} /> Download PNG
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => copyTrackingUrl(preview.tracking_url)}
                style={{ gap: '5px', fontSize: '0.78rem' }}
              >
                <Copy size={12} /> URL
              </button>
            </div>

            {/* Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <DetailRow label="Tracking URL">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <code style={{ fontSize: '0.7rem', color: '#f5c87a', wordBreak: 'break-all' }}>
                    {preview.tracking_url}
                  </code>
                  <a href={preview.tracking_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink size={11} color="#666" />
                  </a>
                </div>
              </DetailRow>
              <DetailRow label="Destination">
                <span style={{ fontSize: '0.75rem', color: '#888', wordBreak: 'break-all' }}>
                  {preview.destination_url}
                </span>
              </DetailRow>
            </div>
          </div>

          {/* Instructions card */}
          <div className="card" style={{ padding: '14px', background: 'rgba(245,200,122,0.03)' }}>
            <p style={{ margin: '0 0 8px', fontSize: '0.65rem', fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
              How to use
            </p>
            <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {[
                'Download the PNG and drop it into Canva, Word, or any design tool',
                'Print on business cards, door hangers, yard signs, or postcards',
                'Every scan is tracked here — you\'ll see totals in real time',
                'Point it at your booking link for the highest ROI',
              ].map((tip, i) => (
                <li key={i} style={{ fontSize: '0.75rem', color: '#888', lineHeight: 1.5 }}>{tip}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, children }) {
  return (
    <div>
      <p style={{ margin: '0 0 2px', fontSize: '0.62rem', color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>{label}</p>
      {children}
    </div>
  )
}

const labelSt = {
  display: 'block', fontSize: '0.72rem', color: '#777', marginBottom: '5px', fontWeight: 500,
}

import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Sparkles, Copy, CheckCircle, Clock } from 'lucide-react'
import toast from 'react-hot-toast'

const PLATFORMS = ['tiktok', 'instagram_reel', 'instagram_carousel', 'facebook', 'linkedin', 'google_business', 'email_snippet']
const CATEGORIES = ['dpa_myths', 'fha_education', 'heloc_strategy', 'dscr_investor', 'refi_triggers', 'underwriting_mistakes', 'credit_readiness', 'realtor_education', 'open_house', 'market_update']

export default function ContentStudio() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [form, setForm] = useState({ platform: 'tiktok', category: 'dpa_myths', product_id: '' })
  const [products, setProducts] = useState([])
  const [tab, setTab] = useState('library')

  const load = async () => {
    setLoading(true)
    try {
      const [postsData, prodsData] = await Promise.all([
        api.get('/content/posts'),
        api.get('/products/'),
      ])
      setPosts(postsData)
      setProducts(prodsData)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const generate = async () => {
    setGenerating(true)
    try {
      const result = await api.post('/content/generate', form)
      toast.success('Content generated — review before publishing')
      setPosts(p => [result.post, ...p])
      setTab('library')
      if (result.compliance.flags.length > 0) {
        toast(`⚠️ ${result.compliance.flags.length} compliance flag(s) — review carefully`, { duration: 5000 })
      }
    } catch (e) {
      toast.error(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const approve = async (postId, action) => {
    try {
      await api.patch(`/content/posts/${postId}/approve`, { action })
      toast.success(`Post ${action}d`)
      load()
    } catch (e) {
      toast.error(e.message)
    }
  }

  const copy = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied!')
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.25rem', fontWeight: 700 }}>Content Studio</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>AI-generated posts ready for your review before publishing.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['library', 'generate'].map(t => (
            <button key={t} className={`btn btn-sm ${tab === t ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(t)}>
              {t === 'generate' ? <><Sparkles size={12} /> Generate</> : 'Library'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'generate' && (
        <div className="card fade-in" style={{ maxWidth: '560px' }}>
          <h3 style={{ margin: '0 0 20px', fontSize: '0.9rem', fontWeight: 600 }}>Generate New Post</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={labelStyle}>Platform</label>
              <select className="select" value={form.platform} onChange={e => setForm(f => ({ ...f, platform: e.target.value }))}>
                {PLATFORMS.map(p => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Content Category</label>
              <select className="select" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Product Context (optional)</label>
              <select className="select" value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))}>
                <option value="">No specific product</option>
                {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" onClick={generate} disabled={generating} style={{ width: 'fit-content' }}>
              <Sparkles size={14} /> {generating ? 'Generating...' : 'Generate Post'}
            </button>
          </div>
        </div>
      )}

      {tab === 'library' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {loading ? (
            <p style={{ color: '#555', padding: '20px' }}>Loading...</p>
          ) : posts.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
              <Sparkles size={28} color="#555" style={{ marginBottom: '12px' }} />
              <p style={{ color: '#ccc', margin: '0 0 4px', fontWeight: 600 }}>No posts yet</p>
              <p style={{ color: '#555', fontSize: '0.8125rem', margin: 0 }}>Click "Generate" to create your first AI post.</p>
            </div>
          ) : posts.map(post => (
            <PostCard key={post.id} post={post} onApprove={approve} onCopy={copy} />
          ))}
        </div>
      )}
    </div>
  )
}

function PostCard({ post, onApprove, onCopy }) {
  const [open, setOpen] = useState(false)
  const statusColors = {
    pending: 'badge-warm',
    approved: 'badge-green',
    rejected: 'badge-red',
    scheduled: 'badge-blue',
    published: 'badge-green',
    needs_edit: 'badge-gray',
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: '14px', padding: '14px 18px', cursor: 'pointer',
      }}>
        <span className="badge badge-gray">{post.platform?.replace(/_/g, ' ')}</span>
        <span className="badge badge-gray" style={{ opacity: 0.7 }}>{post.category?.replace(/_/g, ' ')}</span>
        <p style={{ flex: 1, margin: 0, fontSize: '0.875rem', color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {post.hook || 'No hook'}
        </p>
        <span className={`badge ${statusColors[post.approval_status] || 'badge-gray'}`}>{post.approval_status}</span>
        {post.is_fictional_example && <span className="badge badge-gray">Example</span>}
      </div>

      {open && (
        <div style={{ borderTop: '1px solid var(--color-carbon-border)', padding: '16px 18px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
            {[
              { label: 'Hook', val: post.hook },
              { label: 'Caption', val: post.caption },
              { label: 'Script', val: post.script },
              { label: 'CTA', val: post.cta },
              { label: 'Visual Concept', val: post.visual_concept },
              { label: 'Image Prompt', val: post.image_prompt },
              { label: 'Voiceover Script', val: post.voiceover_script },
              { label: 'Compliance Notes', val: post.compliance_notes },
            ].filter(f => f.val).map(({ label, val }) => (
              <div key={label}>
                <p style={{ margin: '0 0 4px', fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</p>
                <div style={{ background: 'var(--color-carbon-mid)', borderRadius: '6px', padding: '10px 12px', position: 'relative' }}>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#ccc', lineHeight: 1.6 }}>{val}</p>
                  <button onClick={() => onCopy(val)} style={{
                    position: 'absolute', top: '6px', right: '6px',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#555',
                    padding: '2px',
                  }}>
                    <Copy size={11} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {post.approval_status === 'pending' && (
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn btn-primary btn-sm" onClick={() => onApprove(post.id, 'approve')}>
                <CheckCircle size={12} /> Approve
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => onApprove(post.id, 'needs_edit')}>
                Needs Edit
              </button>
              <button className="btn btn-danger btn-sm" onClick={() => onApprove(post.id, 'reject')}>
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: '0.7rem', color: '#888', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.6px' }

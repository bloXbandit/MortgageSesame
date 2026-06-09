# MortgageSesame — Content Video Pipeline Setup

Complete wiring guide for the AI content generation, video production, and social publishing pipeline.

---

## Table of Contents

1. [How the Pipeline Works](#1-how-the-pipeline-works)
2. [ENV Variables — Master Reference](#2-env-variables--master-reference)
3. [Platform Setup — Step by Step](#3-platform-setup--step-by-step)
   - [ElevenLabs (Voiceover)](#31-elevenlabs--voiceover)
   - [HeyGen (Avatar Video)](#32-heygen--avatar-video)
   - [Creatomate (Assembly / Final Render)](#33-creatomate--assembly--final-render)
   - [Meta Graph API (Instagram Reels + Facebook)](#34-meta-graph-api--instagram-reels--facebook)
   - [TikTok Content Posting API](#35-tiktok-content-posting-api-v2)
   - [LinkedIn Marketing API](#36-linkedin-marketing-api)
4. [Agent API Call Sequence](#4-agent-api-call-sequence)
5. [Cost Reference](#5-cost-reference)
6. [Safe Dev Mode (No Real Posts)](#6-safe-dev-mode-no-real-posts)
7. [Going Live Checklist](#7-going-live-checklist)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. How the Pipeline Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — Generate Script                                              │
│  POST /api/v1/content/generate                                          │
│  → OpenAI generates: hook, script, caption, CTA, hashtags,             │
│    visual_concept, image_prompt, voiceover_script, compliance_notes     │
│  → ScriptTemplate records (from DB) are injected into system prompt     │
│  → SocialPost saved  pipeline_stage = "script_only"                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  STAGE 2 — Generate Voiceover                                           │
│  POST /api/v1/content/posts/{id}/generate-voice                         │
│  → ElevenLabs TTS on voiceover_script                                  │
│  → MP3 saved to MEDIA_STORAGE_PATH/{asset_id}.mp3                      │
│  → MediaAsset record created, served at /media/{asset_id}.mp3          │
│  → pipeline_stage = "voice_ready"                                       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  STAGE 3 — Generate Avatar Video                                        │
│  POST /api/v1/content/posts/{id}/generate-video                         │
│  → HeyGen v2 API: avatar lip-syncs to voiceover                        │
│  → Returns provider_id (video_id); status = "video_processing"         │
│  GET /api/v1/content/posts/{id}/video-status?provider_id=...            │
│  → Polls HeyGen until status = completed                               │
│  → MediaAsset created with video URL                                   │
│  → pipeline_stage = "video_ready"                                       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  STAGE 4 — Approval Queue                                               │
│  → ApprovalQueue item created (if auto_queue=true)                      │
│  → You review in ContentStudio → Library tab                           │
│  → Approve / Needs Edit / Reject                                        │
│  → Only APPROVED posts can be published                                 │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│  STAGE 5 — Publish                                                      │
│  POST /api/v1/content/posts/{id}/publish                                │
│  → Finds video MediaAsset for post                                     │
│  → Calls platform publisher (Instagram / TikTok / Facebook / LinkedIn) │
│  → SocialPost.published_at set, pipeline_stage = "published"           │
│  → external_post_id saved for tracking                                  │
└─────────────────────────────────────────────────────────────────────────┘

  ONE-SHOT shortcut (stages 2+3+queue in a single call):
  POST /api/v1/content/posts/{id}/pipeline
  POST /api/v1/agent/content-pipeline   (agent-triggered, creates post too)
```

### Mode Switches

| Variable | `mock` (default) | `live` |
|---|---|---|
| `CAMPAIGN_VIDEO_PROVIDER` | No HeyGen calls, returns fake video_id | Real HeyGen API calls |
| `CONTENT_PUBLISH_MODE` | No platform posts, returns mock external_post_id | Real Meta/TikTok/LinkedIn posts |

**Always start in mock mode** and only flip to live after confirming the pipeline runs end-to-end.

---

## 2. ENV Variables — Master Reference

Copy `backend/.env.example` to `backend/.env` and fill in the values below.

### Core App

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | SQLite (dev) or PostgreSQL (prod) connection string |
| `SECRET_KEY` | ✅ | JWT signing key — run `openssl rand -hex 32` |
| `BACKEND_URL` | ✅ | Public URL of this API server. **Must be publicly reachable for video publishing** (Meta and TikTok pull video by URL). Use ngrok or Render for local dev. |
| `APP_ENV` | ✅ | `development` or `production` |

### AI Content Generation

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI key for script generation (gpt-4o) |
| `AI_MODEL` | — | Default: `gpt-4o` |
| `AI_FAST_MODEL` | — | Default: `gpt-4o-mini` (used for lightweight tasks) |

### ElevenLabs — Voiceover

| Variable | Required | Description |
|---|---|---|
| `ELEVENLABS_API_KEY` | ✅ | Found at elevenlabs.io → Profile → API Key |
| `ELEVENLABS_VOICE_ID` | ✅ | Your cloned voice ID — see §3.1 below |

### HeyGen — Avatar Video

| Variable | Required for video | Description |
|---|---|---|
| `HEYGEN_API_KEY` | ✅ | HeyGen dashboard → Settings → API Key |
| `HEYGEN_AVATAR_ID` | ✅ | Your Instant Avatar ID — see §3.2 below |
| `HEYGEN_VOICE_ID` | — | HeyGen built-in voice ID (optional; leave blank if using ElevenLabs audio) |
| `HEYGEN_ELEVENLABS_VOICE_ID` | — | Your ElevenLabs voice ID used inside HeyGen for voice cloning |
| `HEYGEN_TEST_MODE` | — | `true` = skip real API calls, return mock. Default: `true` |
| `CAMPAIGN_VIDEO_PROVIDER` | — | `mock` (default) or `heygen` |

### Creatomate — Video Assembly

| Variable | Required for assembly | Description |
|---|---|---|
| `CREATOMATE_API_KEY` | ✅ | Creatomate dashboard → API → API Key |
| `CREATOMATE_TEMPLATE_ID_TIKTOK` | ✅ | Creatomate template ID for 9:16 TikTok format |
| `CREATOMATE_TEMPLATE_ID_REELS` | ✅ | Creatomate template ID for Instagram Reels |
| `CREATOMATE_TEMPLATE_ID_LINKEDIN` | ✅ | Creatomate template ID for LinkedIn 16:9 format |

### Meta Graph API — Instagram Reels + Facebook

| Variable | Required for publishing | Description |
|---|---|---|
| `META_ACCESS_TOKEN` | ✅ | Long-lived Page token (60-day expiry) — see §3.4 |
| `META_IG_USER_ID` | ✅ | Numeric Instagram Business Account / Creator ID |
| `META_PAGE_ID` | ✅ | Numeric Facebook Page ID |

### TikTok Content Posting API

| Variable | Required for publishing | Description |
|---|---|---|
| `TIKTOK_ACCESS_TOKEN` | ✅ | OAuth 2.0 user access token — see §3.5 |
| `TIKTOK_OPEN_ID` | ✅ | TikTok user identifier returned in OAuth token response |

### LinkedIn Marketing API

| Variable | Required for publishing | Description |
|---|---|---|
| `LINKEDIN_ACCESS_TOKEN` | ✅ | OAuth 2.0 3-legged token with `w_member_social` scope |
| `LINKEDIN_PERSON_ID` | ✅ | Full URN string, e.g. `urn:li:person:XXXXXXXXX` |

### Media Storage

| Variable | Default | Description |
|---|---|---|
| `MEDIA_STORAGE_PATH` | `./media` | Local directory for generated MP3/MP4 assets. FastAPI serves it at `/media/`. |

### Content Modes

| Variable | Default | Description |
|---|---|---|
| `CAMPAIGN_VIDEO_PROVIDER` | `mock` | `mock` or `heygen` |
| `CONTENT_PUBLISH_MODE` | `mock` | `mock` or `live` |

### Cost Tracking (Content Agent)

| Variable | Default | Description |
|---|---|---|
| `COST_HEYGEN_PER_MIN` | `0.10` | Estimated cost per minute of generated HeyGen video (USD) |
| `COST_CREATOMATE_RENDER` | `0.05` | Estimated cost per Creatomate render (USD) |

---

## 3. Platform Setup — Step by Step

### 3.1 ElevenLabs — Voiceover

1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Go to **Voice Lab → Add Voice → Instant Voice Clone**
3. Upload 2-3 minutes of clean audio of yourself (low background noise, natural speech pace)
4. Once created, click the voice → copy the **Voice ID** (long hex string)
5. Paste into `ELEVENLABS_VOICE_ID` in `.env`
6. Copy your **API Key** from Profile → API Key → paste into `ELEVENLABS_API_KEY`

> **Tip:** ElevenLabs "Creator" plan ($22/month) gives 100k characters/month — enough for ~200 short scripts.

---

### 3.2 HeyGen — Avatar Video

**Record your Instant Avatar:**

1. Sign up at [heygen.com](https://www.heygen.com)
2. Go to **Studio → Avatars → Create Avatar → Instant Avatar**
3. Record a 2-minute consent video (HeyGen requires you to read a specific consent statement on camera)
4. Submit for processing (usually 10-30 minutes)
5. Once approved, click your avatar → copy the **Avatar ID** from the URL or settings panel
6. Paste into `HEYGEN_AVATAR_ID`

**API Key:**

1. HeyGen Dashboard → **Settings → API** → copy key
2. Paste into `HEYGEN_API_KEY`

**Voice in HeyGen:**

- Option A: Let HeyGen use its own voice — set `HEYGEN_VOICE_ID` to a HeyGen voice ID
- Option B: Use your ElevenLabs cloned voice inside HeyGen — set `HEYGEN_ELEVENLABS_VOICE_ID` to your ElevenLabs voice ID and leave `HEYGEN_VOICE_ID` blank. HeyGen will lip-sync the avatar to your ElevenLabs audio.
- Option C: Pre-generate audio with ElevenLabs (Stage 2), then pass the audio URL to HeyGen — the pipeline does this automatically when `voiceover_script` is set.

**Test Mode:**

Set `HEYGEN_TEST_MODE=true` (default) while setting up. The pipeline returns a fake `video_id` without using API credits. Flip to `false` only when you're ready to consume real renders.

> **Pricing:** HeyGen Creator ($29/month) includes ~60 minutes of video/month. Each mortgage video is ~60-90 seconds. Plan for ~40 posts/month.

---

### 3.3 Creatomate — Assembly / Final Render

Creatomate layers your HeyGen avatar video with branded lower-thirds, captions, and platform-specific frames.

**Setup:**

1. Sign up at [creatomate.com](https://creatomate.com)
2. Go to **Templates → New Template**
3. Build three templates (one per platform):
   - **TikTok/Reels** (9:16, 1080×1920): Video layer for avatar clip, text layer for captions, logo overlay, CTA text at bottom
   - **LinkedIn** (16:9, 1920×1080 or 1:1): Video layer, title text, subtitle, logo
4. For each template, add these **dynamic elements** (variable names must match exactly):
   - `video_url` — the HeyGen output video
   - `caption_text` — overlay subtitle/captions
   - `hook_text` — opening hook text card
   - `cta_text` — call-to-action overlay
   - `logo_url` — your brand logo (can be a static asset URL)
5. Click **Publish** → copy the **Template ID** (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
6. Paste each template ID into the corresponding ENV var

**API Key:**

API page → copy key → `CREATOMATE_API_KEY`

> **Pricing:** Creatomate Starter ($19/month) includes 100 renders/month.

---

### 3.4 Meta Graph API — Instagram Reels + Facebook

**This is the same token for both platforms.**

**Step 1 — Create a Meta Developer App:**
1. Go to [developers.facebook.com](https://developers.facebook.com)
2. **My Apps → Create App → Business → Next**
3. App type: **Business**, connect your Facebook Page
4. Add products: **Instagram Graph API** + **Pages API**

**Step 2 — Request Permissions:**
In App Dashboard → App Review → Permissions, request:
- `pages_manage_posts`
- `instagram_content_publish`
- `instagram_basic`
- `pages_read_engagement`

> For personal posting (your own account/page), you can use in **development mode** without App Review. App Review is only required to post on behalf of other users.

**Step 3 — Generate a Long-Lived Token:**
1. Go to **Graph API Explorer** (tools.developers.facebook.com/tools/explorer)
2. Select your app and your **Facebook Page** (not personal profile)
3. Add the permissions listed above → **Generate Access Token** → authorize
4. Copy the **short-lived token** (1 hour)
5. Exchange for a long-lived token (60 days):
   ```
   GET https://graph.facebook.com/v19.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={app_id}
     &client_secret={app_secret}
     &fb_exchange_token={short_lived_token}
   ```
6. Paste the resulting long-lived token into `META_ACCESS_TOKEN`

> ⚠️ **Tokens expire in 60 days.** Set a calendar reminder to refresh. The pipeline will throw `401` errors when the token expires.

**Step 4 — Get Your Instagram User ID:**
```
GET https://graph.facebook.com/v19.0/{page_id}?fields=instagram_business_account&access_token={token}
```
The `id` field in the response is your `META_IG_USER_ID`.

**Step 5 — Get Your Facebook Page ID:**
Go to your Facebook Page → **Settings** → the Page ID is shown in the URL or About section.

---

### 3.5 TikTok Content Posting API v2

> ⚠️ **TikTok does NOT auto-approve Content Posting API access.** You must apply and wait for review (typically 1-2 weeks). Plan ahead.

**Step 1 — Create a TikTok Developer App:**
1. Go to [developers.tiktok.com](https://developers.tiktok.com)
2. **Manage Apps → Create App**
3. Select **Content Posting API** as a product
4. Fill out the use case form honestly: "Automated posting of mortgage educational content for a licensed mortgage banker (NMLS #1454510)"
5. Submit for review

**Step 2 — Configure OAuth:**
While waiting for approval, set up your redirect URI:
- Add `https://your-backend-url.com/api/v1/auth/tiktok/callback` as an allowed redirect URI
- Note your **Client Key** and **Client Secret**

**Step 3 — Get an Access Token (after approval):**
TikTok uses OAuth 2.0 with PKCE. You'll need to:
1. Direct your TikTok account to the authorization URL
2. User authorizes → TikTok redirects to your callback with a `code`
3. Exchange `code` for `access_token` and `open_id`

You can do this one-time manually using the TikTok API Explorer in the developer portal.

**Step 4 — Paste credentials:**
- `TIKTOK_ACCESS_TOKEN` — the access token
- `TIKTOK_OPEN_ID` — the `open_id` from the token response (unique identifier for your creator account)

> TikTok access tokens expire in 24 hours (or 30 days for refresh tokens). For sustained use, implement the token refresh flow.

---

### 3.6 LinkedIn Marketing API

**Step 1 — Create a LinkedIn Developer App:**
1. Go to [developer.linkedin.com](https://developer.linkedin.com)
2. **Create App** → attach to your LinkedIn Company Page
3. Request the **Share on LinkedIn** product (gives `w_member_social` permission)
4. Also request **Sign In with LinkedIn using OpenID Connect** for `openid`, `profile`, `email`

**Step 2 — OAuth 2.0 Three-Legged Flow:**
LinkedIn doesn't have a simple API key — you need a user OAuth token. To do this once for your own account:

1. Construct the authorization URL:
   ```
   https://www.linkedin.com/oauth/v2/authorization
     ?response_type=code
     &client_id={your_client_id}
     &redirect_uri={your_redirect_uri}
     &scope=w_member_social%20openid%20profile
   ```
2. Open it in your browser while logged into your LinkedIn account
3. Authorize → copy the `code` from the redirect URL
4. Exchange for a token:
   ```bash
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d "grant_type=authorization_code" \
     -d "code={code}" \
     -d "client_id={client_id}" \
     -d "client_secret={client_secret}" \
     -d "redirect_uri={redirect_uri}"
   ```
5. Copy `access_token` → paste into `LINKEDIN_ACCESS_TOKEN`

> LinkedIn tokens expire in 60 days. Refresh tokens last up to 1 year if your app is approved for them.

**Step 3 — Get Your Person URN:**
```bash
curl -H "Authorization: Bearer {access_token}" \
     https://api.linkedin.com/v2/me
```
Copy the `id` field — it looks like `urn:li:person:XXXXXXXXX`. Paste the **full URN string** into `LINKEDIN_PERSON_ID`.

---

## 4. Agent API Call Sequence

The agent (`POST /api/v1/agent/*`) can orchestrate the full pipeline autonomously.

### Full Automated Run (script + voice + video + queue)

```bash
# 1. Run the full content pipeline for a new post
POST /api/v1/agent/content-pipeline
{
  "platform": "tiktok",
  "category": "dpa_myths",
  "generate_voice": true,
  "generate_video": true,
  "auto_queue": true
}

# Response includes post_id, pipeline_stage, media_assets[]
```

### Performance Analysis + Decisions

```bash
# 2. Analyze content performance + get agent decisions
POST /api/v1/agent/analyze-performance
{
  "days": 30
}

# Response includes:
# - overall_approval_rate, cost_estimate_usd
# - decisions[]: [{type: "pause"|"adjust"|"scale"|"review", category, platform, reason}]
# - by_category{}: per-category stats
# - recommendation: plain English summary
```

### Publish an Approved Post

```bash
# 3. Publish (post must be APPROVED status first)
POST /api/v1/agent/publish-content
{
  "post_id": "abc-123",
  "platform": "tiktok"
}
```

### One-Shot Pipeline via Content Router

```bash
# Alternative: voice + video + queue in one call directly
POST /api/v1/content/posts/{id}/pipeline
{
  "generate_voice": true,
  "generate_video": false,   # true = submit to HeyGen immediately
  "auto_queue": true
}
```

### Decision Thresholds (Content Agent)

The agent uses these thresholds when analyzing performance:

| Decision | Condition | Action |
|---|---|---|
| `pause` | approval_rate < 35% AND n ≥ 2 | Stop generating this category/platform combo |
| `adjust` | approval_rate < 50% AND n ≥ 2 | Flag for script template review |
| `scale` | approval_rate ≥ 75% AND n ≤ 3 | Generate more content in this category |
| `review` | approval_rate ≥ 75% AND publish_rate < 30% | Good content stuck in queue — push to publish |

---

## 5. Cost Reference

Estimated monthly cost to run at ~40 posts/month across TikTok, Instagram, LinkedIn:

| Item | Unit Cost | ~40 posts/mo | Notes |
|---|---|---|---|
| OpenAI gpt-4o (scripts) | ~$0.05/script | ~$2 | Very cheap |
| ElevenLabs (voiceover) | ~$0.003/char | ~$6 | ~2k chars per script × 40 |
| HeyGen (avatar video) | ~$0.10/min | ~$6 | 60-90 sec per video |
| Creatomate (assembly) | $0.05/render | ~$6 | 3 platform variants each |
| **Total production** | | **~$20/mo** | |
| TikTok posting | Free | $0 | |
| Instagram/Facebook posting | Free | $0 | Meta Graph API free tier |
| LinkedIn posting | Free | $0 | |
| **Grand total** | | **~$20/mo** | |

> All API costs are subject to change. Check each provider's current pricing page.

---

## 6. Safe Dev Mode (No Real Posts)

The pipeline is wired to be safe by default. In `.env`:

```bash
CAMPAIGN_VIDEO_PROVIDER=mock    # No HeyGen API calls
CONTENT_PUBLISH_MODE=mock       # No platform posts
HEYGEN_TEST_MODE=true           # No HeyGen credits consumed
```

In mock mode:
- `/generate-video` returns a fake `provider_id` instantly
- `/video-status` returns `completed` with a placeholder video URL
- `/publish` returns a fake `external_post_id` (no real post goes out)
- All responses look identical to live responses — your UI/agent logic can be tested fully

---

## 7. Going Live Checklist

Before flipping to live mode, verify:

- [ ] `BACKEND_URL` is a **publicly reachable URL** (not localhost). TikTok and Meta pull video files from this URL — it must be accessible from the internet.
- [ ] `MEDIA_STORAGE_PATH` files are accessible at `{BACKEND_URL}/media/` — test by opening `{BACKEND_URL}/media/` in a browser
- [ ] HeyGen: recorded and approved Instant Avatar, `HEYGEN_TEST_MODE=false`
- [ ] Meta: long-lived token generated, not expired, `META_IG_USER_ID` and `META_PAGE_ID` confirmed
- [ ] TikTok: Content Posting API approved by TikTok, OAuth token obtained, `TIKTOK_OPEN_ID` set
- [ ] LinkedIn: OAuth 3-legged flow complete, `LINKEDIN_PERSON_ID` is full URN
- [ ] Run one full `mock` pipeline end-to-end and confirm all stages complete
- [ ] Flip `CAMPAIGN_VIDEO_PROVIDER=heygen`
- [ ] Flip `CONTENT_PUBLISH_MODE=live`
- [ ] Test with a single post on each platform before automating

---

## 8. Troubleshooting

### "Video URL rejected by Meta/TikTok"
**Cause:** `BACKEND_URL` is set to `http://localhost:8000`. Meta and TikTok must be able to reach the URL from their servers.

**Fix:** Use [ngrok](https://ngrok.com) for local dev:
```bash
ngrok http 8000
# Copy the https:// URL → set BACKEND_URL=https://xxxxx.ngrok.io
```
Or deploy to Render/Railway/Fly.io for a permanent public URL.

### "HeyGen returns error: avatar not found"
**Cause:** `HEYGEN_AVATAR_ID` is wrong or the avatar hasn't been approved yet.

**Fix:** Log into HeyGen → Studio → Avatars → confirm your avatar shows "Active" status. Copy the ID exactly (case-sensitive).

### "Instagram: MEDIA_STATUS not FINISHED (polling timeout)"
**Cause:** Meta's container creation can take 1-5 minutes for Reels. The pipeline polls up to 36× at 10-second intervals (6 minutes max).

**Fix:** If it consistently times out, check that the video URL is publicly reachable and the file is a valid MP4 (H.264, AAC audio, 9:16 aspect ratio for Reels).

### "TikTok: 401 Unauthorized"
**Cause:** TikTok access tokens expire in 24 hours.

**Fix:** Re-run the OAuth flow to get a fresh token. For long-term use, implement the refresh token flow using TikTok's `/v2/oauth/token/refresh/` endpoint.

### "LinkedIn: 422 Unprocessable Entity on video post"
**Cause:** `LINKEDIN_PERSON_ID` is missing the `urn:li:person:` prefix, or the video finalize step failed.

**Fix:** Confirm `LINKEDIN_PERSON_ID` is the full URN string: `urn:li:person:XXXXXXXXX`.

### "ElevenLabs returns empty audio"
**Cause:** `ELEVENLABS_VOICE_ID` is wrong or the voice has been deleted.

**Fix:** Log into ElevenLabs → Voice Lab → confirm voice exists → copy ID from the voice detail page.

### "Content agent performance analysis shows no data"
**Cause:** No `SocialPost` records in the database yet, or all posts are in `script_only` stage.

**Fix:** Generate a few posts and put them through the approval flow first. The analysis needs at least 2 posts per category to trigger decisions.

### "MediaAsset MP3 returns 404"
**Cause:** `MEDIA_STORAGE_PATH` directory doesn't exist or the FastAPI static mount failed.

**Fix:** The app auto-creates the directory on startup. Check that the `backend` process has write permission to the directory. On macOS: `chmod 755 ./media`.

---

## Quick Reference — ENV Vars by Feature

| Feature | ENV Vars Needed |
|---|---|
| Script generation only | `OPENAI_API_KEY` |
| + Voiceover | + `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| + HeyGen avatar video | + `HEYGEN_API_KEY`, `HEYGEN_AVATAR_ID`, `CAMPAIGN_VIDEO_PROVIDER=heygen`, `HEYGEN_TEST_MODE=false`, `BACKEND_URL` (public) |
| + Creatomate assembly | + `CREATOMATE_API_KEY`, `CREATOMATE_TEMPLATE_ID_*` |
| + Instagram Reels publish | + `META_ACCESS_TOKEN`, `META_IG_USER_ID`, `CONTENT_PUBLISH_MODE=live` |
| + Facebook publish | + `META_ACCESS_TOKEN`, `META_PAGE_ID` |
| + TikTok publish | + `TIKTOK_ACCESS_TOKEN`, `TIKTOK_OPEN_ID` |
| + LinkedIn publish | + `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_ID` |
| Cost tracking | `COST_HEYGEN_PER_MIN`, `COST_CREATOMATE_RENDER` |

---

*NMLS #1454510 — All AI-generated content is reviewed and approved by a licensed mortgage banker before publishing. Compliance notes are automatically included in every generated post.*

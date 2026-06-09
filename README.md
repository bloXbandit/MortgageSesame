# MortgageSesame

AI-powered mortgage acquisition operating system for solo mortgage bankers.
Built for NMLS #1454510 — Maryland / DC market.

---

## What This Is

Three surfaces. One backend. One mission: turn homeowner data into closed loans.

| Surface | What it does |
|---------|-------------|
| **Public Hub** (`public-site/`) | Lead capture, rate ticker, DPA programs, home listings, product education. Open to the public — no login wall. |
| **Command Center** (`admin-app/`) | Electron `.app` (Mac) + iOS AltStore sideload. Full CRM, campaign management, call queue, agent dashboard. |
| **Backend API** (`backend/`) | FastAPI. Single source of truth. Runs locally inside Electron or deployed to Railway/Render. |

---

## Architecture

```
MortgageSesame/
├── backend/               FastAPI + SQLAlchemy + SQLite → Postgres upgrade path
│   ├── app/
│   │   ├── models/        SQLAlchemy ORM models
│   │   │   ├── outreach.py    ProspectList, Prospect, RefiScore, CampaignOutreach,
│   │   │   │                  QRLink, QREvent, CallTask, SuppressionEntry
│   │   │   ├── hub.py         RateSnapshot, Listing, DpaProgram
│   │   │   ├── campaign.py    Campaign, CampaignStep, MessageTemplate
│   │   │   └── contact.py     Contact, ConsentRecord, OptOut
│   │   ├── routers/
│   │   │   ├── outreach.py    Campaign engine API (prospects → score → generate → send)
│   │   │   ├── tracking.py    QR redirect (/r/{code}) + event recording
│   │   │   ├── rates.py       FRED rate feed + admin overrides
│   │   │   ├── listings.py    Property listings CRUD + calculator
│   │   │   ├── dpa.py         Down payment assistance programs
│   │   │   ├── leads.py       Public intake form receiver
│   │   │   └── agent.py       AI agent API (13 tool endpoints)
│   │   └── services/
│   │       ├── campaign_writer.py   Email/SMS/call script content generation
│   │       ├── mail_templates.py    5 HTML direct mail templates (equity voucher, etc.)
│   │       ├── scoring_service.py   Prospect scoring engine (A/B/NURTURE/SKIP/BLOCKED)
│   │       └── providers/
│   │           ├── base.py          Abstract interfaces (EmailProvider, DirectMailProvider…)
│   │           ├── mock.py          Dev mocks + provider stubs (Lob, SendGrid, Resend…)
│   │           └── registry.py      Env-driven provider factory
├── public-site/           React 18 + Tailwind v4 + Vite — localhost:5173
├── admin-app/             React 18 + Electron 28 + Capacitor 5 — localhost:5174
└── agent/                 AI agent tool contracts + voice integration docs
```

---

## Quick Start (Local Dev)

### Prerequisites

- Python 3.11+
- Node 20+
- Git

### One-command setup

```bash
make setup   # creates backend/.venv, npm install public-site + admin-app
```

### Run everything

```bash
make dev
```

That starts:
- **Backend** → `http://localhost:8000` (uvicorn --reload)
- **Public site** → `http://localhost:5173`
- **Admin app** → `http://localhost:5174`

### Manual (step by step)

```bash
# Terminal 1 — Backend
cd backend
source .venv/bin/activate
cp .env.example .env        # fill in your values (see env guide below)
uvicorn main:app --reload --port 8000

# Terminal 2 — Public site
cd public-site
npm install && npm run dev

# Terminal 3 — Admin app (browser)
cd admin-app
npm install && npm run dev
```

### API docs (dev only)
```
http://localhost:8000/docs
```

---

## Mac App (Electron)

```bash
cd admin-app
npm run electron:dev      # dev mode with hot reload
npm run electron:build    # builds signed .app into dist-electron/
```

The Electron app connects to `http://localhost:8000` by default.
For a standalone `.app`, bundle the backend with PyInstaller and point `VITE_API_URL` at the local binary port.

---

## iOS (AltStore Sideload)

```bash
cd admin-app
npm run build              # Vite build
npx cap sync ios           # sync to Capacitor iOS project
npx cap open ios           # opens Xcode
```

In Xcode: **Product → Archive → Distribute App → Development → Export IPA**
Sideload via AltStore on your iPhone (no App Store, no jailbreak).

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Key sections:

### Core

```bash
DATABASE_URL=sqlite+aiosqlite:///./mortgagesesame.db   # SQLite for dev
SECRET_KEY=<openssl rand -hex 32>                       # JWT signing key
APP_ENV=development
```

### AI (email subject enhancement, lead scoring)

```bash
OPENAI_API_KEY=sk-...          # Optional — works without it (static templates)
AI_FAST_MODEL=gpt-4o-mini
```

### Campaign Providers (all default to mock — safe for dev)

```bash
CAMPAIGN_EMAIL_PROVIDER=mock        # mock | sendgrid | resend
CAMPAIGN_DIRECT_MAIL_PROVIDER=mock  # mock | lob | postgrid
CAMPAIGN_SMS_PROVIDER=mock          # mock | signalwire | twilio
CAMPAIGN_PROPERTY_PROVIDER=mock     # mock | attom

# Set these when switching away from mock:
RESEND_API_KEY=
SENDGRID_API_KEY=
LOB_API_KEY=
POSTGRID_API_KEY=
ATTOM_API_KEY=

# Copy in email sends
CAMPAIGN_FROM_EMAIL=kevin@mortgagesesame.com
CAMPAIGN_FROM_NAME=Kevin at MortgageSesame
BANKER_PHONE=443-555-0100
```

### SMS (TCPA — consent required before enabling)

```bash
SIGNALWIRE_ACCOUNT_SID=
SIGNALWIRE_AUTH_TOKEN=
SIGNALWIRE_FROM_NUMBER=
SIGNALWIRE_SPACE=
CAMPAIGN_SMS_PROVIDER=signalwire    # only after consent gate is live
```

### Public site (frontend env)

Create `public-site/.env.local`:
```bash
VITE_API_URL=http://localhost:8000
```

---

## Campaign Engine — End to End

> The full workflow: import list → score → generate content → approve → send → track → call.

### Overview

```
CSV / Manual Import
        │
        ▼
  ProspectList + Prospects
        │
        ▼
  Scoring Engine ──── ScoreGrade: A_TARGET / B_TARGET / NURTURE / SKIP / BLOCKED
        │
        ▼
  Content Generation ─── Email HTML / Direct Mail HTML / SMS / Call Script
        │
        ▼
  Compliance Check + Approval
        │
        ▼
  Provider Send ────────── Email (SendGrid/Resend) | Mail (Lob/PostGrid) | SMS (SignalWire)
        │
        ▼
  QR Scan / Email Open / Click
        │
        ▼
  CallTask (Priority 1 hot lead) ──── Your call queue
        │
        ▼
  CONVERTED 🎯
```

---

### Step 1 — Create a Prospect List

```bash
POST /api/v1/outreach/prospect-lists
{
  "name": "MD Refi Targets June 2026",
  "prospect_type": "homeowner",
  "state": "MD",
  "county": "Prince George's"
}
```

---

### Step 2 — Import Prospects

**Option A: JSON batch**
```bash
POST /api/v1/outreach/prospect-lists/{id}/prospects
[
  {
    "first_name": "Marcus",
    "last_name": "Williams",
    "email": "marcus@email.com",
    "phone": "301-555-0182",
    "property_address": "8842 Chesapeake Blvd",
    "property_city": "Bowie",
    "property_state": "MD",
    "current_rate_estimate": 7.25,
    "estimated_equity_pct": 42.0,
    "estimated_equity_dollars": 187000,
    "current_loan_amount": 380000,
    "loan_type": "Conventional",
    "origination_date": "2022-11-15",
    "is_owner_occupied": true
  }
]
```

**Option B: CSV upload**
```bash
POST /api/v1/outreach/prospect-lists/{id}/upload-csv
Content-Type: multipart/form-data
file=<your_list.csv>
```

The CSV importer auto-maps 30+ column header variants (spaces, underscores, abbreviations).
Common column names it recognizes:

| Your header | Maps to |
|-------------|---------|
| `rate`, `interest_rate` | `current_rate_estimate` |
| `loan_balance`, `balance` | `current_loan_amount` |
| `equity_%`, `equity_pct` | `estimated_equity_pct` |
| `avm`, `home_value` | `estimated_current_value` |
| `owner_name`, `name` | `full_name` |
| `dnc`, `do_not_contact` | `is_do_not_contact` |

---

### Step 3 — Score the List

```bash
POST /api/v1/outreach/prospect-lists/{id}/score
```

Runs the scoring engine on every prospect. Returns:
```json
{
  "scored": 847,
  "a_target": 124,
  "b_target": 231,
  "nurture": 389,
  "suppressed": 22
}
```

**How scoring works** (additive/subtractive, 0–100):

| Signal | Points |
|--------|--------|
| Rate ≥ 6.5% | +30 |
| Rate 6.0–6.49% | +15 |
| Originated 90d–18mo ago (high-rate window) | +25 |
| Equity ≥ 40% | +25 |
| Equity 25–39% | +20 |
| Loan ≥ $250K | +15 |
| FHA loan + rate ≥ 6% | +10 (streamline flag) |
| No refi detected | +10 |
| Owner-occupied | +10 |
| Purchased < 90 days ago | −50 |
| Refi'd < 12 months ago | −25 |
| DNC / suppressed | −200 → BLOCKED |

**Grade cutoffs:**
- `A_TARGET` → 80+
- `B_TARGET` → 60–79
- `NURTURE` → 40–59
- `SKIP` → < 40
- `BLOCKED` → DNC or suppression list hit

View score distribution:
```bash
GET /api/v1/outreach/prospect-lists/{id}/score-summary
```

---

### Step 4 — Generate Content

**Single prospect:**
```bash
POST /api/v1/outreach/generate
{
  "prospect_id": "abc123",
  "channel": "email",
  "campaign_type": "cash_out_equity",
  "step": 1
}
```

**Batch (all A+B prospects in a list):**
```bash
POST /api/v1/outreach/prospect-lists/{id}/generate-batch
{
  "campaign_type": "refi_rate_reduction",
  "channel": "direct_mail",
  "step": 1,
  "grades": ["A_TARGET", "B_TARGET"],
  "max_items": 500
}
```

**Campaign types available:**

| Type | Best channel | What it sends |
|------|-------------|---------------|
| `refi_rate_reduction` | direct_mail, email | Rate savings analysis, "I ran your numbers" |
| `cash_out_equity` | direct_mail, email | Big equity number as headline, use cases |
| `fha_streamline_watch` | email, sms | FHA streamline education, no-appraisal pitch |
| `past_client_equity_review` | email | Annual check-in from their banker |
| `investor_refi` | email, direct_mail | DSCR investor cash flow angle |
| `realtor_partnership` | email | Value-first intro, buyer qualification offer |
| `listing_agent_outreach` | email | Property-specific intro, fast close positioning |
| `dpa_education` | email | DPA program awareness, qualification check |

**Channels:**

| Channel | What gets generated |
|---------|-------------------|
| `email` | Subject line + HTML + plain text (3-step sequence per type) |
| `direct_mail` | Full HTML postcard/letter (5 templates, premium dark/gold design) |
| `sms` | 160-char TCPA-compliant body |
| `call_task` | Opener script + pitch + talking points + objection handlers |

**Direct mail templates:**

| Template key | Design | Use case |
|-------------|--------|----------|
| `equity_voucher` | Dark/gold, big equity $ as headline | High-equity homeowners |
| `refi_certificate` | Certificate frame, ribbon header | Rate reduction prospects |
| `fha_streamline_notice` | Navy blue, checklist design | FHA loan holders |
| `dscr_investor_notice` | All-dark, bold investor voice | Non-owner occupied |
| `realtor_invite` | Clean professional, feature grid | Realtor partnership |

Every direct mail piece includes:
- **ADVERTISEMENT** header label
- **NOT A CHECK — NOT A LOAN APPROVAL** disclaimer
- NMLS #1454510
- Equal Housing Lender
- Personal QR code linked to booking page

---

### Step 5 — Approve & Send

**Review generated items:**
```bash
GET /api/v1/outreach/items?status=draft
GET /api/v1/outreach/items/{id}          # Full HTML/text/script preview
```

**Edit content before approval:**
```bash
PATCH /api/v1/outreach/items/{id}
{
  "subject": "Your revised subject line",
  "body_html": "...",
  "body_text": "..."
}
```

**Approve:**
```bash
POST /api/v1/outreach/items/{id}/approve
```

**Reject with reason:**
```bash
POST /api/v1/outreach/items/{id}/reject
"Subject line too aggressive — soften"
```

**Send:**
```bash
POST /api/v1/outreach/items/{id}/send
```

The send endpoint:
1. Checks prospect for DNC/suppression — blocks if found
2. Routes to the configured provider (`CAMPAIGN_EMAIL_PROVIDER`, etc.)
3. In mock mode: logs + returns fake ID, nothing actually sends
4. In live mode: calls the real provider API
5. Updates status to `sent` with timestamp

---

### Step 6 — QR Tracking

Every mail piece and email gets a unique QR code like:
```
https://yourdomain.com/r/AB12CD34EF
```

When someone scans → `GET /r/{code}` runs:
1. Records a `QREvent` (type: `scan`)
2. Increments `scan_count` on the `QRLink`
3. Updates `CampaignOutreach.status` → `QR_SCANNED`
4. **Creates a Priority-1 `CallTask`** (hottest lead signal possible)
5. Redirects to your Cal.com booking page

Email clicks use the same codes — tracked as `click` type instead.

**Track all QR activity:**
```bash
GET /api/v1/track/links               # all links + scan counts
GET /api/v1/track/links/{code}        # single link + event log
GET /api/v1/track/summary             # aggregate stats across all campaigns
```

---

### Step 7 — Work Your Call Queue

When a QR is scanned, a `CallTask` appears immediately in your warm-lead queue:

```bash
GET /api/v1/outreach/call-tasks        # pending tasks, priority order
```

Response includes:
```json
{
  "prospect_name": "Marcus Williams",
  "phone": "301-555-0182",
  "property_address": "8842 Chesapeake Blvd, Bowie MD",
  "trigger": "qr_scan",
  "trigger_detail": "Scanned QR from equity_voucher mailer",
  "priority": 1,
  "talking_points": [
    "Estimated $187,000 accessible in 8842 Chesapeake Blvd",
    "HELOC vs cash-out refi — 15-minute comparison",
    "Home equity rates much lower than credit card rates",
    "Tax implications — consult your CPA"
  ],
  "call_script": "...",
  "campaign_context": "equity_voucher"
}
```

**Update task after call:**
```bash
PATCH /api/v1/outreach/call-tasks/{id}
{
  "status": "completed",
  "notes": "Spoke 8 min. Interested in HELOC. Sending pre-app link.",
  "outcome_detail": "Scheduling follow-up next Tuesday"
}
```

Task status options: `pending` → `completed` / `no_answer` / `voicemail_left` / `callback_scheduled` / `not_interested` / `converted`

---

## Suppression List

The engine checks suppression before every email and SMS send.

```bash
GET  /api/v1/outreach/suppression          # view all
POST /api/v1/outreach/suppression          # add manually
DELETE /api/v1/outreach/suppression/{id}   # remove

# Example add:
{
  "value": "user@email.com",
  "value_type": "email",
  "reason": "opt_out"
}
```

Provider webhooks (SendGrid, Resend, SignalWire) auto-add to suppression on unsubscribe/bounce/STOP.
Webhook endpoint: `POST /api/v1/outreach/webhooks/{provider_name}`

---

## How Everything Connects

```
┌─────────────────────────────────────────────────────────────────┐
│                     PUBLIC HUB (port 5173)                       │
│  Rate Ticker ─── FRED API (/api/v1/rates/ticker)                 │
│  Listings ─────── /api/v1/listings                               │
│  DPA Hub ──────── /api/v1/dpa                                    │
│  MicroIntake ──── /api/v1/leads/intake ──────────┐               │
└─────────────────────────────────────────────────│───────────────┘
                                                  │
┌─────────────────────────────────────────────────▼───────────────┐
│                     BACKEND API (port 8000)                       │
│                                                                   │
│  /api/v1/auth          JWT login + refresh                        │
│  /api/v1/leads         Public intake → LeadIntake table           │
│  /api/v1/contacts      CRM contacts + consent records             │
│  /api/v1/rates         FRED feed + admin overrides                │
│  /api/v1/listings      Property listings + calculator             │
│  /api/v1/dpa           Down payment assistance programs           │
│  /api/v1/outreach      ◀── Campaign engine (see above)           │
│  /r/{code}             ◀── QR redirect (root, no prefix)         │
│  /api/v1/track         QR admin + tracking stats                  │
│  /api/v1/agent         AI agent tool endpoints (API key auth)     │
│                                                                   │
│  SQLite (dev) / Postgres (prod)                                   │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────┐
│               COMMAND CENTER (port 5174 / Electron / iOS)         │
│                                                                   │
│  Dashboard ─── Live stats                                         │
│  Leads ──────── Intake review + AI scoring                        │
│  Contacts ───── CRM + CSV import                                  │
│  Outreach ───── Prospect lists → scoring → generate → send       │
│  Call Queue ─── Warm leads from QR scans + form fills             │
│  Rates ──────── FRED sync + manual overrides                      │
│  Listings ───── Property CRUD                                     │
│  DPA Programs ── Program management + seed                        │
│  Content Studio ─ AI social / email content                       │
│  Approvals ───── Review AI-generated items before publish         │
│  Agent Logs ──── AI agent run history                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Provider System

All channel sends go through a swappable provider layer.
Change one env var → different provider, zero code changes.

```bash
# Switch email from mock to Resend:
CAMPAIGN_EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxx

# Switch direct mail from mock to Lob:
CAMPAIGN_DIRECT_MAIL_PROVIDER=lob
LOB_API_KEY=live_xxxx
```

See **`backend/CAMPAIGN_PROVIDERS_README.md`** for full implementation instructions for each provider.

---

## AI Agent API

The agent API lets Clawdbot / Hermes / any OpenAI-function-calling agent manage the system.
Auth: `Authorization: Bearer {AGENT_API_KEY}` (from `.env`).

```
GET  /api/v1/agent/context            System state summary for orientation
GET  /api/v1/agent/products           Active loan products
GET  /api/v1/agent/campaigns          Campaign list
GET  /api/v1/agent/contacts           Contact summary
POST /api/v1/agent/research-target    Prospect research
POST /api/v1/agent/generate-outreach  Draft outreach content
POST /api/v1/agent/generate-content   Social/email content
POST /api/v1/agent/score-lead         Score a lead
POST /api/v1/agent/create-task        Create a task
POST /api/v1/agent/queue-action       Queue an action for human approval
POST /api/v1/agent/compliance-check   Run compliance on content
GET  /api/v1/agent/pending-approvals  Items awaiting human review
POST /api/v1/agent/voice-generate     ElevenLabs audio generation
```

All outbound actions require human approval unless explicitly unlocked.
Every agent action is logged to `AgentAction` + `AuditLog`.

---

## Database

SQLite by default (no setup needed). Zero-config dev startup.

**Upgrade to Postgres** (production):
```bash
# docker-compose.yml already has a postgres service
docker compose up db -d

# .env
DATABASE_URL=postgresql+asyncpg://mortgagesesame:mortgagesesame@localhost/mortgagesesame

# Migrate
cd backend && alembic upgrade head
```

Tables auto-created in `development` mode on startup (`Base.metadata.create_all`).
Use Alembic migrations for production schema changes.

---

## Public Hub — Rate Ticker

The rate ticker at the top of the public site pulls from:
1. **Admin override** (set in Command Center → Rates) — highest priority
2. **FRED API** (Federal Reserve Economic Data) — auto-synced daily
3. **Fallback static rates** — shown if both sources are unavailable

Force a FRED sync:
```bash
POST /api/v1/rates/admin/sync-fred
Authorization: Bearer {token}
```

Manual rate entry (for same-day market moves):
```bash
POST /api/v1/rates/admin/update
{
  "conv_30yr": 6.875,
  "fha_30yr": 6.625,
  "conv_15yr": 6.125,
  "notes": "Fed press conference today — rates bumped"
}
```

---

## DPA Programs — Seeded Data

The DPA Hub ships with 13 real Maryland + DC programs pre-seeded.

Seed them:
```bash
POST /api/v1/dpa/admin/seed-md-dc
Authorization: Bearer {token}
```

**Maryland:** MMP 6000, MMP 3%, MMP SmartBuy ($20K student debt payoff), HomeCredit MCC, MD Homefront (Veterans), PG County ($10K), Montgomery County ($25K), Baltimore City ($10K), Anne Arundel ($12.5K), Howard County ($40K)

**DC:** HPAP ($202K+), DC Open Doors (3–3.5%), EAHP (DC employees, $15K)

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI 0.111 + SQLAlchemy 2.0 async + aiosqlite |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Cache | Redis (optional in dev) |
| AI | OpenAI-compatible API (swap model/provider via env) |
| Email generation | Static templates + optional GPT subject-line enhancement |
| Frontend | React 18 + Tailwind v4 + Vite |
| Mac app | Electron 28 |
| iOS app | Capacitor 5 (AltStore sideload) |
| Voice | ElevenLabs |
| SMS | SignalWire (TCPA consent-gated) |
| Direct mail | Lob / PostGrid (mock by default) |
| Auth | JWT (bcrypt + access/refresh tokens) |
| Logging | structlog (structured JSON) |
| Rate data | FRED API (Federal Reserve) |

---

## File Reference

| File | Purpose |
|------|---------|
| `backend/app/services/scoring_service.py` | Prospect scoring engine |
| `backend/app/services/campaign_writer.py` | Email/SMS/call script content generation |
| `backend/app/services/mail_templates.py` | 5 HTML direct mail templates |
| `backend/app/services/providers/base.py` | Abstract provider interfaces |
| `backend/app/services/providers/mock.py` | Mock + real provider stubs |
| `backend/app/services/providers/registry.py` | Env-driven provider factory |
| `backend/app/routers/outreach.py` | Campaign engine routes |
| `backend/app/routers/tracking.py` | QR redirect + event recording |
| `backend/app/models/outreach.py` | All campaign engine database models |
| `backend/CAMPAIGN_PROVIDERS_README.md` | How to add/swap/implement providers |
| `backend/.env.example` | All environment variable reference |

---

## NMLS Compliance Notes

- NMLS #1454510 appears on every public page, every email, every mailer
- All rate/payment figures are labeled **illustrative** — not a commitment to lend
- Direct mail templates include **ADVERTISEMENT** header and **NOT A CHECK** disclaimer on every piece
- DNC check happens at score time (flag) and again at send time (hard block)
- SMS requires express written consent before any send — mock provider is safe; enabling SignalWire requires consent gate to be live
- Unsubscribe links required in all email — wire `{{unsubscribe_url}}` to your ESP's unsubscribe mechanism
- Equal Housing Lender statement on all public-facing materials

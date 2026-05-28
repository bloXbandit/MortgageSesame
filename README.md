# MortgageSesame

AI-powered mortgage acquisition operating system for solo mortgage bankers.

## Architecture

```
MortgageSesame/
├── backend/        # FastAPI — runs locally (Electron) + deployed (Railway/Render)
├── public-site/    # React + Pika style — public lead capture (Vercel/Netlify)
├── admin-app/      # React + Electron (Mac .app) + Capacitor (iOS via AltStore)
└── agent/          # Agent tool contracts, voice integration docs
```

## Quick Start (Development)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # fill in your values
alembic upgrade head
uvicorn main:app --reload --port 8000

# 2. Public site
cd public-site
npm install && npm run dev   # localhost:5173

# 3. Admin app (web)
cd admin-app
npm install && npm run dev   # localhost:5174
```

## Mac App (Electron)

```bash
cd admin-app
npm install
npm run electron:dev      # dev mode
npm run electron:build    # builds .app in dist-electron/
```

## iOS / AltStore Sideload

```bash
cd admin-app
npm run build
npx cap sync ios
# Open ios/App/App.xcworkspace in Xcode
# Product → Archive → Distribute → Development Distribution → IPA
# Sideload via AltStore
```

See `agent/voice_integration.md` for ElevenLabs + phone number setup.

## Environment Variables

Copy `.env.example` → `.env` in both `backend/` and `admin-app/`.

## Phase 1 MVP Scope

- [x] Auth (JWT)
- [x] Product library CRUD
- [x] Contact management + CSV import
- [x] Public lead intake (multi-step form)
- [x] AI lead scoring + summary
- [x] AI content generation
- [x] AI outreach draft generation
- [x] Approval queue
- [x] Agent API skeleton (13 endpoints)
- [x] Compliance guardrails middleware
- [x] Audit logging

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Database | PostgreSQL (Supabase or self-hosted) |
| Cache | Redis |
| AI | OpenAI-compatible (swap provider via env) |
| Frontend | React 18 + Tailwind v4 + Vite |
| Mac app | Electron 28 |
| iOS app | Capacitor 5 |
| Voice | ElevenLabs (connector) |
| SMS | Twilio (consent-gated) |
| Auth | JWT (bcrypt + RS256 ready) |

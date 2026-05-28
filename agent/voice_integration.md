# Voice Integration — ElevenLabs + Agent Phone Number

## Overview

Your agent has its own voice (ElevenLabs) and its own phone number (Twilio).
These work together for:

1. **Ad voiceovers** — agent generates scripts → ElevenLabs renders audio → you use in TikTok/IG Reels
2. **Outreach audio** — agent generates personalized audio messages (future: Twilio voice calls)
3. **Phone number identity** — every outbound SMS/call comes from a consistent number your contacts recognize

---

## Step 1: ElevenLabs Setup

1. Create account at **elevenlabs.io**
2. Use a pre-built voice OR clone your own voice:
   - Go to **Voices → Add Voice → Instant Voice Clone**
   - Upload 1–3 min of clean audio of yourself
   - Name it (e.g. "Agent Voice")
3. Copy the **Voice ID** from the voice card
4. Go to **API Keys** → create a key
5. Add to your `.env`:
   ```
   ELEVENLABS_API_KEY=xi-...
   ELEVENLABS_VOICE_ID=abc123...  # your cloned/selected voice
   ELEVENLABS_AGENT_VOICE_NAME=Agent Voice
   ```

The agent calls `POST /api/v1/agent/voice-generate` → gets back base64 MP3 → saves or plays.

---

## Step 2: Agent Phone Number (Twilio)

Your agent needs a dedicated number so:
- Contacts see a consistent caller ID
- SMS opt-out tracking works per-number
- Call recordings can be routed to you

### Setup:
1. Create account at **twilio.com**
2. Buy a local number (same area code as your market — e.g. Houston 713/832)
3. Copy Account SID, Auth Token, and the number
4. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxx
   TWILIO_AUTH_TOKEN=xxx
   TWILIO_FROM_NUMBER=+17135550100
   ```

### The agent uses this number for:
- Outbound SMS (consent-gated only — contact must have `consent_sms: true`)
- Future: voice calls via TwiML + ElevenLabs audio stream

---

## Step 3: Phone Call Flow (future / Phase 3)

When ready for AI-assisted outbound calls:

```
Agent generates call script
  → POST /agent/voice-generate  (ElevenLabs renders MP3)
  → Upload MP3 to storage (S3 / Supabase)
  → Queue TwiML call via Twilio REST
  → Twilio dials contact's number
  → Plays ElevenLabs audio
  → Transfers to banker if prospect engages
```

This is NOT implemented in Phase 1 — it requires:
- Consent verification before every call
- TCPA-compliant timing (no calls before 8am / after 9pm local)
- Do-Not-Call registry check
- Recording disclosure in call

Add this in Phase 3. For now the agent drafts scripts and you make the calls yourself.

---

## Using Your Voice for Social Content

1. Agent calls `POST /agent/generate-content` → gets `voiceover_script`
2. Agent calls `POST /agent/voice-generate` with the script → gets MP3
3. You download the MP3 from the API response (base64 decode)
4. Use it as voiceover in CapCut / DaVinci / Premiere for TikTok/Reels

The voice is consistent across all content → builds brand recognition.

---

## ElevenLabs Voice Tips for Mortgage Content

- **Model:** `eleven_multilingual_v2` (best quality, used by default)
- **Stability:** 0.5 (slight variation = natural delivery)
- **Similarity Boost:** 0.75 (stay true to cloned voice)
- Keep scripts under 500 characters per generation (API limit on free tier)
- For long scripts, split at sentence boundaries

---

## SMS Compliance Summary

Before any SMS fires:
```python
contact.consent_sms == True      # explicit consent recorded
contact.is_dnc == False           # not on DNC list  
contact.is_opted_out == False     # hasn't opted out
message contains opt-out language # "Reply STOP to unsubscribe"
```

All of this is enforced in `backend/app/services/integrations/twilio.py`.
The compliance check middleware also scans the message body before it's queued.

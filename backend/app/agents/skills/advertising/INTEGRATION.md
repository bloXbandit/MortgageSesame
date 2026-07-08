# INTEGRATION GUIDE
# How Clawdbot / Hermes loads and uses these advertising skills

---

## ARCHITECTURE OVERVIEW

```
You (trigger: "build a campaign for declined buyers targeting FHA")
  │
  ▼
Clawdbot / Hermes (your agent orchestrator)
  │  reads skill files from this directory as context
  │  runs 9-step chain internally
  │
  ▼
POST /api/v1/agent/build-campaign         ← new endpoint (see campaign_builder.py)
  │  payload: { avatar, product, proof, market, budget_hint }
  │
  ▼
campaign_builder.py                       ← loads skill files, runs chain via ai_service.py
  │
  ▼
ai_service.py                             ← calls your LLM (Claude, GPT-4o, etc.)
  │
  ▼
Output → Approval Queue (/approvals)      ← your human checkpoint
  │
  ▼
You approve → assets are ready to deploy
```

---

## STEP 1 — CONFIGURE YOUR LLM

In `backend/.env`, set which model Clawdbot uses for generation:

**Option A — Claude (Anthropic) via OpenAI-compatible SDK:**
```bash
OPENAI_API_KEY=sk-ant-xxxxxxxxxxxx
OPENAI_BASE_URL=https://api.anthropic.com/v1
AI_MODEL=claude-opus-4-5
AI_FAST_MODEL=claude-haiku-4-5
```

**Option B — GPT-4o (current default):**
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o
AI_FAST_MODEL=gpt-4o-mini
```

**Option C — Any OpenAI-compatible endpoint (local model, etc.):**
```bash
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=http://localhost:11434/v1   # e.g. Ollama
AI_MODEL=your-model-name
```

The skills and chain work with any capable model. Claude performs best on long-form sales letter generation.

---

## STEP 2 — CONFIRM AGENT API KEY

Clawdbot authenticates to the MortgageSesame backend via:

```bash
# in backend/.env
AGENT_API_KEY=your-secret-key-here
```

Every request Clawdbot makes must include:
```
Authorization: Bearer YOUR_AGENT_API_KEY
```

---

## STEP 3 — THE ENDPOINT CLAWDBOT CALLS

**Endpoint:** `POST /api/v1/agent/build-campaign`

**Auth:** Bearer AGENT_API_KEY (same as all other /agent/ routes)

**Payload:**
```json
{
  "avatar": "declined_buyer",
  "product": "fha",
  "proof": "Closed $390k FHA in 9 business days for a buyer in Bowie MD who had been declined twice",
  "market": "MD",
  "budget_hint": "low"
}
```

**Avatar options:**
`declined_buyer` | `first_timer` | `equity_prisoner` | `realtor_client`

**Product options:**
`fha` | `va` | `dpa` | `conventional` | `heloc` | `dscr` | `refi`

**Market options:**
`MD` | `DC` | `both`

**Budget hint options:**
`low` | `mid` | `scale`

---

## STEP 4 — WHAT COMES BACK

The endpoint returns the full campaign package and routes everything to the Approval Queue:

```json
{
  "status": "pipeline_complete",
  "run_id": "uuid",
  "campaign_meta": { ... },
  "ad_units": [ ... ],        // 3 FB/IG ad units
  "sales_letter": { ... },    // full landing page copy
  "email_sequence": [ ... ],  // 3-part follow-up
  "qa_report": { ... },
  "approval_queue_ids": [     // IDs in /approvals for review
    "queue-id-1",
    "queue-id-2",
    "queue-id-3"
  ],
  "note": "All assets are pending your review at /approvals. Nothing goes live until approved."
}
```

---

## STEP 5 — REVIEW IN APPROVAL QUEUE

Go to `/approvals` in the admin app.
You'll see each asset:
- 3 ad copy units (labeled by angle type)
- 1 sales letter (labeled with the URL slug)
- 3 emails (labeled day 1/2/3)

For each one:
- ✅ **Approve** → asset is marked ready (you then deploy it to Facebook manually, or schedule the email)
- ✏️ **Edit** → tweak the copy if something doesn't sound like you
- ❌ **Reject** → sends it back; run the endpoint again with a different proof or avatar

---

## STEP 6 — GIVING CLAWDBOT THE SYSTEM PROMPT

When you're setting up Clawdbot/Hermes with its system context, include this:

```
You are the campaign orchestration agent for [BANKER_NAME], a [SERVICE_STATES] mortgage banker (NMLS #[BANKER_NMLS]).
When asked to build a campaign, you:
1. Confirm the 5 inputs: avatar, product, proof, market, budget_hint
2. Call POST /api/v1/agent/build-campaign with those inputs
3. Report what was generated and where to find it in the Approval Queue
4. Do NOT write ad copy yourself — the endpoint handles that via the skill chain
5. Do NOT send or publish anything — all assets require human approval first

Available avatars: declined_buyer, first_timer, equity_prisoner, realtor_client
Available products: fha, va, dpa, conventional, heloc, dscr, refi
Auth: include Authorization: Bearer {AGENT_API_KEY} on every call
Base URL: {BACKEND_URL}/api/v1
```

---

## STEP 7 — EXAMPLE CLAWDBOT CONVERSATION FLOW

**You say:**
"Build a campaign targeting first-time buyers for FHA loans in Maryland."

**Clawdbot responds:**
"Got it. Do you have a proof point to include — a specific closing or result I can use?"

**You say:**
"Yes — I closed a buyer in Hyattsville, 3.5% down, $312k home, 11 business days."

**Clawdbot calls:**
```
POST /api/v1/agent/build-campaign
{
  "avatar": "first_timer",
  "product": "fha",
  "proof": "Closed a buyer in Hyattsville MD, $312k home, 3.5% down, 11 business days",
  "market": "MD",
  "budget_hint": "low"
}
```

**Clawdbot reports back:**
"Campaign built. 3 ad units, 1 sales letter (slug: /campaign/fha-first-timer-md), 3 emails.
All in your Approval Queue at /approvals. Review and approve before deploying."

---

## ADDING NEW AVATARS OR PRODUCTS

To add a new avatar (e.g., "refi_candidate"):
1. Add the avatar profile to `00_mortgage-avatar-library.md`
2. Add the avatar slug to the `avatar` field options in `campaign_builder.py`
3. That's it — the chain picks it up automatically

To add a new product (e.g., "bridge_loan"):
1. Add the product offer template to `01_offer-templates.md`
2. Add the product slug to `campaign_builder.py`
3. Done

---

## SKILL FILE LOCATION

All skill files live at:
```
backend/app/agents/skills/advertising/
  00_mortgage-avatar-library.md
  01_offer-templates.md
  02_schwartz-awareness-guide.md
  03_mechanism-builder.md
  04_ad-angle-multiplier.md
  05_scroll-stopping-creative.md
  06_sales-letter-architect.md
  07_objection-crusher.md
  08_generic-language-killer.md
  ORCHESTRATOR.md
  INTEGRATION.md         ← you are here
```

The `campaign_builder.py` service reads these at runtime and injects them into the LLM system prompt.
No database entries needed. Edit the .md files directly to update the agent's knowledge.

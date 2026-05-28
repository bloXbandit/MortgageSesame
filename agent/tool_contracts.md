# MortgageSesame — Agent Tool Contracts

All endpoints live at `{BACKEND_URL}/api/v1/agent/...`
Auth: `Authorization: Bearer {AGENT_API_KEY}`

---

## GET /agent/context
**Purpose:** Agent orientation — system counts, active instructions  
**Auth:** Agent key  
**Response:** `{ active_products, total_contacts, total_campaigns, pending_approvals, agent_instructions, timestamp }`  
**Audit:** No (read-only)

---

## GET /agent/products
**Purpose:** Read all active mortgage products for outreach/content context  
**Response:** `[{ id, name, product_type, audience, benefits, cta_language, prohibited_claims }]`  
**Audit:** No

---

## GET /agent/campaigns
**Purpose:** Read all campaigns and their approval requirements  
**Response:** `[{ id, name, campaign_type, goal, status, channel, requires_approval }]`  
**Audit:** No

---

## GET /agent/contacts?contact_type=&limit=
**Purpose:** Read sendable contacts (DNC/opted-out excluded server-side)  
**Response:** `[{ id, name, email, phone, company, contact_type, consent_email, consent_sms, lead_score }]`  
**Audit:** No

---

## POST /agent/research-target
**Purpose:** Generate talking points and research summary for a specific contact  
**Body:** `{ contact_id, research_type?, context? }`  
**Response:** `{ contact_id, research_summary }`  
**Audit:** YES — logged per contact

---

## POST /agent/generate-outreach
**Purpose:** Draft personalized outreach for a contact+product+goal+channel  
**Body:** `{ contact_id, product_id?, goal, channel }`  
**Response:** `{ draft: { subject, body, cta, opt_out }, compliance: { passed, flags }, requires_approval: true }`  
**Audit:** YES  
**IMPORTANT:** Always call `/agent/queue-action` after — never send directly

---

## POST /agent/generate-content
**Purpose:** Generate social media post draft for a platform+category  
**Body:** `{ platform, category, product_id? }`  
**Response:** `{ post_id, content: { hook, script, caption, cta, visual_concept, image_prompt, voiceover_script, compliance_notes, is_fictional_example }, compliance }`  
**Audit:** YES  
**NOTE:** Post is auto-saved with `pending` status. User approves in Content Studio.

---

## POST /agent/score-lead
**Purpose:** Re-score an existing lead intake  
**Body:** `{ intake_id }`  
**Response:** `{ intake_id, score: { score_value, score_label, recommended_product, readiness_score, summary, questions_for_call, recommended_cta, compliance_response } }`  
**Audit:** YES

---

## POST /agent/create-task
**Purpose:** Create a follow-up task for the banker  
**Body:** `{ title, description?, task_type?, priority?, contact_id?, campaign_id? }`  
**Response:** `{ task_id, title, status }`  
**Audit:** YES

---

## POST /agent/queue-action
**Purpose:** Queue any agent-generated output for human approval  
**Body:** `{ item_type, item_id, title, preview, priority? }`  
**item_type:** `outreach_message | social_post | campaign_step | agent_action | content_item`  
**Response:** `{ queue_id, status: "pending_approval" }`  
**RULE:** Call this BEFORE any external action. Banker reviews in Approvals tab.

---

## POST /agent/report-run
**Purpose:** Log a completed agent run (called at end of each session)  
**Body:** `{ agent_name, run_type, status, input_payload?, output_payload?, error_message?, duration_ms? }`  
**Response:** `{ run_id }`  
**Audit:** YES (creates AgentRun record)

---

## GET /agent/pending-approvals
**Purpose:** Check what's waiting in the approval queue  
**Response:** `[{ id, item_type, item_id, title, preview, created_at }]`

---

## POST /agent/compliance-check
**Purpose:** Run compliance guardrail check on any text before using it  
**Body:** `{ text, channel?, is_ad? }`  
**Response:** `{ passed: bool, flags: [{ rule, snippet, severity, suggestion }] }`  
**RULE:** Always run this before generating outreach or content. Block if `passed = false`.

---

## POST /agent/log-event
**Purpose:** Write a custom audit log entry  
**Body:** `{ action, resource_type?, resource_id?, details? }`  
**Response:** `{ logged: true }`

---

## POST /agent/voice-generate
**Purpose:** Generate MP3 voiceover via ElevenLabs (for ad scripts, content narration)  
**Body:** `{ text, voice_id? }`  
**Response:** `{ audio_base64, mime_type: "audio/mpeg", char_count }`  
**NOTE:** Requires `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` in backend `.env`

---

## Compliance Rules (enforced server-side + AI prompt)

| Rule | Severity |
|------|----------|
| Guaranteed approval claim | BLOCKED |
| No credit check / no-doc claim | BLOCKED |
| Referral fee / kickback language | BLOCKED |
| False government affiliation | BLOCKED |
| Fake testimonial / closing | BLOCKED |
| Missing opt-out for email/SMS | HIGH |
| Teaser rate without APR | HIGH |
| Superlative rate claim | HIGH |
| Missing NMLS/Equal Housing (ads) | MEDIUM |
| "Free money" / misleading DPA claim | MEDIUM |

---

## Agent Workflow Pattern

```
1. GET /agent/context          → orient yourself
2. GET /agent/products         → know what you're promoting
3. GET /agent/contacts         → who to reach
4. POST /agent/compliance-check → verify text is clean
5. POST /agent/generate-outreach OR generate-content
6. POST /agent/queue-action    → park for human review
7. POST /agent/create-task     → flag any follow-ups
8. POST /agent/report-run      → log the session
```

The banker reviews everything in the Approvals tab. Nothing external fires unless approved.

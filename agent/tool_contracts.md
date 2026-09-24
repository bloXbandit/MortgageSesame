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

## POST /outreach/scheduler/run
**Purpose:** One tick of the campaign engine — call on a schedule (e.g. every 15–60 min via cron)  
**Auth:** agent key OR admin JWT  
**What it does:**
- Advances ACTIVE campaign sequences: prospects whose last step was sent ≥ `delay_days` ago get the next step **drafted** (goes to approval queue — never auto-sends)
- Publishes SocialPosts marked `scheduled` whose `scheduled_date` has passed (scheduling = approval)
- Resurfaces due callbacks to the call queue
**Response:** `{ steps_generated, posts_published, posts_failed, callbacks_resurfaced, details[] }`  
**NOTE:** The backend also runs this automatically every `SCHEDULER_INTERVAL_MINUTES` while the server is up — calling it manually is for on-demand ticks or when the backend isn't always running.

---

## POST /campaigns/pages/{slug}/deploy
**Purpose:** Turn a built campaign page's email_sequence into a LIVE drip campaign  
**Auth:** admin JWT  
**Body:** `{ prospect_list_id? }` or `{ contact_ids?: [] }` (contacts auto-bridge to prospect rows)  
**What it does:** Creates an ACTIVE Campaign + CampaignSteps carrying the generated copy, drafts step-1 outreach per recipient (pending approval), scheduler auto-drafts steps 2+ as `delay_days` elapse  
**Response:** `{ campaign_id, steps, step1_drafts, skipped_suppressed }`  
**RULE:** Approval gate preserved — every step still needs human approval to send.

---

## POST /outreach/newsletter/draft
**Purpose:** Draft a market-update newsletter (live rates from latest RateSnapshot + rotating tip)  
**Auth:** agent key OR admin JWT  
**Body:** `{ audience: "contacts"|"prospect_list", prospect_list_id?, contact_ids? }`  
**Response:** `{ drafted, rates_as_of, subject }` — drafts await approval  
**NOTE:** contacts audience requires `consent_email`. Run weekly via Pi cron for the sphere-nurture motion.

---

## GET /partners?search=
**Purpose:** Look up realtor/title partners for co-marketing (flyers, letters)  
**Then:** pass `partner_id` to `/agent/build-flyer` — fills the realtor block (name/brokerage/phone/headshot) + auto-attaches their saved logo.  
**CRUD:** POST /partners, PATCH/DELETE /partners/{id}

---

## POST /outreach/webhooks/{provider}
**Purpose:** Inbound provider webhook — delivery events AND inbound SMS replies  
**Behavior:**
- Status callbacks (delivered/bounced/opted_out) update the outreach item
- Inbound SMS (`From`+`Body`, form-encoded) → marks item `replied`, creates a priority-1 CallTask, pushes `AGENT_WEBHOOK_URL` notification
- `STOP`/`UNSUBSCRIBE`/etc → suppression entry + prospect suppressed
- `START`/`UNSTOP` → removes phone suppression
**NOTE:** Point SignalWire's inbound message webhook at `https://<public-backend>/api/v1/outreach/webhooks/signalwire`. Requires BACKEND_URL to be publicly reachable.

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

## POST /agent/build-flyer
**Purpose:** Generate a branded flyer (AI avatar + themed Pillow/Bannerbear composite)
**Body:** `{ headline?, subheadline?, cta_text?, use_case?, flyer_format?, style_preset?, style_prompt_override?, skip_ai?, theme?, avatar_id?, source_flyer_id?, brand_name?, logo_asset_id?, logo_label? }`
- `theme`: midnight_gold | ocean | forest | plum | slate_ember
- `brand_name`: label drawn on the flyer — defaults to `FLYER_BRAND_NAME` env (falls back to APP_NAME)
- `logo_asset_id`: BrandAsset id — partner logo composited right-aligned in the footer strip
- `logo_label`: text before the logo, e.g. "Powered by" / "Driven by"
- `layout`: promo (default) | listing | open_house | program | comparison | lifestyle | rate_update | testimonial | just_funded | steps
- `layout_data`: structured content per layout — listing: {address, city_state, price, beds, baths, sqft, scenarios[], realtor{}} · program: {headline, highlight, benefits[]} · comparison: {left_title, right_title, rows[{left:{title,text}, right:{...}}], banner} · lifestyle: {headline_lines[], subheadline, cta_text} · rate_update: {rates[{label,value}], as_of, note} · testimonial: {quote, author, context} · just_funded: {badge, address, stat_line} · open_house: {address, date_line, time_line, price, note} · steps: {headline, steps[{title,desc}]}
- `listing_id`: auto-fills listing layouts (address/specs/price/photo/realtor) + LIVE payment scenarios (Conv 5% + FHA from latest rate snapshot via calc engine)
- `hero_asset_id`: BrandAsset used as the lead photo
- Layout flyers render 1080×1350 portrait. Revisions merge `layout_data` (send only changed keys).
- `avatar_id`: reuse a SavedAvatar from the library — skips AI generation entirely
- `source_flyer_id`: **revision mode** — inherits headline/copy/format/avatar from that flyer; pass only the fields to change. `headline` becomes optional when set.
**Response:** `{ flyer_id, status, flyer_url, avatar_url, provider, format, revised_from, avatar_reused }`

**WORKED EXAMPLES — verified live (flyers 16–23). Copy these shapes exactly; change only the copy:**

```json
// program — flyer 16
{"layout":"program","theme":"midnight_gold","headline":"Maryland DPA Programs",
 "layout_data":{"headline":"Maryland DPA Programs","highlight":"Up to $8,500 toward your down payment","benefits":["No repayment while you live in the home","Works with FHA, VA, and Conventional","Most buyers qualify with 640+ credit"]}}

// comparison — flyer 18
{"layout":"comparison","theme":"ocean","headline":"HELOC vs Home Equity Loan",
 "layout_data":{"headline":"Which fits your situation?","left_title":"HELOC","right_title":"Home Equity Loan","banner":"Both use your equity — the difference is flexibility","rows":[{"left":{"title":"Draw as needed","text":"Pay interest only on what you use"},"right":{"title":"Lump sum","text":"All funds at closing, fixed payment"}}]}}

// rate_update — flyer 17
{"layout":"rate_update","theme":"forest","headline":"This Week in Rates",
 "layout_data":{"headline":"Where rates sit this week","as_of":"this week","note":"Illustrative — not a rate lock.","rates":[{"label":"Conventional 30yr","value":"6.52%"},{"label":"FHA 30yr","value":"6.42%"}]}}

// lifestyle — flyer 19
{"layout":"lifestyle","theme":"slate_ember","headline":"Your Home Paid You Back",
 "layout_data":{"headline_lines":["YOUR HOME","PAID YOU","BACK"],"subheadline":"Cash-out refi — consolidate debt or fund renovations","cta_text":"See what your equity unlocks"}}

// testimonial — flyer 20
{"layout":"testimonial","theme":"plum","headline":"Client Words",
 "layout_data":{"quote":"Kenneth got us approved in days after two banks said no.","author":"The Carter Family","context":"First-time buyers · Upper Marlboro, MD"}}

// just_funded — flyer 21
{"layout":"just_funded","theme":"ocean","headline":"Just Funded",
 "layout_data":{"badge":"JUST FUNDED","address":"Bowie, MD","stat_line":"$412,000 purchase · FHA · closed in 16 days"}}

// steps — flyer 22
{"layout":"steps","theme":"midnight_gold","headline":"5 Steps to Your First Home",
 "layout_data":{"headline":"Your path to the keys","steps":[{"title":"15-minute call","desc":"We map your numbers — no credit pull"},{"title":"Pre-approval","desc":"Same-day letter when ready"}]}}

// open_house — flyer 23
{"layout":"open_house","theme":"forest","headline":"Open House This Weekend",
 "layout_data":{"address":"14 Midway Ave","city_state":"Laurel, MD 20723","date_line":"Saturday, June 14","time_line":"1:00 – 3:00 PM","price":145000,"note":"Financing answers on-site."}}
```

**REFERENCE THE LIBRARY:** `GET /flyers?layout=<name>` (agent key works) returns each example with its `layout_data` — revise one by passing `source_flyer_id` + only the changed keys.
**Audit:** Yes (`agent.flyer_built`)

---

## Avatar Library — /flyers/avatars (agent key OR admin JWT)

| Method | Path | Body / Purpose |
|---|---|---|
| GET | /flyers/avatars | List saved avatars (favorites first) → `{count, avatars:[{id, name, source, image_url, is_favorite, times_used}]}` |
| POST | /flyers/avatars | `{ flyer_id, name, is_favorite? }` — copy that flyer's avatar into the library |
| POST | /flyers/avatars/upload | multipart file + `name` + `source` (upload/heygen/reference) — add an external avatar image |
| PATCH | /flyers/avatars/{id} | `{ name?, is_favorite? }` |
| DELETE | /flyers/avatars/{id} | Remove from library (deletes library file copy) |

Reuse flow: operator likes a render → `POST /flyers/avatars {flyer_id, name}` → later builds pass `avatar_id` for an identical face every time (no AI credits, no variation).

---

## Brand Assets — /flyers/assets (agent key OR admin JWT)

| Method | Path | Body / Purpose |
|---|---|---|
| GET | /flyers/assets?kind= | List uploaded assets → `{count, assets:[{id, name, kind, image_url}]}` |
| POST | /flyers/assets/upload | multipart file + query `name` + `kind` (logo/image/screenshot) — PNG/JPEG/WebP |
| DELETE | /flyers/assets/{id} | Remove asset (deletes file) |

Operator uploads via admin Settings → Brand Assets with a simple name ("uwm logo").
Agent finds by name and passes `logo_asset_id` + `logo_label` to build-flyer / flyer-to-campaign.
Logo composites right-aligned in the footer strip, auto-scaled, aspect preserved.

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

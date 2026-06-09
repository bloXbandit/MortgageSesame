# ORCHESTRATOR: Full Funnel Ad Campaign Builder
# Clawdbot / Hermes — Campaign Generation Mode

## TRIGGER PHRASES
Activate this orchestrator when the request contains any of:
- "build a campaign"
- "build an ad"
- "generate ad copy"
- "create a sales letter"
- "run a full funnel"
- "build FB ads"
- "generate campaign assets"

---

## REQUIRED INPUTS (Collect before starting chain)

Before running any step, confirm these 5 inputs are available.
If any are missing, ask for them. Do NOT fabricate.

```
1. avatar       → declined_buyer | first_timer | equity_prisoner | realtor_client
2. product      → fha | va | dpa | conventional | heloc | dscr | refi
3. proof        → (optional) A real result Kenneth has. e.g. "Closed $390k FHA in 9 days in Bowie MD"
4. market       → MD | DC | both
5. budget_hint  → low ($500-1k/mo) | mid ($1-3k/mo) | scale ($3k+/mo)
```

---

## THE 9-STEP CHAIN

Run steps in order. Each step's output feeds the next.
Do NOT skip steps. Do NOT write copy before strategy is complete.

---

### STEP 0 — LOAD AVATAR
**Skill file:** `00_mortgage-avatar-library.md`
**Action:** Load the full avatar profile for the selected avatar.
Extract:
- Their internal language (exact phrases)
- Their Schwartz awareness stage
- Their biggest fear
- Their hook formula

**Output:** Avatar profile object (used in all subsequent steps)

---

### STEP 1 — EXTRACT OFFER
**Skill file:** `01_offer-templates.md`
**Action:** Load the offer template for the selected product.
Apply it to the avatar — what outcome does THIS avatar specifically want from THIS product?

**Output:** Offer statement + "Why this why now" for this avatar/product combo

---

### STEP 2 — MAP AWARENESS
**Skill file:** `02_schwartz-awareness-guide.md`
**Action:** Confirm the Schwartz stage for this avatar.
Determine the entry point for all copy: what's the FIRST thing every piece of copy says?

**Output:** Confirmed awareness stage + opening line approach

---

### STEP 3 — BUILD MECHANISM
**Skill file:** `03_mechanism-builder.md`
**Action:** Select the 2 most relevant of Kenneth's 8 mechanisms for this avatar/product combo.
These become the "HOW" proof layer in the sales letter and the credibility line in the ads.

**Output:** 2 selected mechanisms + how they're framed for this avatar

---

### STEP 4 — GENERATE 3 ANGLES
**Skill file:** `04_ad-angle-multiplier.md`
**Action:** Generate exactly 3 distinct angles using different angle types.
Must use avatar's internal language. Must not repeat the same opening approach.

**Output:** 3 angle objects (each with opening line, argument, emotion, platform, stage fit)

---

### STEP 5 — BUILD AD CREATIVE (3 units)
**Skill file:** `05_scroll-stopping-creative.md`
**Action:** For each angle, produce one full ad unit:
hook, body copy, image direction, CTA.

**Output:** 3 ad unit objects (deployable, compliance-note included)

---

### STEP 6 — BUILD SALES LETTER
**Skill file:** `06_sales-letter-architect.md`
**Action:** Using the best-performing angle (angle 1 by default, or the one that matches the sales letter best),
build the full sales letter with all 6 sections.

**Output:** Full sales letter object with headline, lead, villain, method, proof, CTA, URL slug

---

### STEP 7 — CRUSH OBJECTIONS
**Skill file:** `07_objection-crusher.md`
**Action:** Select the 2–3 most relevant objections for this avatar.
Weave objection responses into the sales letter sections.
Also generate a 3-email follow-up sequence using the objection framework.

**Output:**
- Updated sales letter with objections woven in
- 3-email follow-up sequence (day 1: proof, day 2: objection, day 3: urgency/re-engage)

---

### STEP 8 — FINAL QA PASS
**Skill file:** `08_generic-language-killer.md`
**Action:** Run ALL output through the banned phrases list, specificity test, human voice test, and compliance checklist.
Fix anything that fails.

**Output:** QA report + final cleaned assets

---

## FINAL OUTPUT PACKAGE

After all 9 steps complete, assemble and return:

```json
{
  "campaign_meta": {
    "avatar": "...",
    "product": "...",
    "market": "...",
    "awareness_stage": "...",
    "primary_mechanism": "...",
    "secondary_mechanism": "...",
    "budget_hint": "..."
  },
  "ad_units": [
    { "angle": 1, "hook": "...", "body": "...", "cta": "...", "image_direction": "...", "compliance_note": "..." },
    { "angle": 2, ... },
    { "angle": 3, ... }
  ],
  "sales_letter": {
    "headline": "...",
    "subheadline": "...",
    "lead_opening": "...",
    "villain_paragraph": "...",
    "method_steps": [...],
    "proof_block": "...",
    "cta_primary": "...",
    "cta_secondary": "...",
    "compliance_footer": "...",
    "url_slug": "..."
  },
  "email_sequence": [
    { "day": 1, "subject": "...", "body": "...", "cta": "..." },
    { "day": 2, "subject": "...", "body": "...", "cta": "..." },
    { "day": 3, "subject": "...", "body": "...", "cta": "..." }
  ],
  "qa_report": {
    "compliance_checklist": {...},
    "final_status": "approved_for_queue",
    "revision_notes": ""
  }
}
```

---

## ROUTING AFTER COMPLETION

Once the chain completes and QA passes:

1. **Ad units** → POST to `/agent/queue-action` as `item_type: social_post`
2. **Sales letter** → POST to `/agent/queue-action` as `item_type: content_item`
3. **Email sequence** → POST to `/agent/queue-action` as `item_type: campaign_step` (×3)
4. **Log the run** → POST to `/agent/report-run` with full output payload

Nothing goes live until you approve it in the Approval Queue at `/approvals`.

---

## WHAT THIS ORCHESTRATOR DOES NOT DO

- Does not publish ads directly to Facebook/Instagram (that requires your ad account — human step)
- Does not buy media (budget decisions are yours)
- Does not create images (provides direction; image creation is a separate tool/human task)
- Does not send emails without approval
- Does not fabricate client testimonials or invent proof points

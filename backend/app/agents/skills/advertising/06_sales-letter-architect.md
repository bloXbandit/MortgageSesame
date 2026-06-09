# SKILL: Sales Letter Architect
# Step 6 of 9 — Landing Page / Long-Form Copy

## WHEN TO USE
After ad creative is defined.
This skill builds the landing page the ad points to.

The sales letter is what converts the click into a booked call or a lead captured.
The ad gets the click. The sales letter gets the appointment.

---

## WHY A SALES LETTER (NOT A VSL OR SHORT LANDING PAGE)

- A VSL (video sales letter) requires production time and cost. Not needed here.
- A short landing page (just a form) has no persuasion layer — cold traffic bounces.
- A long-form sales letter lets the prospect "skim then dive" — skimmers see the structure,
  engaged readers read every word, both can convert.

The goal: make them feel understood enough that filling out the form or booking feels obvious.

---

## SALES LETTER STRUCTURE (6 Sections)

---

### SECTION 1 — HEADLINE + SUBHEADLINE
**Job:** Speak directly to the avatar. Make the promise clear. Create certainty.
**Length:** 1 headline (10–14 words) + 1 subheadline (1–2 sentences)

**Headline formula:**
"[Specific outcome] for [Avatar] in [Timeframe/Condition] — even if [Biggest objection]"

**Example — Declined Buyer:**
Headline: "Get Your Mortgage Approved in Maryland — Even If Banks Have Already Said No"
Subheadline: "I work with 10+ wholesale lenders. One 'no' from a bank is not a final answer. It's just the wrong door."

**Example — First-Timer:**
Headline: "Buy Your First Home in Maryland with as Little as 3.5% Down — Even If You Think You're Not Ready"
Subheadline: "You don't need 20% down, perfect credit, or a finance degree. You need the right advisor and 15 minutes on a call."

**Compliance:** No rate promises. No approval guarantees. NMLS #1454510 near headline.

---

### SECTION 2 — THE LEAD (First 400–600 words)
**Job:** Expand the headline. Enter the conversation already happening in their head.
Loop the benefit again and again until they want to know HOW.
This section does NOT explain the mechanism yet — it builds desire for it.

**Structure of the lead:**
1. Validate their current situation (show you understand)
2. Name the villain (the bank, the rigid system, the myth they believed)
3. Tease that a solution exists (without fully revealing it yet)
4. Social proof moment — 5 stars, years of experience, real result (framed correctly)

**Example opening lines for Declined Buyer lead:**
"If you've been working hard, paying your bills, and doing everything right — and banks still keep saying no —
I want you to understand something important: it's not you. It's their criteria."

"Banks approve people who fit a mold. If you're a W2 employee with perfect credit and 20% sitting in a savings account —
a bank will love you. But most of us aren't that. Most of us are real people with real situations."

"There is a different path. And it's been sitting right in front of you the whole time."

---

### SECTION 3 — THE VILLAIN FRAME
**Job:** Name the enemy. This is NOT Kenneth's competition — it's the system/belief that's been failing them.
This section validates their frustration and redirects blame from themselves to an external cause.

**The villain for each avatar:**
- Declined Buyer: Rigid retail bank criteria. "One-size-fits-all underwriting."
- First-Timer: The 20% down myth. "Nobody corrected this lie."
- Equity Prisoner: "Your equity is locked and your bank won't tell you how to use it responsibly."
- Realtor's Client: A slow or unresponsive lender who cost someone a house.

**How to use it:**
2–3 paragraphs. Name the problem. Make it structural, not personal.
Then position Kenneth as the alternative structure — not as a salesman.

---

### SECTION 4 — THE METHOD (The "HOW" — 4–5 Steps)
**Job:** Walk them through the exact process. Specificity = certainty = conversion.
This is where the mechanism lives. Make it feel simple.

**Format:** Numbered list, 4–5 steps, each 2–3 sentences.

**Example — Any Avatar:**
1. **15-minute call (free, no credit pull):**
   "We talk through your situation. I ask real questions — not just income and credit score.
   By the end, you know exactly where you stand and what your options are."

2. **I run your numbers across lenders:**
   "I take your profile to the wholesale lenders I work with — UWM, Rocket, NewRez, and others.
   You're not tied to one bank's criteria. I find the right product for your situation."

3. **Same-day pre-approval:**
   "If you're ready to move, I turn the pre-approval letter the same day.
   Your realtor gets what they need. You don't lose a house waiting on paperwork."

4. **I walk you through every step:**
   "From application to closing, you know what's happening and why.
   No black box. No surprises. I pick up the phone."

5. **Close fast:**
   "I've closed loans in as little as 10 business days.
   Most lenders take 30–45 days. Speed is a competitive advantage in this market."

---

### SECTION 5 — PROOF STACK
**Job:** Reinforce that this is real and has worked before.
**Elements to include (use what's available):**

- Zillow 5-star rating + link
- Years of experience (10+)
- NMLS #1454510
- Illustrative client scenario (properly framed as hypothetical if not verified real)
- Markets served (MD & DC)

**Example:**
"I've been doing this in Maryland and DC for over 10 years.
5 stars on Zillow — real clients, real closings. You can read them yourself: [link]
NMLS #1454510. Licensed in MD and DC. Equal Housing Opportunity."

---

### SECTION 6 — CTA + CLOSE
**Job:** Make the next step feel obvious, safe, and low-friction.

**Structure:**
1. Restate the big promise in one sentence
2. Make the CTA feel low-commitment ("free call, no credit pull, no paperwork")
3. One booking button — Cal.com link
4. Secondary CTA for "already ready" prospects — 1003 link (below the fold, clearly labeled)

**Example close:**
"If you've been told no, or you're not sure where to start, or you're sitting on equity you can't figure out how to use —
book a free 15-minute call. No credit pull. No paperwork. Just real answers.

[BOOK A FREE CALL →] https://cal.com/kmanjo-vzz/home-purchase-consultation

Already spoken with me and ready to move forward?
[Start Your Full Application →] https://2704714.my1003app.com/1454510/register

NMLS #1454510 · Maryland & DC · Equal Housing Opportunity
Not a commitment to lend. All loans subject to credit approval."

---

## OUTPUT FORMAT

```json
{
  "headline": "...",
  "subheadline": "...",
  "lead_opening": "First 3 sentences of the lead section",
  "villain_paragraph": "2-3 sentences naming the structural enemy",
  "method_steps": [
    {"step": 1, "title": "...", "body": "..."},
    {"step": 2, "title": "...", "body": "..."},
    {"step": 3, "title": "...", "body": "..."},
    {"step": 4, "title": "...", "body": "..."},
    {"step": 5, "title": "...", "body": "..."}
  ],
  "proof_block": "...",
  "cta_primary": "Button text + destination URL",
  "cta_secondary": "1003 link — only for already-sold prospects",
  "compliance_footer": "NMLS #1454510 · MD & DC · Equal Housing Opportunity · Not a commitment to lend.",
  "url_slug": "suggested URL slug for /campaign/[slug] page"
}
```

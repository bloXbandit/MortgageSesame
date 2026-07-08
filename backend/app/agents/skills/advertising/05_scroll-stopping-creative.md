# SKILL: Scroll-Stopping Creative
# Step 5 of 9 — Ad Creative Production

## WHEN TO USE
After 3 angles are defined.
This skill turns each angle into a deployable ad unit:
hook line, full ad copy body, image direction, and CTA.

One angle = one ad unit.
Three angles = three ad units to A/B/C test.

---

## THE CREATIVE FRAMEWORK

### PART 1 — THE HOOK (First 3 seconds / First sentence)
This is the ONLY thing that matters until the reader decides to keep reading.
If the hook fails, nothing else matters.

**Hook construction rules:**
- Must speak the avatar's internal language (from Skill 00)
- Must create an open loop — curiosity, tension, or a challenged belief
- Must NOT look like an ad (no "LIMITED TIME!" no exclamation spam)
- Must be able to stand alone as a one-line text post
- Maximum 12 words for primary hook. Secondary can extend.

**Hook formulas that work for mortgage:**

FORMULA A — THE PATTERN INTERRUPT FACT
"[Specific number] Maryland buyers got their down payment covered for free last year."

FORMULA B — THE BELIEF CHALLENGE
"You don't need 20% down to buy a house. You never did."

FORMULA C — THE EMPATHY OPEN
"If banks keep saying no — even though you have a job, income, and savings — keep reading."

FORMULA D — THE COST OF INACTION
"Every month you wait, that's another $2,000 building your landlord's equity. Not yours."

FORMULA E — THE IDENTITY STATEMENT
"The first person in your family to own a home doesn't start with perfect credit."

FORMULA F — THE SPEED PROOF
"Same-day pre-approval. 10 business days to close. Your clients won't lose a home waiting on me."

---

### PART 2 — AD COPY BODY
After the hook, the body does 3 things in sequence:

1. **EXPAND THE HOOK** — deliver on the promise made in the first line (2–3 sentences)
2. **THE MECHANISM** — explain the "how" in simple human terms (2–3 sentences)
3. **REMOVE THE RISK** — make the CTA feel safe and low-commitment (1–2 sentences)

**Body length:** 80–150 words for Facebook/Instagram. 40–60 words for Instagram story.
Do NOT write 300-word ad copy. If it requires that much explaining, the angle is wrong.

---

### PART 3 — IMAGE / CREATIVE DIRECTION
The image does the job of stopping the scroll before the copy is even read.

**What works for mortgage in 2024–2025:**
- Candid photo of [BANKER_NAME] — at a table, on the phone, outside a home — no heavy editing
- Real family receiving keys or celebrating — stock only if it looks genuinely candid
- Text overlay: MAXIMUM 5 words, large font, high contrast
- Color: Warm backgrounds ([BANKER_NAME]'s brand: #ffedd2 buttermilk / #1f1f1f carbon / #f5c87a gold)

**What does NOT work:**
- Stock photo of a perfect nuclear family in a perfect house
- Heavy graphic design with multiple fonts and colors
- Blue/white bank-looking design
- Anything that looks like it came from Canva mortgage templates

**Creative direction format:**
"[Photo type]: [Subject]: [Setting]: [Mood]: [Text overlay if any]"

Example:
"Candid phone photo: Kenneth sitting at a kitchen table, looking at laptop with a slight smile: warm natural light: relaxed and approachable: Text overlay: 'Same day. Every time.'"

---

### PART 4 — CTA (Call to Action)
One action. Make it feel safe.

**CTA options by avatar:**

| Avatar | Best CTA |
|---|---|
| Declined Buyer | "Find out why — free call, no credit pull" |
| First-Timer | "See what you actually qualify for — takes 5 minutes" |
| Equity Prisoner | "Run the numbers — no commitment" |
| Realtor's Client | "Book a 15-min call — walk away with real answers" |
| Realtor | "Let's connect — 10 minutes, I'll show you what I bring to your clients" |

**Never use:**
- "Apply Now" (too high-commitment for cold/warm audiences)
- "Get Pre-Approved Today" (too much pressure)
- "Click Here" (no context, no reason to click)
- "Learn More" alone without what they're learning

---

## OUTPUT FORMAT

For each ad unit, output:

```json
{
  "angle_number": 1,
  "hook": "The exact hook line",
  "ad_copy_body": "Full ad copy text, paragraphs separated by newlines",
  "cta_text": "The call to action text",
  "cta_destination": "booking_link | intake_form | realtor_page | campaign_landing_page",
  "image_direction": "Candid/specific description of what the image should look like",
  "text_overlay": "5 words max, or null if no overlay",
  "platform_primary": "facebook | instagram_feed | instagram_story | both",
  "estimated_audience": "Cold | Warm | Hot",
  "compliance_note": "Any compliance flag or NMLS #[BANKER_NMLS] placement note"
}
```

---

## COMPLIANCE LAYER (Non-Negotiable)
Every ad must include NMLS #[BANKER_NMLS] in the ad copy body or caption.
No rate claims. No approval guarantees.
Soft CTA only — never "apply now" for cold audiences.
If a real client scenario is referenced, must be framed as illustrative unless written permission obtained.

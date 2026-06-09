# SKILL: Generic Language Killer — QA Pass
# Step 8 of 9 — Final Polish Before Approval Queue

## WHEN TO USE
Run this as the LAST pass on every piece of copy before it routes to the Approval Queue.
Every ad, every sales letter section, every email subject line, every CTA.

Rule: Clear > Clever. Human > Polished. Specific > Broad.

---

## THE KILL LIST — Banned Words and Phrases

These are the phrases that make mortgage copy sound like every other mortgage company.
If any of these appear in the output, REPLACE immediately with the specific alternative.

| BANNED | REPLACE WITH |
|---|---|
| "seamless process" | Describe the actual steps ("pre-approval same day, close in 10 business days") |
| "your dream home" | "the house you want" or "a home you own" |
| "your mortgage journey" | Delete entirely. Nobody uses this phrase in real life. |
| "hassle-free" | What specifically is removed? ("no 45-day wait, no runaround") |
| "dedicated team" | Kenneth is one person. "I'll be your point of contact from first call to closing." |
| "personalized service" | What specifically is personalized? ("I run your numbers across 10+ lenders, not one") |
| "competitive rates" | Rates are wholesale. Say why. Or don't mention rates at all. |
| "we're here for you" | Too vague. "I pick up the phone. Every time." |
| "proven track record" | Show the proof. "5-star Zillow. 10+ years. 10-day close." |
| "trusted advisor" | Others decide if you're trusted. Show proof. Don't claim it. |
| "stress-free" | What specifically is removed? |
| "I've got you covered" | Vague. What specifically is covered? |
| "reach your goals" | What goal? Be specific. "get the keys to a home in PG County" |
| "take the next step" | What is the step? "Book a 15-minute call at [link]" |
| "let us help you" | Too passive. Make an offer. "Book a call — I'll run your numbers free." |
| "today's competitive market" | Cliché. Delete or replace with a real market fact. |
| "industry-leading" | Says who? Delete or replace with specific proof. |
| "cutting-edge" | Meaningless in mortgage context. Delete. |
| "solutions" | Replace with what the solution actually is. |
| "leverage" (non-financial) | Only use in actual financial leverage context. |
| "synergy" | Delete always. |
| "empower you" | Delete. Show them the specific capability instead. |
| "game-changer" | Show why. Don't claim it. |
| "state-of-the-art" | What is state-of-the-art about a mortgage process? Delete. |

---

## THE SPECIFICITY TEST

For every claim in the copy, ask: **Can I make this more specific?**

| VAGUE | SPECIFIC |
|---|---|
| "fast closing" | "Close in as little as 10 business days" |
| "low down payment" | "As little as 3.5% down with FHA" |
| "many lenders" | "UWM, Rocket, NewRez, and more" |
| "experienced" | "10+ years, senior mortgage advisor, MD & DC licensed" |
| "great reviews" | "5-star Zillow rating — read them at [link]" |
| "down payment help" | "Maryland DPA grants — some buyers receive $10,000+" |
| "quick pre-approval" | "Same business day pre-approval" |
| "I'll explain everything" | "I explain every step in plain language — no jargon, no paperwork surprises" |

---

## THE HUMAN VOICE TEST

Read the copy out loud. If Kenneth would not actually say it in a conversation, rewrite it.

**Test questions:**
1. Does this sound like a person or a bank brochure?
2. Would a 35-year-old from PG County understand every word without googling anything?
3. Does any sentence start with "In today's market..."? (Delete it. Start with the human truth instead.)
4. Is there an exclamation point where there shouldn't be one? (Max 1 per full ad unit)
5. Does any paragraph start with "We believe..."? (Rewrite to show, not tell.)

---

## THE COMPLIANCE FINAL CHECK

Before routing to Approval Queue, confirm ALL of the following:

- [ ] NMLS #1454510 appears in copy or caption
- [ ] No specific interest rate stated ("X.X%") unless it's a clearly labeled example rate with disclaimer
- [ ] No guaranteed approval language ("you will qualify," "guaranteed to close," "100% approval")
- [ ] No fake urgency ("offer expires tonight," "only 3 spots left") unless factually true
- [ ] Any client scenario is framed as illustrative if not verified real ("for example" / "as an illustration")
- [ ] CTA is soft for cold/warm traffic ("book a free call" not "apply now")
- [ ] "Equal Housing Opportunity" or "Equal Housing Lender" present on landing pages
- [ ] No income or employment promises ("you'll save $X/month guaranteed")

---

## OUTPUT FORMAT

Return a compliance and quality report alongside the cleaned copy:

```json
{
  "banned_phrases_found": ["list of any banned phrases that were replaced"],
  "replacements_made": [
    {"original": "...", "replacement": "..."}
  ],
  "specificity_upgrades": [
    {"original": "...", "upgraded": "..."}
  ],
  "compliance_checklist": {
    "nmls_present": true,
    "no_rate_claims": true,
    "no_approval_guarantees": true,
    "no_fake_urgency": true,
    "scenarios_properly_framed": true,
    "soft_cta": true,
    "equal_housing_on_landing": true
  },
  "human_voice_score": "pass | needs_revision",
  "human_voice_notes": "Any lines that still sound corporate and need revision",
  "final_status": "approved_for_queue | needs_revision",
  "revision_notes": "If needs_revision — what specifically to fix"
}
```

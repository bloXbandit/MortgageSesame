# SKILL: Ad Angle Multiplier
# Step 4 of 9 — Generate 3 Distinct Angles Per Campaign

## WHEN TO USE
After awareness stage is diagnosed and mechanisms are selected.
Before writing actual creative or copy.

An "angle" is the specific emotional entry point the ad uses.
Same product. Same avatar. Three completely different doors into their head.
You test all three. One will outperform. You scale that one.

---

## THE 6 ANGLE TYPES (Mortgage-Specific)

### ANGLE TYPE 1 — THE MYTH BUSTER
Calls out a false belief the avatar holds and flips it.
Most powerful for Stage 1–2 awareness.

**Structure:** "You've been told [false belief]. Here's what's actually true: [truth]."

**Example — First-Timer:**
"You've been told you need 20% down to buy a house. That hasn't been true since 1934."

**Example — Declined Buyer:**
"You've been told your credit isn't good enough. But most declines aren't about credit — they're about which lender you asked."

**Works because:** People pay immediate attention when a belief they hold is challenged.
The brain stops scrolling to resolve cognitive dissonance.

---

### ANGLE TYPE 2 — THE PROBLEM AGITATOR
Amplifies the pain of staying stuck. Makes inaction feel costly.
Most powerful for Stage 2 awareness.

**Structure:** [Current pain] is costing you [specific cost]. Here's the math.

**Example — Equity Prisoner:**
"You paid $2,200 in rent last year — to your credit card company, not your mortgage.
Meanwhile you have $140,000 sitting in home equity doing nothing.
That math doesn't have to stay that way."

**Example — Declined Buyer:**
"Every month you wait to figure out why you keep getting declined, rent eats another $2,000.
That's $24,000 a year building someone else's equity. Not yours."

**Works because:** Makes the cost of inaction concrete, not abstract. Creates urgency without fake scarcity.

---

### ANGLE TYPE 3 — THE PROOF STORY
Uses a real or illustrative scenario to make the outcome tangible.
Works across all stages. Most powerful for building trust.

**Structure:** [Avatar-like person] had [exact problem]. Here's what happened.

**Example — Declined Buyer:**
"A buyer came to me after getting declined twice — once at a big bank, once online.
Same income. Same job. Different lender criteria.
We closed in 18 days. FHA. 3.5% down. Same buyer."

**Example — First-Timer:**
"First-time buyer in PG County. Thought she needed $40,000 saved.
Maryland DPA program covered her entire down payment.
She moved in with $4,200 out of pocket."

**Works because:** Specificity makes it believable. The reader puts themselves in the story.

**Compliance note:** If real client, use only with written permission. If illustrative, must be clearly framed as a hypothetical scenario ("For example" / "Illustrative scenario").

---

### ANGLE TYPE 4 — THE MECHANISM REVEAL
Introduces the "new way" — the mechanism that makes the outcome possible.
Most powerful for Stage 2–3 awareness (they know the problem, don't know the solution).

**Structure:** Most people try [old way]. Here's what actually works: [mechanism].

**Example — Declined Buyer:**
"Most people go to their bank when they want a mortgage. Banks have one set of rules.
I work with 10+ wholesale lenders — each with different criteria.
One 'no' at a bank is not the end. It's just the wrong door."

**Example — Equity Prisoner:**
"Most people think refinancing means starting over.
A HELOC lets you tap your equity without touching your existing rate.
You keep the rate you have. You access the cash you built. Different product entirely."

**Works because:** Educates while selling. Makes them feel like they learned something valuable — which creates reciprocity.

---

### ANGLE TYPE 5 — THE DIRECT PROOF / CREDIBILITY
Leads with proof first. Social validation, ratings, results.
Most powerful for Stage 4 awareness (they're comparing, they just need to pick).

**Structure:** [Specific proof] → [CTA]

**Example — Realtor's Client:**
"5 stars on Zillow. Same-day pre-approval. 10 business day close.
If your lender can't say the same — book a call."

**Example — Anyone stage 4:**
"10+ years in MD & DC mortgage. I've seen the edge cases.
I'll tell you honestly what you qualify for — and what you don't.
That call is free. The clarity is priceless."

**Works because:** Removes comparison friction. They're already looking for reasons to choose — give them the proof.

---

### ANGLE TYPE 6 — THE IDENTITY PLAY
Speaks to who they ARE, not just what they want.
Most powerful for first-timers and veterans (VA).

**Structure:** "People like you [do this thing]. You're one step away."

**Example — VA:**
"You gave years to this country.
The VA loan is the government's way of saying: you earned a home with $0 down.
Use it."

**Example — First-Timer:**
"The first person in your family to own a home doesn't start with perfect credit.
They start with one call."

**Works because:** Makes the action feel like identity expression, not just a transaction.

---

## OUTPUT FORMAT

For each campaign build, generate exactly 3 angles. Label them by type.
Each angle gets:

```json
{
  "angle_number": 1,
  "angle_type": "myth_buster",
  "opening_line": "The exact first sentence of this angle",
  "core_argument": "2-3 sentence summary of what this angle argues",
  "emotional_target": "The specific emotion this angle aims to create",
  "best_platform": "facebook | instagram | email | sms | all",
  "awareness_stage_fit": "1 | 2 | 3 | 4",
  "mechanism_used": "Which of Kenneth's mechanisms is highlighted"
}
```

---

## RULES

1. No two angles use the same opening approach.
2. At least one angle must be Stage 2 (problem agitation) — that's where the volume is.
3. At least one angle must include a proof element (rating, speed, specific outcome).
4. Never open with "Are you looking for a mortgage?" — that's the worst possible hook.
5. The opening line must work WITHOUT the image — copy does the heavy lifting.
6. Use the avatar's exact internal language from Skill 00 in the opening line.

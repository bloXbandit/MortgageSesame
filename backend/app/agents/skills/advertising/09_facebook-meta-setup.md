# SKILL 09 — Facebook / Meta Ad Setup
# Mortgage-specific campaign structure, targeting, and compliance rules.
# Apply these rules to every Facebook/Instagram ad unit produced by this chain.

---

## CRITICAL COMPLIANCE — READ FIRST

Every mortgage ad on Meta **MUST** use **Special Ad Category: HOUSING**.

This is a Fair Housing Act / HUD requirement. Violating it risks account suspension and legal liability.

**What this means:**
- You CANNOT restrict by: age, gender, ZIP code, radius under 15 miles, race, religion, national origin, familial status, disability
- You CAN target by: city/state/DMA, interests, behaviors, custom audiences, lookalike audiences
- Lookalike audiences are allowed but Meta auto-broadens them under Housing category
- Custom audiences from your own past clients/leads list: allowed and highly effective

**When building the campaign setup block, always include:**
```
Special Ad Category: HOUSING
```
Never omit this. Non-compliance is not optional.

---

## CAMPAIGN STRUCTURE (Meta Ads Manager)

```
Campaign
  └── Objective: LEAD_GENERATION  ← best for mortgage (collects name/phone/email in-app)
      └── Special Ad Category: HOUSING
          └── Ad Set (targeting + budget lives here)
              ├── Geographic targeting
              ├── Detailed targeting (interests/behaviors)
              ├── Custom / Lookalike audiences
              └── Budget + Schedule
                  └── Ad (creative + copy)
                      ├── Headline (primary hook — 40 chars max)
                      ├── Primary text (story/pain/offer — 125 chars above fold)
                      ├── Description (benefit summary)
                      ├── Image (1080×1080 social_square recommended)
                      └── CTA button
```

---

## AD SET RULES (apply to every scenario)

| Setting | Rule |
|---------|------|
| Placement | Facebook Feed + Instagram Feed only. Turn off Audience Network, Marketplace, Right Column. |
| Budget | Minimum $20/day to exit learning phase. $25–40/day recommended for new campaigns. |
| Schedule | Run minimum 5 days before optimizing — Meta needs ~50 conversions to exit learning phase. |
| CTA button | "Learn More" or "Get Quote" — avoid "Apply Now" until warm retargeting stage |
| Pixel | Must be installed on landing page for retargeting and optimization |
| Optimization event | Lead (if pixel + lead event firing) or Landing Page Views |
| Attribution | 7-day click, 1-day view |

---

## SCENARIO TARGETING PLAYBOOK

### 🏠 FIRST-TIME BUYER + DPA
**Campaign hook:** Down payment assistance — remove the #1 barrier
**Targeting:**
- Geography: Maryland + DC metro (DMA level, not ZIP)
- Interests: "First-time home buyer," "Renting an apartment," "Real estate," "Personal finance"
- Behaviors: "Likely to move," "Recently moved"
- Custom audience: Website visitors to /dpa page, email list of renters
- Lookalike: 1% LAL of past FHA/DPA clients
- Exclude: Known homeowners (if suppression list available)
- Budget: $25–35/day
- Best formats: Single image (show a happy family at keys ceremony) or short video

### 🎖 VA LOANS
**Campaign hook:** $0 down, no PMI — earned benefit most veterans don't use
**Targeting:**
- Geography: MD + DC + military-adjacent areas (PG County, Prince William, Anne Arundel)
- Interests: "Veterans," "United States Armed Forces," "Military families," "VA loan"
- Behaviors: "US military veterans" (Meta behavior), "Active duty military"
- Custom audience: Veteran org email lists (if available)
- Lookalike: 1% LAL of past VA clients
- Budget: $20–30/day (smaller audience, higher intent)
- Best formats: Single image — avoid anything that looks like clickbait; veterans respond to direct, respectful copy

### 🏦 FHA PURCHASE
**Campaign hook:** 3.5% down, flexible credit — more people qualify than they think
**Targeting:**
- Geography: Maryland + DC (DMA)
- Interests: "Home buying," "Mortgage," "Real estate," "Credit score improvement"
- Behaviors: "Likely to move," "Recently moved," "First-time home buyer"
- Custom audience: Leads who opened but didn't convert, website visitors
- Budget: $30–40/day (broad audience)
- Best formats: Single image or carousel (show 3 different home price ranges)

### 💰 HELOC / CASH-OUT EQUITY
**Campaign hook:** Your equity is sitting there — put it to work
**Targeting:**
- Geography: MD + DC homeowner-heavy zip areas (use DMA, not ZIP)
- Interests: "Home improvement," "Home equity," "Real estate investing," "Debt consolidation"
- Behaviors: "Homeowners" (Meta behavior — available under Housing category)
- Custom audience: Past purchase clients 2+ years ago (they have equity), website visitors to /heloc or rates page
- Lookalike: 1% LAL of past HELOC/cash-out clients
- Budget: $25–35/day
- Best formats: Single image — show the "before/after" concept (cluttered debt vs. freedom)

### 🔄 REFINANCE (Rate/Term)
**Campaign hook:** Your rate is too high — here's what you could pay instead
**Targeting:**
- Geography: MD + DC
- Interests: "Refinancing," "Mortgage," "Personal finance," "Interest rates"
- Behaviors: "Homeowners"
- Custom audience: Leads from 2020–2022 (bought at higher rates), past clients not yet refinanced
- Budget: $20–30/day (rate-sensitive, timing-dependent — pause if rates rise)
- Best formats: Single image with rate comparison visual

### 🏘 CONVENTIONAL PURCHASE
**Campaign hook:** Skip FHA — conventional can be cleaner and cheaper long-term
**Targeting:**
- Geography: MD + DC
- Interests: "Home buying," "Real estate," "Personal finance," "Mortgage"
- Behaviors: "Likely to move," "Recently moved"
- Custom audience: FHA leads who may now qualify for conventional, website visitors
- Budget: $30–40/day
- Best formats: Single image or carousel

### 📈 DSCR INVESTOR
**Campaign hook:** Buy investment property with rental income — no W2 required
**Targeting:**
- Geography: MD + DC + national (DSCR is nationwide for investors)
- Interests: "Real estate investing," "Rental property," "Passive income," "Landlord," "Real estate investor"
- Behaviors: "Small business owners," "Frequent international travelers" (often investors)
- Custom audience: Past investors, website visitors to rates page
- Lookalike: 1% LAL of past DSCR clients
- Budget: $25–40/day
- Best formats: Single image or video — numbers-driven copy works best

### ❌ DECLINED BUYER COMEBACK
**Campaign hook:** Got turned down? We get buyers approved when others say no
**Targeting:**
- Geography: MD + DC
- Interests: "Home buying," "Credit repair," "Mortgage," "FHA loan"
- Custom audience: Leads marked "declined" or "lost" in your CRM (retarget list)
- Lookalike: 1% LAL of past FHA clients with 580–620 credit range
- Budget: $20–25/day (warm audience focus — retargeting heavy)
- Best formats: Single image — empathetic copy, "second chance" framing

### 🤝 REALTOR PARTNERSHIP
**Campaign hook:** Your buyers need a lender who closes fast — I do it in 10 days
**Targeting:**
- Geography: MD + DC
- Interests: "Real estate agent," "Real estate broker," "Keller Williams," "RE/MAX," "Coldwell Banker," "Real estate"
- Job titles: "Real estate agent," "Realtor," "Real estate broker" (use Detailed Targeting)
- Custom audience: Realtor contacts from your CRM
- Lookalike: 1% LAL of past realtor referral partners
- Budget: $15–25/day (small audience, relationship play)
- Best formats: Video (30s) works best — face-to-camera, professional tone

---

## AD COPY RULES FOR META

1. **Headline (40 chars max):** Lead with the benefit, not the product. "Own a home for less than rent" not "FHA Loan Program Available"
2. **Primary text (125 chars above fold):** Hook first — pain or curiosity. Story follows. CTA at end.
3. **No guaranteed approval language** — "You're guaranteed to qualify" = immediate rejection
4. **No specific rate promises** — "Rates as low as X%" requires APR disclosure in the ad. Avoid in feed ads.
5. **No "best" or "lowest"** without substantiation
6. **NMLS # required** in ad copy or landing page — include it
7. **Equal Housing Opportunity** — include EHO logo or text on landing page
8. **No income/demographic targeting language** in the ad copy itself — "for first-time buyers" is fine; anything that implies exclusion by protected class is not

---

## WHAT TO INCLUDE IN THE CAMPAIGN SETUP OUTPUT

When returning a campaign setup block, always include:

```json
{
  "facebook_setup": {
    "special_ad_category": "HOUSING",
    "objective": "LEAD_GENERATION",
    "ad_set": {
      "geography": "...",
      "interests": [...],
      "behaviors": [...],
      "custom_audiences": [...],
      "lookalike_audiences": [...],
      "exclude": [...],
      "budget_daily": "$X/day",
      "minimum_run": "5 days before optimizing",
      "placements": ["Facebook Feed", "Instagram Feed"],
      "cta_button": "Learn More",
      "optimization_event": "Lead"
    },
    "ad_format": "...",
    "compliance": [
      "Special Ad Category: HOUSING applied",
      "NMLS #[BANKER_NMLS] included",
      "No guaranteed approval language",
      "Equal Housing Opportunity"
    ]
  }
}
```

---

## LEAD FORM (if using Meta Lead Gen forms)

Recommended fields:
1. Full name (pre-filled)
2. Email (pre-filled)
3. Phone number (pre-filled)
4. Custom question: "Are you currently renting or do you own a home?"
5. Custom question: "What's your estimated credit score range?" (580–619 / 620–659 / 660–699 / 700+)

Privacy policy URL: your public site's /privacy or Cal.com booking link
Thank you screen: "We'll call you within 1 business hour" + link to book a call

---

## PIXEL EVENTS TO FIRE

| Page | Event |
|------|-------|
| Campaign page (/campaign/slug) | PageView + ViewContent |
| Intake form submit | Lead |
| Cal.com booking complete | Schedule (custom) |
| /rates page visit | ViewContent |

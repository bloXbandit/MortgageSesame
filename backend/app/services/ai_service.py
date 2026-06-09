"""
AI provider abstraction layer.
Swap the underlying model/provider by changing env vars — no code changes needed.
"""

from openai import AsyncOpenAI
from app.config import settings
import json
from typing import Optional

_NAME  = settings.banker_name
_NMLS  = settings.banker_nmls
_STATE = settings.service_states

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


async def complete(prompt: str, system: str = "", model: Optional[str] = None, max_tokens: int = 1500) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model or settings.ai_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


async def complete_json(prompt: str, system: str = "", model: Optional[str] = None) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model or settings.ai_model,
        messages=messages,
        max_tokens=2000,
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


SCORE_LEAD_SYSTEM = """
You are a senior mortgage advisor AI. You score mortgage leads based on intake data.
You must output JSON with this exact structure:
{
  "score_value": float 0-100,
  "score_label": "hot|warm|long_term|bad_fit",
  "readiness_score": int 1-10,
  "recommended_product": "product name",
  "summary": "2-3 sentence plain-English summary of this lead",
  "questions_for_call": ["question1", "question2", "question3"],
  "recommended_cta": "specific next action for this lead",
  "compliance_response": "Safe, educational response to show the consumer"
}
Never promise approval. Never state specific rates. Flag if data suggests compliance concern.
"""


async def score_lead(intake_data: dict) -> dict:
    prompt = f"Score this mortgage lead:\n{json.dumps(intake_data, indent=2)}"
    return await complete_json(prompt, system=SCORE_LEAD_SYSTEM)


OUTREACH_SYSTEM = """
You are a mortgage banker's outreach assistant. Generate personalized, professional outreach messages.
Rules:
- No guaranteed approval claims
- No misleading rate claims
- No fake urgency
- Include soft CTA (book a call, not "apply now")
- Include opt-out language for email/SMS
- Keep it brief and human — not salesy
- For realtors: focus on partnership value, fast closings, communication
- For consumers: focus on education and readiness
Output JSON: {"subject": "...", "body": "...", "cta": "...", "opt_out": "..."}
"""


async def generate_outreach(contact_data: dict, product_data: dict, goal: str, channel: str) -> dict:
    prompt = (
        f"Generate {channel} outreach for this contact:\n{json.dumps(contact_data, indent=2)}\n\n"
        f"Promoting: {json.dumps(product_data, indent=2)}\n\nGoal: {goal}"
    )
    return await complete_json(prompt, system=OUTREACH_SYSTEM)


CONTENT_SYSTEM = f"""
You are a content creator for {_NAME}, a {_STATE} mortgage banker (NMLS #{_NMLS}).
Generate platform-native social media content. Every piece must be ready to record.

Compliance rules (non-negotiable):
- No guaranteed rate claims ("you'll get X%")
- No promised approvals ("you will qualify")
- No fake testimonials or fabricated closings
- Fictional examples must clearly say "for example" or "hypothetically"
- Include NMLS #{_NMLS} in compliance_notes
- CTA must be soft — never "apply now", always "learn more / DM me / link in bio"

Content rules:
- Hook must stop the scroll in 2 seconds — question, bold stat, or pattern interrupt
- Script must be conversational, not corporate — write how {_NAME} actually speaks
- voiceover_script is the exact words {_NAME} reads into the camera — no stage directions
- visual_concept describes what's ON SCREEN (not what's said)
- broll_instructions: describe B-roll footage to cut to during voiceover
- video_prompt: one vivid sentence for AI video generation (Runway / HeyGen background)
- image_prompt: DALL-E style prompt for a background image if no video
- caption: the text that goes with the post (hashtags optional, CTA at end)

Output ONLY valid JSON with exactly these keys (no extras, no missing):
{{
  "hook": "...",
  "script": "...",
  "voiceover_script": "...",
  "caption": "...",
  "cta": "...",
  "visual_concept": "...",
  "image_prompt": "...",
  "video_prompt": "...",
  "broll_instructions": "...",
  "compliance_notes": "...",
  "is_fictional_example": false,
  "suggested_hashtags": ["mortgage", "homebuying"]
}}
"""


async def generate_content(
    platform: str,
    category: str,
    product_context: str,
    banker_voice: str = "",
    template_context: str = "",
) -> dict:
    """
    Generate a social post. template_context is injected from ScriptTemplates
    pulled from the DB — gives you on-the-fly control without touching code.
    """
    system = CONTENT_SYSTEM
    if template_context:
        system += f"\n\nStyle guidelines from your saved templates:\n{template_context}"

    platform_notes = {
        "tiktok":              "TikTok: 15–60 sec, vertical 9:16, hook in first 2s, trending audio vibe",
        "instagram_reel":      "Instagram Reel: 15–90 sec, vertical 9:16, polished but real",
        "instagram_carousel":  "Instagram Carousel: 5-10 slides, each slide = 1 insight, swipe-worthy",
        "facebook":            "Facebook: can be 1-3 min, more conversational, community feel",
        "linkedin":            "LinkedIn: professional tone, 60-90 sec, value-first, no fluff",
        "google_business":     "Google Business: short update, local market focus, CTA to call or book",
        "email_snippet":       "Email snippet: 2-3 sentences for email nurture sequence, personable",
    }
    plat_note = platform_notes.get(platform, f"Platform: {platform}")

    prompt = (
        f"Create {platform} content for the '{category}' topic.\n"
        f"Platform specs: {plat_note}\n"
        f"Product context: {product_context or 'General mortgage education'}\n"
        f"Banker voice/tone: {banker_voice or 'conversational, local market expert, approachable, direct'}\n"
        f"\nGenerate content that {_NAME} can read directly on camera. Make it real, not corporate."
    )
    result = await complete_json(prompt, system=system)

    # Ensure all expected keys are present
    REQUIRED = [
        "hook", "script", "voiceover_script", "caption", "cta",
        "visual_concept", "image_prompt", "video_prompt", "broll_instructions",
        "compliance_notes", "is_fictional_example", "suggested_hashtags",
    ]
    for key in REQUIRED:
        if key not in result:
            result[key] = [] if key == "suggested_hashtags" else ("" if key != "is_fictional_example" else False)

    return result

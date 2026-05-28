"""
AI provider abstraction layer.
Swap the underlying model/provider by changing env vars — no code changes needed.
"""

from openai import AsyncOpenAI
from app.config import settings
import json

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


async def complete(prompt: str, system: str = "", model: str | None = None, max_tokens: int = 1500) -> str:
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


async def complete_json(prompt: str, system: str = "", model: str | None = None) -> dict:
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


CONTENT_SYSTEM = """
You are a mortgage content creator. Generate social media content for a mortgage banker.
Rules:
- Educational, not promotional spam
- Fictional examples must be labeled as examples
- No fake testimonials, no fake closings
- Include compliance notes
- Hook must stop the scroll
- CTA must be soft (learn more, DM me, link in bio)
Output JSON: {
  "hook": "...",
  "script": "...",
  "caption": "...",
  "cta": "...",
  "visual_concept": "...",
  "image_prompt": "...",
  "voiceover_script": "...",
  "compliance_notes": "...",
  "is_fictional_example": bool
}
"""


async def generate_content(platform: str, category: str, product_context: str, banker_voice: str = "") -> dict:
    prompt = (
        f"Create {platform} content in the '{category}' category.\n"
        f"Product context: {product_context}\n"
        f"Banker voice/tone: {banker_voice or 'professional, approachable, local market expert'}"
    )
    return await complete_json(prompt, system=CONTENT_SYSTEM)

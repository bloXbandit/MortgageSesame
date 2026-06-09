"""
ElevenLabs voice connector.

Used by the agent to generate voiceovers for ad scripts, outreach audio, and content narration.
The agent already has its own voice configured — this connector just calls the API.

For phone outreach: your agent's SignalWire number handles the call flow.
ElevenLabs generates the audio; SignalWire streams it or plays LAML.
See agent/voice_integration.md for the full setup.
"""

import httpx
from app.config import settings
from typing import Optional


BASE_URL = "https://api.elevenlabs.io/v1"


async def generate_audio(text: str, voice_id: Optional[str] = None) -> bytes:
    """Generate speech from text. Returns raw MP3 bytes."""
    vid = voice_id or settings.elevenlabs_voice_id
    if not settings.elevenlabs_api_key or not vid:
        raise RuntimeError("ElevenLabs not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL}/text-to-speech/{vid}",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        )
        response.raise_for_status()
        return response.content


async def list_voices() -> list[dict]:
    """List all available voices in the account."""
    if not settings.elevenlabs_api_key:
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{BASE_URL}/voices",
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
        response.raise_for_status()
        return response.json().get("voices", [])


async def get_voice_by_name(name: str) -> Optional[dict]:
    voices = await list_voices()
    return next((v for v in voices if v["name"].lower() == name.lower()), None)

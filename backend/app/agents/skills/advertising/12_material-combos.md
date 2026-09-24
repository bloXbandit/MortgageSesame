# SKILL 12 — Material Combos
# How to pick and assemble creative materials (flyer / video / voice) for a campaign.
# The goal: reuse what exists, generate only what's needed, match the combo to
# budget + platform.

---

## THE MATERIALS STACK

The system can produce four material types:

| Material | How it's made | Cost | Speed |
|----------|--------------|------|-------|
| **Flyer** (graphic) | Reference photo → AI avatar → branded composite | Free (Pillow) | Seconds |
| **Voice** (audio) | Script → ElevenLabs clone voice | Cheap (~cents) | Seconds |
| **Video** (avatar) | Script → HeyGen avatar + cloned voice | ~$0.10/min + credits | Minutes |
| **Copy** | LLM skill chain (this file's siblings) | Cheap | Seconds |

---

## THE 5 COMBOS

### 1. STATIC — Flyer + Ad Copy
- **Materials:** 1 flyer (social_square 1080×1080) + 3 ad copy units
- **Best for:** Facebook/Instagram feed, lowest budget, fastest launch
- **Cost:** Free
- **When to pick:** budget_hint `low`, placements are Feed-only, operator wants to test copy before spending on video

### 2. VIDEO — HeyGen Avatar Video + Ad Copy
- **Materials:** 1 avatar video (script = ad hook + body, ~30–45s) + 3 ad copy units
- **Best for:** Instagram Reels, Facebook video placements, story formats
- **Cost:** HeyGen credits (~$0.10/min)
- **When to pick:** placements include Reels/Stories, budget_hint `mid`+, goal is engagement or booked calls
- **Aspect ratio:** 9:16 for reels/story, 1:1 for feed — decide from the template's placements

### 3. VOICE_GRAPHIC — Voiceover + Flyer
- **Materials:** 1 voice MP3 (ElevenLabs) + 1 flyer — can be overlaid in stories or used in video editors
- **Best for:** Instagram story with audio, repurposing into video later
- **Cost:** Cheap
- **When to pick:** operator wants audio presence but no avatar video yet

### 4. FULL_STACK — Flyer + Video + Voice + Email Sequence
- **Materials:** Everything — flyer for feed ads, video for reels, voice for overlays, 3-email follow-up
- **Best for:** Complete campaign launch across all placements
- **Cost:** Highest
- **When to pick:** budget_hint `scale`, committed campaign with real spend behind it

### 5. REPURPOSE — Existing Flyer/Video + New Copy
- **Materials:** Reuse an existing flyer or video from the materials inventory + fresh angles/copy
- **Best for:** Iterating on a scenario without regenerating visuals
- **Cost:** Free
- **When to pick:** materials inventory already has a flyer/video that fits the avatar+product

---

## DECISION RULES

1. **Check inventory first.** If a completed flyer or video already fits the avatar + product, use REPURPOSE.
2. **Budget gates video.** budget_hint `low` → static or repurpose. `mid` → video or voice_graphic. `scale` → full_stack.
3. **Platform gates aspect ratio.** Placements with Reels/Stories → 9:16 video. Feed-only → 1:1.
4. **Realtor B2B → video first.** Face-to-camera trust matters more than graphics for agent referral plays.
5. **Cold traffic → flyer first.** Static images outperform avatar videos for cold mortgage audiences in most tests. Video wins in retargeting and warm traffic.
6. **Never generate video without a script.** The video script comes from the winning ad angle's hook + body — not a separate script.

---

## HOW TO ASSEMBLE

```
material_combo = pick_combo(budget_hint, placements, inventory)

if material_combo in ("video", "full_stack"):
    video_script = build_video_script(winning_angle)   # 30–45s, hook-first
    aspect_ratio = "9:16" if reels_or_story else "1:1"
    video = generate_video(script=video_script, aspect_ratio=aspect_ratio)

if material_combo in ("static", "full_stack", "voice_graphic") and no_existing_flyer:
    flyer = generate_flyer(headline, subheadline, cta_text, format)

if material_combo in ("voice_graphic", "full_stack"):
    voice = generate_voice(ad_hook_script)

# Copy always generated — flyers/videos are visual anchors, copy is the persuasion
ad_units = generate_ad_units(angles, flyer_or_video_url)
email_sequence = generate_emails(flyer_image_url)
```

---

## OUTPUT BLOCK (add to campaign package)

```json
{
  "material_combo": "video",
  "materials": {
    "flyer_image_url": "http://.../media/flyers/abc.jpg",
    "video_url": "https://.../video.mp4",
    "video_provider_id": "heygen_xxx",
    "video_aspect_ratio": "9:16",
    "video_status": "processing | completed",
    "voice_url": "http://.../media/voice.mp3"
  },
  "cost_estimate": "HeyGen ~$0.10 + ElevenLabs ~$0.02",
  "rationale": "Reels placement in template + mid budget → video combo. Reused existing flyer for feed placements."
}
```

---

## RULES (non-negotiable)

- Always report which materials were reused vs newly generated.
- Always include `video_status` — HeyGen renders are async; "processing" means poll later.
- Never burn HeyGen credits when `video_test_mode` is on without telling the operator the video is watermarked.
- If `video_provider` is `mock`, tell the operator videos are simulated and how to flip to `heygen`.
- If no reference photo is uploaded, tell the operator likeness-based creative is unavailable and prompt them to upload one first.

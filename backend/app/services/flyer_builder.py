"""
Flyer Builder — Pillow-based branded flyer compositing.

Takes a generated avatar image and composes it onto a branded template.
All templates use MortgageSesame brand colors and typography.

Templates:
  social_square   — 1080×1080  (Instagram, Facebook post)
  facebook_banner — 1200×628   (Facebook/LinkedIn cover, ad banner)
  story           — 1080×1920  (Instagram/Facebook Story)
  wide_banner     — 1500×500   (Twitter header, email banner)

Usage:
    result = build_flyer(
        avatar_image_path="/path/to/avatar.jpg",
        headline="Get Pre-Approved Today",
        subheadline="Same-day results. No pressure.",
        cta_text="Book a Free Call →",
        use_case="purchase",
        flyer_format="social_square",
        banker_name="Your Name",
        banker_nmls="XXXXXX",
    )
    # result = {"path": "...", "url": "..."}
"""

import os
import uuid
import textwrap
import structlog
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from app.config import settings

log = structlog.get_logger()

# ── Brand colors ─────────────────────────────────────────────────────────────

DARK    = (31, 31, 31)       # #1f1f1f
GOLD    = (245, 200, 122)    # #f5c87a
CREAM   = (255, 251, 245)    # #fffbf5
WHITE   = (255, 255, 255)
GRAY    = (136, 136, 136)    # #888
DARK2   = (42, 42, 42)       # #2a2a2a
GOLD_DIM = (200, 134, 10)    # #c8860a


# ── Font loader ───────────────────────────────────────────────────────────────

_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates_bold = [
        "/System/Library/Fonts/Helvetica.ttc",        # macOS (index 1 = bold)
        "/System/Library/Fonts/SFCompact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    candidates_regular = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    candidates = candidates_bold if bold else candidates_regular
    for path in candidates:
        if Path(path).exists():
            try:
                # For .ttc files, index 1 is usually bold
                idx = 1 if (bold and path.endswith(".ttc")) else 0
                f = ImageFont.truetype(path, size, index=idx)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                continue

    f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


# ── Text helpers ──────────────────────────────────────────────────────────────

def _draw_text_wrapped(draw, text: str, x: int, y: int, max_width: int,
                        font: ImageFont.FreeTypeFont, color: tuple,
                        line_spacing: int = 8) -> int:
    """Draw wrapped text, return final y position."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def _draw_pill_button(draw, x: int, y: int, text: str, font, bg=GOLD, fg=DARK, padding_x=28, padding_h=18):
    """Draw a rounded-rect pill button, return (x2, y2)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x2 = x + tw + padding_x * 2
    y2 = y + th + padding_h * 2
    draw.rounded_rectangle([x, y, x2, y2], radius=10, fill=bg)
    draw.text((x + padding_x, y + padding_h), text, font=font, fill=fg)
    return x2, y2


def _paste_avatar(base: Image.Image, avatar: Image.Image,
                  box: tuple, blend_left: bool = True) -> Image.Image:
    """
    Resize avatar to fill `box` (x, y, w, h) and paste onto base.

    If the avatar has an alpha channel (RGBA — from rembg background removal),
    uses it as the composite mask so the person is cleanly cut out.
    Optionally blends the left edge with a gradient for seamless integration.

    If the avatar is RGB (no background removal), falls back to the original
    gradient-mask approach.
    """
    from PIL import ImageChops

    x, y, w, h = box
    avatar_resized = avatar.resize((w, h), Image.LANCZOS)

    if avatar_resized.mode == "RGBA":
        # ── Clean cutout from rembg ───────────────────────────────────────────
        if blend_left:
            # Fade left edge of the existing alpha so the cutout blends smoothly
            r, g, b, a = avatar_resized.split()
            blend_w = min(w // 4, 120)
            gradient = Image.new("L", (w, h), 255)
            g_draw = ImageDraw.Draw(gradient)
            for i in range(blend_w):
                g_draw.line([(i, 0), (i, h)], fill=int(255 * (i / blend_w)))
            # Multiply avatar's own alpha by the gradient → fades left edge only
            faded_a = ImageChops.multiply(a, gradient)
            avatar_resized.putalpha(faded_a)
        base.paste(avatar_resized, (x, y), avatar_resized)

    else:
        # ── RGB avatar (no bg removal) — gradient mask approach ───────────────
        avatar_rgb = avatar_resized.convert("RGB")
        if blend_left:
            mask = Image.new("L", (w, h), 255)
            mask_draw = ImageDraw.Draw(mask)
            blend_w = min(w // 3, 200)
            for i in range(blend_w):
                mask_draw.line([(i, 0), (i, h)], fill=int(255 * (i / blend_w)))
            base.paste(avatar_rgb, (x, y), mask)
        else:
            base.paste(avatar_rgb, (x, y))

    return base


# ── Template builders ─────────────────────────────────────────────────────────

def _build_social_square(avatar: Optional[Image.Image], headline: str,
                          subheadline: str, cta: str,
                          banker_name: str, banker_nmls: str) -> Image.Image:
    """1080 × 1080 — Instagram / Facebook post."""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # Avatar — right 58%, full height
    if avatar:
        avatar_x = int(W * 0.42)
        _paste_avatar(img, avatar, (avatar_x, 0, W - avatar_x, H), blend_left=True)

    # Gold left accent bar
    draw.rectangle([0, 0, 8, H], fill=GOLD)

    # Brand label
    text_x = 52
    draw.text((text_x, 56), settings.app_name.upper(), font=_font(22), fill=GOLD)
    draw.line([(text_x, 94), (text_x + 160, 94)], fill=GOLD, width=2)

    # Headline
    y = 130
    y = _draw_text_wrapped(draw, headline, text_x, y, int(W * 0.42) - 60,
                            _font(64, bold=True), WHITE, line_spacing=10)

    # Subheadline
    if subheadline:
        y += 24
        y = _draw_text_wrapped(draw, subheadline, text_x, y, int(W * 0.42) - 60,
                                _font(30), GRAY, line_spacing=8)

    # CTA button
    if cta:
        y += 40
        _draw_pill_button(draw, text_x, y, cta, _font(26, bold=True))

    # Bottom NMLS bar
    bar_h = 70
    draw.rectangle([0, H - bar_h, W, H], fill=DARK2)
    nmls_text = f"NMLS #{banker_nmls}  ·  {banker_name}  ·  Equal Housing Opportunity"
    draw.text((text_x, H - bar_h + 22), nmls_text, font=_font(18), fill=GRAY)

    return img


def _build_facebook_banner(avatar: Optional[Image.Image], headline: str,
                            subheadline: str, cta: str,
                            banker_name: str, banker_nmls: str) -> Image.Image:
    """1200 × 628 — Facebook/LinkedIn ad banner."""
    W, H = 1200, 628
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # Avatar — right 50%
    if avatar:
        av_x = W // 2
        _paste_avatar(img, avatar, (av_x, 0, W - av_x, H), blend_left=True)

    # Gold left bar
    draw.rectangle([0, 0, 6, H], fill=GOLD)

    text_x = 48
    draw.text((text_x, 44), settings.app_name.upper(), font=_font(18), fill=GOLD)

    y = 100
    y = _draw_text_wrapped(draw, headline, text_x, y, W // 2 - 80,
                            _font(52, bold=True), WHITE, line_spacing=8)

    if subheadline:
        y += 18
        y = _draw_text_wrapped(draw, subheadline, text_x, y, W // 2 - 80,
                                _font(26), GRAY, line_spacing=6)

    if cta:
        y += 30
        _draw_pill_button(draw, text_x, y, cta, _font(22, bold=True))

    # Footer
    footer_text = f"NMLS #{banker_nmls}  ·  Equal Housing Opportunity  ·  {banker_name}"
    draw.text((text_x, H - 36), footer_text, font=_font(15), fill=GRAY)

    return img


def _build_story(avatar: Optional[Image.Image], headline: str,
                  subheadline: str, cta: str,
                  banker_name: str, banker_nmls: str) -> Image.Image:
    """1080 × 1920 — Instagram / Facebook Story."""
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # Avatar — top 55%, full width, no blend
    if avatar:
        av_h = int(H * 0.55)
        _paste_avatar(img, avatar, (0, 0, W, av_h), blend_left=False)

        # Gradient from avatar bottom into text section
        grad_h = 200
        grad_y = av_h - grad_h
        for y_offset in range(grad_h):
            alpha = int(255 * (y_offset / grad_h))
            draw.line([(0, grad_y + y_offset), (W, grad_y + y_offset)],
                      fill=(*DARK, alpha))
    else:
        # Decorative geometric background
        draw.rectangle([0, 0, W, int(H * 0.55)], fill=DARK2)

    # Gold accent bar at divider
    div_y = int(H * 0.56)
    draw.rectangle([0, div_y, W, div_y + 6], fill=GOLD)

    text_x = 72
    text_max_w = W - text_x * 2

    y = div_y + 56
    draw.text((text_x, y - 40), settings.app_name.upper(), font=_font(24), fill=GOLD)

    y = _draw_text_wrapped(draw, headline, text_x, y, text_max_w,
                            _font(76, bold=True), WHITE, line_spacing=12)

    if subheadline:
        y += 28
        y = _draw_text_wrapped(draw, subheadline, text_x, y, text_max_w,
                                _font(36), GRAY, line_spacing=8)

    if cta:
        y += 48
        # Full-width button on story
        btn_w = W - text_x * 2
        draw.rounded_rectangle([text_x, y, text_x + btn_w, y + 88], radius=14, fill=GOLD)
        bbox = draw.textbbox((0, 0), cta, font=_font(34, bold=True))
        tx = text_x + (btn_w - (bbox[2] - bbox[0])) // 2
        draw.text((tx, y + 24), cta, font=_font(34, bold=True), fill=DARK)

    # Bottom compliance bar
    draw.rectangle([0, H - 90, W, H], fill=DARK2)
    footer = f"NMLS #{banker_nmls}  ·  {banker_name}  ·  Equal Housing Opportunity"
    bbox = draw.textbbox((0, 0), footer, font=_font(22))
    fx = (W - (bbox[2] - bbox[0])) // 2
    draw.text((fx, H - 58), footer, font=_font(22), fill=GRAY)

    return img


def _build_wide_banner(avatar: Optional[Image.Image], headline: str,
                        subheadline: str, cta: str,
                        banker_name: str, banker_nmls: str) -> Image.Image:
    """1500 × 500 — email header / Twitter banner / website hero."""
    W, H = 1500, 500
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # Avatar — right 40%
    if avatar:
        av_x = int(W * 0.60)
        _paste_avatar(img, avatar, (av_x, 0, W - av_x, H), blend_left=True)

    draw.rectangle([0, 0, 6, H], fill=GOLD)

    text_x = 60
    draw.text((text_x, 40), settings.app_name.upper(), font=_font(20), fill=GOLD)

    y = 100
    y = _draw_text_wrapped(draw, headline, text_x, y, int(W * 0.55) - 80,
                            _font(60, bold=True), WHITE, line_spacing=8)

    if subheadline:
        y += 16
        y = _draw_text_wrapped(draw, subheadline, text_x, y, int(W * 0.55) - 80,
                                _font(28), GRAY, line_spacing=6)

    if cta:
        y += 28
        _draw_pill_button(draw, text_x, y, cta, _font(24, bold=True))

    draw.text((text_x, H - 34), f"NMLS #{banker_nmls}  ·  Equal Housing Opportunity", font=_font(16), fill=GRAY)

    return img


# ── Public build function ──────────────────────────────────────────────────────

TEMPLATE_MAP = {
    "social_square":   _build_social_square,
    "facebook_banner": _build_facebook_banner,
    "story":           _build_story,
    "wide_banner":     _build_wide_banner,
}


def build_flyer(
    avatar_image_path: Optional[str],
    headline: str,
    subheadline: str = "",
    cta_text: str = "",
    flyer_format: str = "social_square",
    banker_name: Optional[str] = None,
    banker_nmls: Optional[str] = None,
) -> dict:
    """
    Composite a branded flyer.

    Returns {"path": str, "url": str} on success.
    Raises on failure.
    """
    banker_name = banker_name or settings.banker_name
    banker_nmls = banker_nmls or settings.banker_nmls

    # Load avatar image if provided
    avatar = None
    if avatar_image_path and Path(avatar_image_path).exists():
        try:
            avatar = Image.open(avatar_image_path).convert("RGB")
        except Exception as exc:
            log.warning("flyer_builder.avatar_load_failed", error=str(exc))

    builder = TEMPLATE_MAP.get(flyer_format, _build_social_square)

    img = builder(
        avatar=avatar,
        headline=headline,
        subheadline=subheadline,
        cta=cta_text,
        banker_name=banker_name,
        banker_nmls=banker_nmls,
    )

    # Save
    out_dir = Path(settings.media_storage_path) / "flyers"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"flyer_{flyer_format}_{uuid.uuid4().hex[:10]}.jpg"
    out_path = out_dir / filename
    img.save(out_path, "JPEG", quality=92, optimize=True)

    served_url = f"{settings.backend_url}/media/flyers/{filename}"
    log.info("flyer_builder.saved", filename=filename, format=flyer_format)

    return {"path": str(out_path), "url": served_url}


# ── Async dispatcher (Bannerbear → Pillow fallback) ───────────────────────────

async def build_flyer_async(
    avatar_image_path: Optional[str],
    avatar_image_url: Optional[str],
    headline: str,
    subheadline: str = "",
    cta_text: str = "",
    flyer_format: str = "social_square",
    banker_name: Optional[str] = None,
    banker_nmls: Optional[str] = None,
) -> dict:
    """
    Async flyer builder.

    Routes to Bannerbear when FLYER_COMPOSER=bannerbear and a template ID is set
    for the requested format. Falls back to Pillow silently on any error so a
    flyer is always produced.

    Returns {"path": str, "url": str}.
    """
    import asyncio as _asyncio
    banker_name = banker_name or settings.banker_name
    banker_nmls = banker_nmls or settings.banker_nmls

    if settings.flyer_composer.lower() == "bannerbear" and avatar_image_url:
        try:
            from app.services.bannerbear_composer import compose_flyer_bannerbear
            return await compose_flyer_bannerbear(
                avatar_url=avatar_image_url,
                headline=headline,
                subheadline=subheadline,
                cta_text=cta_text,
                flyer_format=flyer_format,
                banker_name=banker_name,
                banker_nmls=banker_nmls,
            )
        except Exception as exc:
            log.warning(
                "build_flyer_async.bannerbear_failed — falling back to Pillow",
                error=str(exc),
                format=flyer_format,
            )

    # Pillow is synchronous — run in thread so we don't block the event loop
    loop = _asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: build_flyer(
            avatar_image_path=avatar_image_path,
            headline=headline,
            subheadline=subheadline,
            cta_text=cta_text,
            flyer_format=flyer_format,
            banker_name=banker_name,
            banker_nmls=banker_nmls,
        ),
    )

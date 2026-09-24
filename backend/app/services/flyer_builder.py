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

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

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

# ── Theme palettes ────────────────────────────────────────────────────────────
# Each theme: gradient background (top → bottom), accent color, secondary accent,
# text colors, and footer band. Complementary pairs chosen for contrast + warmth.

THEMES = {
    "midnight_gold": {           # default — dark charcoal + warm gold (brand)
        "bg_top":    (24, 24, 28),
        "bg_bottom": (44, 38, 30),
        "accent":    (245, 200, 122),
        "accent2":   (200, 134, 10),
        "headline":  (255, 255, 255),
        "sub":       (196, 190, 180),
        "footer_bg": (18, 18, 20),
        "footer_fg": (150, 144, 134),
        "btn_fg":    (31, 31, 31),
    },
    "ocean": {                   # deep navy + aqua — trustworthy, crisp
        "bg_top":    (12, 27, 51),
        "bg_bottom": (24, 56, 92),
        "accent":    (94, 212, 201),
        "accent2":   (46, 134, 171),
        "headline":  (255, 255, 255),
        "sub":       (168, 194, 216),
        "footer_bg": (8, 19, 36),
        "footer_fg": (128, 156, 180),
        "btn_fg":    (10, 24, 44),
    },
    "forest": {                  # deep green + cream — grounded, premium
        "bg_top":    (18, 38, 32),
        "bg_bottom": (36, 66, 52),
        "accent":    (222, 205, 164),
        "accent2":   (150, 178, 128),
        "headline":  (255, 253, 246),
        "sub":       (182, 200, 184),
        "footer_bg": (12, 26, 22),
        "footer_fg": (140, 160, 146),
        "btn_fg":    (20, 40, 33),
    },
    "plum": {                    # rich plum + blush — bold, modern
        "bg_top":    (43, 21, 51),
        "bg_bottom": (84, 41, 75),
        "accent":    (247, 178, 173),
        "accent2":   (196, 116, 150),
        "headline":  (255, 250, 250),
        "sub":       (212, 186, 202),
        "footer_bg": (30, 14, 36),
        "footer_fg": (168, 140, 160),
        "btn_fg":    (43, 21, 51),
    },
    "slate_ember": {             # cool slate + ember orange — energetic
        "bg_top":    (28, 32, 38),
        "bg_bottom": (52, 58, 66),
        "accent":    (255, 145, 77),
        "accent2":   (214, 90, 49),
        "headline":  (255, 255, 255),
        "sub":       (184, 192, 200),
        "footer_bg": (20, 23, 28),
        "footer_fg": (140, 150, 160),
        "btn_fg":    (28, 24, 20),
    },
}

DEFAULT_THEME = "midnight_gold"


def _theme(name: Optional[str]) -> dict:
    return THEMES.get((name or DEFAULT_THEME).lower().strip(), THEMES[DEFAULT_THEME])


def _vertical_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    """Smooth vertical gradient background."""
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
    return base.resize((w, h))


def _decorate(img: Image.Image, theme: dict, W: int, H: int, seed: int = 0) -> None:
    """
    Draw subtle translucent rings and dots so backgrounds never look flat.
    Painted onto an RGBA overlay then composited (keeps shapes soft).
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    a1, a2 = theme["accent"], theme["accent2"]

    # Large ring off the bottom-left corner
    r = int(min(W, H) * 0.42)
    cx, cy = int(-r * 0.35), H - int(r * 0.4)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*a1, 26), width=max(int(r * 0.10), 18))

    # Medium ring near the top-right
    r2 = int(min(W, H) * 0.22)
    cx2, cy2 = W - int(r2 * 0.5), int(r2 * 0.35)
    d.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2], outline=(*a2, 22), width=max(int(r2 * 0.14), 12))

    # Small solid dot accent
    r3 = int(min(W, H) * 0.045)
    d.ellipse([int(W * 0.06), int(H * 0.72), int(W * 0.06) + r3, int(H * 0.72) + r3], fill=(*a1, 30))

    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))


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


def _draw_pill_button(draw, x: int, y: int, text: str, font, bg=GOLD, fg=DARK,
                      padding_x=32, padding_h=18, shadow=None):
    """Draw a rounded-rect pill button with an arrow and soft shadow. Returns (x2, y2)."""
    label = text.replace("→", "›") if "→" in text else f"{text}  ›"
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x2 = x + tw + padding_x * 2
    y2 = y + th + padding_h * 2
    if shadow:
        draw.rounded_rectangle([x + 4, y + 6, x2 + 4, y2 + 6], radius=14, fill=shadow)
    draw.rounded_rectangle([x, y, x2, y2], radius=14, fill=bg)
    draw.text((x + padding_x, y + padding_h), label, font=font, fill=fg)
    return x2, y2


def _draw_headline(draw, text: str, x: int, y: int, max_width: int,
                   font: ImageFont.FreeTypeFont, color: tuple, accent: tuple,
                   line_spacing: int = 10) -> int:
    """
    Draw a wrapped headline with the LAST word rendered in the accent color —
    gives every flyer a designed, intentional look. Returns final y.
    """
    words = text.split()
    if not words:
        return y
    lines, current = [], ""
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

    last_word = words[-1]
    for i, line in enumerate(lines):
        is_last_line = i == len(lines) - 1
        if is_last_line and line.endswith(last_word) and len(words) > 1:
            head = line[: len(line) - len(last_word)].rstrip()
            if head:
                draw.text((x, y), head, font=font, fill=color)
                hw = draw.textbbox((0, 0), head + " ", font=font)[2]
            else:
                hw = 0
            draw.text((x + hw, y), last_word, font=font, fill=accent)
        else:
            draw.text((x, y), line, font=font, fill=color)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


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
    # Crop-to-fill: preserves aspect ratio instead of stretching/distorting.
    # Without this, a 1024×1024 avatar jammed into a 627×1080 box looks elongated.
    avatar_resized = ImageOps.fit(avatar, (w, h), method=Image.LANCZOS)

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
                          banker_name: str, banker_nmls: str,
                          theme: Optional[dict] = None, brand: str = "") -> Image.Image:
    """1080 × 1080 — Instagram / Facebook post."""
    t = theme or _theme(None)
    W, H = 1080, 1080
    img = _vertical_gradient(W, H, t["bg_top"], t["bg_bottom"])
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)

    # Avatar — right 58%, full height
    if avatar:
        avatar_x = int(W * 0.42)
        _paste_avatar(img, avatar, (avatar_x, 0, W - avatar_x, H), blend_left=True)
        draw = ImageDraw.Draw(img)

    # Accent left bar with secondary underlay
    draw.rectangle([0, 0, 10, H], fill=t["accent"])
    draw.rectangle([10, 0, 14, H], fill=(*t["accent2"],))

    # Brand label + keyline
    text_x = 56
    draw.text((text_x, 56), brand, font=_font(22, bold=True), fill=t["accent"])
    draw.line([(text_x, 96), (text_x + 170, 96)], fill=t["accent2"], width=3)

    # Headline (last word in accent)
    y = 136
    y = _draw_headline(draw, headline, text_x, y, int(W * 0.42) - 60,
                       _font(66, bold=True), t["headline"], t["accent"], line_spacing=10)

    # Subheadline
    if subheadline:
        y += 26
        y = _draw_text_wrapped(draw, subheadline, text_x, y, int(W * 0.42) - 60,
                                _font(30), t["sub"], line_spacing=8)

    # CTA button with shadow
    if cta:
        y += 42
        _draw_pill_button(draw, text_x, y, cta, _font(27, bold=True),
                          bg=t["accent"], fg=t["btn_fg"], shadow=(12, 12, 14))

    # Bottom NMLS bar
    bar_h = 70
    draw.rectangle([0, H - bar_h, W, H], fill=t["footer_bg"])
    draw.line([(0, H - bar_h), (W, H - bar_h)], fill=t["accent2"], width=2)
    nmls_text = f"NMLS #{banker_nmls}  ·  {banker_name}  ·  Equal Housing Opportunity"
    draw.text((text_x, H - bar_h + 24), nmls_text, font=_font(18), fill=t["footer_fg"])

    return img


def _build_facebook_banner(avatar: Optional[Image.Image], headline: str,
                            subheadline: str, cta: str,
                            banker_name: str, banker_nmls: str,
                            theme: Optional[dict] = None, brand: str = "") -> Image.Image:
    """1200 × 628 — Facebook/LinkedIn ad banner."""
    t = theme or _theme(None)
    W, H = 1200, 628
    img = _vertical_gradient(W, H, t["bg_top"], t["bg_bottom"])
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)

    # Avatar — right 50%
    if avatar:
        av_x = W // 2
        _paste_avatar(img, avatar, (av_x, 0, W - av_x, H), blend_left=True)
        draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 8, H], fill=t["accent"])

    text_x = 52
    draw.text((text_x, 44), brand, font=_font(18, bold=True), fill=t["accent"])
    draw.line([(text_x, 76), (text_x + 130, 76)], fill=t["accent2"], width=2)

    y = 104
    y = _draw_headline(draw, headline, text_x, y, W // 2 - 80,
                       _font(54, bold=True), t["headline"], t["accent"], line_spacing=8)

    if subheadline:
        y += 18
        y = _draw_text_wrapped(draw, subheadline, text_x, y, W // 2 - 80,
                                _font(26), t["sub"], line_spacing=6)

    if cta:
        y += 32
        _draw_pill_button(draw, text_x, y, cta, _font(23, bold=True),
                          bg=t["accent"], fg=t["btn_fg"], shadow=(12, 12, 14))

    # Footer
    footer_text = f"NMLS #{banker_nmls}  ·  Equal Housing Opportunity  ·  {banker_name}"
    draw.text((text_x, H - 38), footer_text, font=_font(15), fill=t["footer_fg"])

    return img


def _build_story(avatar: Optional[Image.Image], headline: str,
                  subheadline: str, cta: str,
                  banker_name: str, banker_nmls: str,
                  theme: Optional[dict] = None, brand: str = "") -> Image.Image:
    """1080 × 1920 — Instagram / Facebook Story."""
    t = theme or _theme(None)
    W, H = 1080, 1920
    img = _vertical_gradient(W, H, t["bg_top"], t["bg_bottom"])
    draw = ImageDraw.Draw(img)

    # Avatar — top 55%, full width, no blend
    av_h = int(H * 0.55)
    if avatar:
        _paste_avatar(img, avatar, (0, 0, W, av_h), blend_left=False)

        # Gradient from avatar bottom into text section (RGBA overlay for true alpha)
        grad_h = 260
        grad = Image.new("RGBA", (W, grad_h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y_offset in range(grad_h):
            alpha = int(255 * (y_offset / grad_h))
            gd.line([(0, y_offset), (W, y_offset)], fill=(*t["bg_top"], alpha))
        img.paste(Image.alpha_composite(
            img.crop((0, av_h - grad_h, W, av_h)).convert("RGBA"), grad).convert("RGB"),
            (0, av_h - grad_h))
        draw = ImageDraw.Draw(img)

    # Decorations only in the text section (keep the face clean)
    lower = img.crop((0, av_h, W, H))
    _decorate(lower, t, W, H - av_h)
    img.paste(lower, (0, av_h))
    draw = ImageDraw.Draw(img)

    # Accent divider — two-tone
    div_y = int(H * 0.56)
    draw.rectangle([0, div_y, W, div_y + 8], fill=t["accent"])
    draw.rectangle([0, div_y + 8, W, div_y + 12], fill=t["accent2"])

    text_x = 72
    text_max_w = W - text_x * 2

    # Measure the text block so it centers between divider and footer
    y = div_y + 72
    draw.text((text_x, y - 44), brand, font=_font(26, bold=True), fill=t["accent"])

    y += 20
    y = _draw_headline(draw, headline, text_x, y, text_max_w,
                       _font(80, bold=True), t["headline"], t["accent"], line_spacing=14)

    if subheadline:
        y += 30
        y = _draw_text_wrapped(draw, subheadline, text_x, y, text_max_w,
                                _font(38), t["sub"], line_spacing=10)

    if cta:
        y += 56
        # Full-width button on story with shadow + arrow
        btn_w = W - text_x * 2
        label = cta.replace("→", "›") if "→" in cta else f"{cta}  ›"
        draw.rounded_rectangle([text_x + 4, y + 6, text_x + btn_w + 4, y + 94], radius=18, fill=(0, 0, 0))
        draw.rounded_rectangle([text_x, y, text_x + btn_w, y + 88], radius=18, fill=t["accent"])
        bbox = draw.textbbox((0, 0), label, font=_font(36, bold=True))
        tx = text_x + (btn_w - (bbox[2] - bbox[0])) // 2
        draw.text((tx, y + 22), label, font=_font(36, bold=True), fill=t["btn_fg"])

    # Bottom compliance bar
    draw.rectangle([0, H - 90, W, H], fill=t["footer_bg"])
    draw.line([(0, H - 90), (W, H - 90)], fill=t["accent2"], width=2)
    footer = f"NMLS #{banker_nmls}  ·  {banker_name}  ·  Equal Housing Opportunity"
    bbox = draw.textbbox((0, 0), footer, font=_font(22))
    fx = (W - (bbox[2] - bbox[0])) // 2
    draw.text((fx, H - 58), footer, font=_font(22), fill=t["footer_fg"])

    return img


def _build_wide_banner(avatar: Optional[Image.Image], headline: str,
                        subheadline: str, cta: str,
                        banker_name: str, banker_nmls: str,
                        theme: Optional[dict] = None, brand: str = "") -> Image.Image:
    """1500 × 500 — email header / Twitter banner / website hero."""
    t = theme or _theme(None)
    W, H = 1500, 500
    img = _vertical_gradient(W, H, t["bg_top"], t["bg_bottom"])
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)

    # Avatar — right 40%
    if avatar:
        av_x = int(W * 0.60)
        _paste_avatar(img, avatar, (av_x, 0, W - av_x, H), blend_left=True)
        draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 8, H], fill=t["accent"])

    text_x = 64
    draw.text((text_x, 40), brand, font=_font(20, bold=True), fill=t["accent"])
    draw.line([(text_x, 72), (text_x + 140, 72)], fill=t["accent2"], width=2)

    y = 104
    y = _draw_headline(draw, headline, text_x, y, int(W * 0.55) - 80,
                       _font(62, bold=True), t["headline"], t["accent"], line_spacing=8)

    if subheadline:
        y += 16
        y = _draw_text_wrapped(draw, subheadline, text_x, y, int(W * 0.55) - 80,
                                _font(28), t["sub"], line_spacing=6)

    if cta:
        y += 30
        _draw_pill_button(draw, text_x, y, cta, _font(24, bold=True),
                          bg=t["accent"], fg=t["btn_fg"], shadow=(12, 12, 14))

    draw.text((text_x, H - 36), f"NMLS #{banker_nmls}  ·  Equal Housing Opportunity",
              font=_font(16), fill=t["footer_fg"])

    return img


def _apply_logo(img: Image.Image, logo: Image.Image, label: str,
                t: dict, flyer_format: str) -> None:
    """
    Composite a partner/brand logo into the flyer's footer strip — right-aligned,
    vertically centered, aspect-preserved. Optional label ("Powered by") renders
    to the left of the mark in the footer text color.

    Placement is deliberate: the footer is the standard spot for partner marks
    ("Powered by X") and never collides with headline, avatar, or CTA.
    """
    W, H = img.size
    bar_h = {"social_square": 70, "story": 90}.get(flyer_format, 56)
    margin = 40

    # Scale: fit inside the footer strip, never wider than 22% of the canvas
    max_h = bar_h - 22
    max_w = int(W * 0.22)
    logo = logo.convert("RGBA")
    ratio = min(max_h / logo.height, max_w / logo.width)
    lw, lh = max(int(logo.width * ratio), 1), max(int(logo.height * ratio), 1)
    logo_resized = logo.resize((lw, lh), Image.LANCZOS)

    lx = W - margin - lw
    ly = H - bar_h // 2 - lh // 2

    draw = ImageDraw.Draw(img)
    if label:
        f = _font(16, bold=True)
        bbox = draw.textbbox((0, 0), label.upper(), font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((lx - tw - 14, H - bar_h // 2 - th // 2 - 2),
                  label.upper(), font=f, fill=t["footer_fg"])

    img.paste(logo_resized, (lx, ly), logo_resized)


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
    theme: Optional[str] = None,
    brand_name: Optional[str] = None,
    logo_path: Optional[str] = None,
    logo_label: Optional[str] = None,
) -> dict:
    """
    Composite a branded flyer.

    theme: midnight_gold (default) | ocean | forest | plum | slate_ember
    brand_name: label drawn on the flyer — request param > FLYER_BRAND_NAME env > app_name
    logo_path: optional partner/brand logo composited into the footer strip
    logo_label: optional text before the logo, e.g. "Powered by"

    Returns {"path": str, "url": str} on success.
    Raises on failure.
    """
    banker_name = banker_name or settings.banker_name
    banker_nmls = banker_nmls or settings.banker_nmls
    brand = (brand_name or settings.flyer_brand_name or settings.app_name).upper()

    # Load avatar image if provided — keep RGBA so bg-removed cutouts stay clean
    avatar = None
    if avatar_image_path and Path(avatar_image_path).exists():
        try:
            avatar = Image.open(avatar_image_path)
            if avatar.mode not in ("RGB", "RGBA"):
                avatar = avatar.convert("RGB")
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
        theme=_theme(theme),
        brand=brand,
    )

    # Optional partner/brand logo in the footer strip
    if logo_path and Path(logo_path).exists():
        try:
            _apply_logo(img, Image.open(logo_path), logo_label or "",
                        _theme(theme), flyer_format)
        except Exception as exc:
            log.warning("flyer_builder.logo_apply_failed", error=str(exc))

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
    theme: Optional[str] = None,
    brand_name: Optional[str] = None,
    logo_path: Optional[str] = None,
    logo_label: Optional[str] = None,
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
            theme=theme,
            brand_name=brand_name,
            logo_path=logo_path,
            logo_label=logo_label,
        ),
    )

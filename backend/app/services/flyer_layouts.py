"""
Flyer Layouts — data-rich marketing layouts beyond the avatar-promo templates.

Design doctrine: REAL photos lead (property, lifestyle, uploads); the banker's
avatar demotes to a small circular contact chip. Nothing should look AI-made.

Layouts (all 1080×1350 portrait — IG/FB feed optimal — unless noted):
  listing      — co-marketing listing flyer: property hero, price, beds/baths,
                 2-scenario payment table (Conv/FHA), dual contact blocks
  open_house   — event flyer: property hero, date/time banner, address, co-brand
  program      — benefits flyer: hero, headline, highlight banner, ✓ checklist
  comparison   — VS layout: two option columns with rows, unifying banner
  lifestyle    — full-bleed photo, gradient overlay, stacked bold type
  rate_update  — today's rates grid from the rate snapshot, market note
  testimonial  — big quote card with client name + context
  just_funded  — milestone banner over property photo, stat line, co-brand
  steps        — numbered educational steps ("5 Steps to Buying")

Every layout: theme palettes, brand label, optional partner logo, NMLS +
Equal Housing footer. Rate-bearing layouts carry the "illustrative" disclaimer.
"""

import uuid
from pathlib import Path
from typing import Optional

import httpx
import structlog
from PIL import Image, ImageDraw, ImageOps

from app.config import settings
from app.services.flyer_builder import (
    _font, _theme, _vertical_gradient, _decorate,
    _draw_text_wrapped, _draw_headline, _apply_logo,
)

log = structlog.get_logger()

W, H = 1080, 1350
MARGIN = 56


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _fetch_image(src: Optional[str]) -> Optional[Image.Image]:
    """
    Load an image from a local path or http(s) URL.
    URLs pointing at our own /media/ tree resolve straight to disk (BACKEND_URL
    may be a LAN IP that isn't reachable from the server itself).
    Returns None on failure.
    """
    if not src:
        return None
    try:
        if src.startswith("http") and "/media/" in src:
            local = Path(settings.media_storage_path) / src.split("/media/", 1)[1]
            if local.exists():
                return Image.open(local)
        if src.startswith("http"):
            res = httpx.get(src, timeout=20, follow_redirects=True)
            res.raise_for_status()
            import io
            return Image.open(io.BytesIO(res.content))
        p = Path(src)
        if p.exists():
            return Image.open(p)
    except Exception as exc:
        log.warning("flyer_layouts.image_load_failed", src=src[:100], error=str(exc))
    return None


def _circle_chip(img: Image.Image, size: int) -> Image.Image:
    """Crop an image into a circular chip with transparency."""
    fitted = ImageOps.fit(img.convert("RGB"), (size, size), method=Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(fitted, (0, 0), mask)
    return out


def _hero(img: Image.Image, photo: Optional[Image.Image], hero_h: int, t: dict) -> None:
    """Paste a hero photo across the top with a gradient fade into the body."""
    if photo is None:
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, hero_h], fill=t["bg_top"])
        top = img.crop((0, 0, W, hero_h))
        _decorate(top, t, W, hero_h)
        img.paste(top, (0, 0))
        return
    img.paste(ImageOps.fit(photo.convert("RGB"), (W, hero_h), method=Image.LANCZOS), (0, 0))
    grad_h = 140
    grad = Image.new("RGBA", (W, grad_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(grad_h):
        gd.line([(0, y), (W, y)], fill=(*t["bg_top"], int(255 * (y / grad_h))))
    img.paste(Image.alpha_composite(
        img.crop((0, hero_h - grad_h, W, hero_h)).convert("RGBA"), grad).convert("RGB"),
        (0, hero_h - grad_h))


def _footer(img: Image.Image, t: dict, disclaimer: str = "") -> int:
    """Compliance footer bar. Returns the y where the bar starts."""
    draw = ImageDraw.Draw(img)
    lines = [f"NMLS #{settings.banker_nmls}  ·  {settings.banker_name}  ·  Equal Housing Opportunity"]
    if disclaimer:
        lines.append(disclaimer)
    bar_h = 56 + (30 if disclaimer else 0)
    y0 = H - bar_h
    draw.rectangle([0, y0, W, H], fill=t["footer_bg"])
    draw.line([(0, y0), (W, y0)], fill=t["accent2"], width=2)
    ty = y0 + 16
    for i, line in enumerate(lines):
        f = _font(17 if i == 0 else 14)
        bbox = draw.textbbox((0, 0), line, font=f)
        draw.text(((W - (bbox[2] - bbox[0])) // 2, ty), line, font=f, fill=t["footer_fg"])
        ty += (bbox[3] - bbox[1]) + 10
    return y0


def _brand_header(draw: ImageDraw.ImageDraw, t: dict, brand: str, y: int = 40,
                  on_photo: bool = False) -> None:
    color = (255, 255, 255) if on_photo else t["accent"]
    draw.text((MARGIN, y), brand, font=_font(22, bold=True), fill=color)
    draw.line([(MARGIN, y + 36), (MARGIN + 150, y + 36)], fill=t["accent2"], width=3)


def _contact_strip(img: Image.Image, t: dict, y: int, strip_h: int,
                   avatar: Optional[Image.Image], partner: Optional[dict]) -> None:
    """
    Dual contact strip: banker chip + details left, partner (realtor) right.
    partner: {name, company, phone, title?}
    """
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, y, W, y + strip_h], fill=t["footer_bg"])
    draw.line([(0, y), (W, y)], fill=t["accent"], width=3)

    chip = 84
    cy = y + (strip_h - chip) // 2
    tx = MARGIN
    if avatar is not None:
        img.paste(_circle_chip(avatar, chip), (MARGIN, cy), _circle_chip(avatar, chip))
        tx = MARGIN + chip + 20

    draw.text((tx, cy + 2), settings.banker_name or "Your Loan Officer",
              font=_font(26, bold=True), fill=t["headline"])
    draw.text((tx, cy + 38), f"Mortgage Banker · NMLS #{settings.banker_nmls}",
              font=_font(18), fill=t["sub"])
    contact_line = "  ·  ".join(x for x in [settings.banker_phone, settings.campaign_from_email] if x)
    if contact_line:
        draw.text((tx, cy + 64), contact_line, font=_font(18), fill=t["accent"])

    if partner and partner.get("name"):
        px = W - MARGIN
        lines = [
            (partner["name"], _font(26, bold=True), t["headline"]),
            (partner.get("title") or "Realtor" + (f" · {partner['company']}" if partner.get("company") else ""),
             _font(18), t["sub"]),
        ]
        if partner.get("phone"):
            lines.append((partner["phone"], _font(18), t["accent"]))
        ly = cy + 2
        for text, f, color in lines:
            bbox = draw.textbbox((0, 0), text, font=f)
            draw.text((px - (bbox[2] - bbox[0]), ly), text, font=f, fill=color)
            ly += (bbox[3] - bbox[1]) + 12


def _base(t: dict) -> Image.Image:
    return _vertical_gradient(W, H, t["bg_top"], t["bg_bottom"])


def _money(v) -> str:
    try:
        return f"${round(float(v)):,}"
    except Exception:
        return str(v)


# ── 1. LISTING — co-marketing flyer with payment table ────────────────────────

def _build_listing(payload: dict, t: dict, brand: str,
                   avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    hero_h = int(H * 0.36)
    _hero(img, hero, hero_h, t)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand, y=36, on_photo=hero is not None)

    # Address + specs
    y = hero_h + 18
    draw.text((MARGIN, y), payload.get("address", ""), font=_font(40, bold=True), fill=t["headline"])
    y += 54
    specs = "  |  ".join(x for x in [
        payload.get("city_state", ""),
        f"{payload['beds']} Bed" if payload.get("beds") else "",
        f"{payload['baths']} Bath" if payload.get("baths") else "",
        f"{payload['sqft']:,} SQFT" if payload.get("sqft") else "",
    ] if x)
    draw.text((MARGIN, y), specs, font=_font(24), fill=t["sub"])

    # Price banner
    y += 46
    price = _money(payload.get("price", 0))
    pf = _font(52, bold=True)
    bbox = draw.textbbox((0, 0), price, font=pf)
    draw.rounded_rectangle([MARGIN, y, MARGIN + bbox[2] + 48, y + 78], radius=12, fill=t["accent"])
    draw.text((MARGIN + 24, y + 12), price, font=pf, fill=t["btn_fg"])
    lbl = "ESTIMATED MONTHLY PAYMENTS"
    lf = _font(20, bold=True)
    lb = draw.textbbox((0, 0), lbl, font=lf)
    draw.text((W - MARGIN - (lb[2] - lb[0]), y + 44), lbl, font=lf, fill=t["accent"])

    # Payment table — 2 scenario columns
    y += 104
    scenarios = payload.get("scenarios", [])[:2]
    rows = [
        ("Loan Program", [s.get("loan_type", "") for s in scenarios]),
        ("Interest Rate*", [f"{s.get('rate', 0):.3f}%" for s in scenarios]),
        ("Down Payment", [f"{_money(s.get('down_payment', 0))} ({s.get('down_pct', 0):g}%)" for s in scenarios]),
        ("Principal & Interest", [_money(s.get("monthly_breakdown", {}).get("principal_interest", 0)) for s in scenarios]),
        ("Taxes + Insurance", [_money(s.get("monthly_breakdown", {}).get("taxes", 0)
                                       + s.get("monthly_breakdown", {}).get("insurance", 0)
                                       + s.get("monthly_breakdown", {}).get("hoa", 0)) for s in scenarios]),
        ("MI / PMI", [_money(s.get("monthly_breakdown", {}).get("mip_pmi", 0)) for s in scenarios]),
        ("TOTAL MONTHLY", [_money(s.get("monthly_breakdown", {}).get("total", 0)) for s in scenarios]),
        ("Est. Cash to Close", [_money(s.get("cash_to_close", 0)) for s in scenarios]),
    ]
    label_w = 380
    col_w = (W - MARGIN * 2 - label_w) // max(len(scenarios), 1)
    row_h = 46
    table_y = y
    for i, (label, values) in enumerate(rows):
        ry = table_y + i * row_h
        is_total = label == "TOTAL MONTHLY"
        is_head = i == 0
        if is_head:
            draw.rounded_rectangle([MARGIN, ry, W - MARGIN, ry + row_h - 6], radius=8, fill=t["accent2"])
        elif is_total:
            draw.rounded_rectangle([MARGIN, ry, W - MARGIN, ry + row_h - 6], radius=8, fill=t["accent"])
        elif i % 2 == 0:
            draw.rectangle([MARGIN, ry, W - MARGIN, ry + row_h - 6], fill=(*t["footer_bg"],))
        lf2 = _font(21, bold=is_total or is_head)
        lcolor = t["btn_fg"] if is_total else ((255, 255, 255) if is_head else t["sub"])
        draw.text((MARGIN + 16, ry + 10), label, font=lf2, fill=lcolor)
        for c, v in enumerate(values):
            vf = _font(21, bold=is_total or is_head)
            vcolor = t["btn_fg"] if is_total else ((255, 255, 255) if is_head else t["headline"])
            vb = draw.textbbox((0, 0), v, font=vf)
            cx = MARGIN + label_w + c * col_w + (col_w - (vb[2] - vb[0])) // 2
            draw.text((cx, ry + 10), v, font=vf, fill=vcolor)

    # Contact strip + footer
    strip_h = 130
    disclaimer = payload.get("disclaimer_line",
        "*Illustrative rates as of " + payload.get("as_of", "today") + ". Not a rate lock or commitment to lend.")
    _contact_strip(img, t, H - 86 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t, disclaimer)
    return img


# ── 2. OPEN HOUSE ──────────────────────────────────────────────────────────────

def _build_open_house(payload: dict, t: dict, brand: str,
                      avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    hero_h = int(H * 0.46)
    _hero(img, hero, hero_h, t)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand, y=36, on_photo=hero is not None)

    # OPEN HOUSE banner overlapping hero bottom
    banner_y = hero_h - 44
    bf = _font(56, bold=True)
    text = payload.get("banner", "OPEN HOUSE")
    bbox = draw.textbbox((0, 0), text, font=bf)
    bw = bbox[2] - bbox[0] + 80
    draw.rounded_rectangle([MARGIN, banner_y, MARGIN + bw, banner_y + 88], radius=14, fill=t["accent"])
    draw.text((MARGIN + 40, banner_y + 12), text, font=bf, fill=t["btn_fg"])

    y = banner_y + 120
    draw.text((MARGIN, y), payload.get("address", ""), font=_font(42, bold=True), fill=t["headline"])
    y += 56
    if payload.get("city_state"):
        draw.text((MARGIN, y), payload["city_state"], font=_font(26), fill=t["sub"])
        y += 44

    # Date / time chips
    y += 12
    for chip_text in [payload.get("date_line", ""), payload.get("time_line", "")]:
        if not chip_text:
            continue
        f = _font(30, bold=True)
        cb = draw.textbbox((0, 0), chip_text, font=f)
        draw.rounded_rectangle([MARGIN, y, MARGIN + cb[2] + 56, y + 64], radius=12,
                               outline=t["accent"], width=3)
        draw.text((MARGIN + 28, y + 14), chip_text, font=f, fill=t["accent"])
        y += 82

    if payload.get("price"):
        y += 8
        draw.text((MARGIN, y), f"Offered at {_money(payload['price'])}",
                  font=_font(34, bold=True), fill=t["headline"])
        y += 50
    if payload.get("note"):
        y += 4
        _draw_text_wrapped(draw, payload["note"], MARGIN, y, W - MARGIN * 2, _font(24), t["sub"])

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── 3. PROGRAM — benefits checklist ───────────────────────────────────────────

def _build_program(payload: dict, t: dict, brand: str,
                   avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    hero_h = int(H * 0.30) if hero else int(H * 0.16)
    _hero(img, hero, hero_h, t)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand, y=36, on_photo=hero is not None)

    y = hero_h + 20
    y = _draw_headline(draw, payload.get("headline", ""), MARGIN, y, W - MARGIN * 2,
                       _font(58, bold=True), t["headline"], t["accent"], line_spacing=10)
    if payload.get("subheadline"):
        y += 14
        y = _draw_text_wrapped(draw, payload["subheadline"], MARGIN, y, W - MARGIN * 2,
                               _font(26), t["sub"])

    # Highlight banner
    if payload.get("highlight"):
        y += 28
        hf = _font(30, bold=True)
        hb = draw.textbbox((0, 0), payload["highlight"], font=hf)
        draw.rounded_rectangle([MARGIN, y, W - MARGIN, y + 72], radius=12, fill=t["accent"])
        draw.text((MARGIN + (W - MARGIN * 2 - (hb[2] - hb[0])) // 2, y + 18),
                  payload["highlight"], font=hf, fill=t["btn_fg"])
        y += 100
    else:
        y += 24

    # Benefits — two columns of ✓ items
    benefits = payload.get("benefits", [])[:8]
    col_w = (W - MARGIN * 2 - 40) // 2
    bx = [MARGIN, MARGIN + col_w + 40]
    by = [y, y]
    for i, item in enumerate(benefits):
        c = i % 2
        cx, cy = bx[c], by[c]
        draw.ellipse([cx, cy + 4, cx + 30, cy + 34], fill=t["accent"])
        # Hand-drawn check (Helvetica has no ✓ glyph)
        draw.line([(cx + 8, cy + 19), (cx + 13, cy + 25)], fill=t["btn_fg"], width=3)
        draw.line([(cx + 13, cy + 25), (cx + 23, cy + 12)], fill=t["btn_fg"], width=3)
        end_y = _draw_text_wrapped(draw, item, cx + 44, cy + 2, col_w - 44, _font(23), t["headline"], line_spacing=6)
        by[c] = max(end_y + 22, cy + 56)

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── 4. COMPARISON — VS layout ─────────────────────────────────────────────────

def _build_comparison(payload: dict, t: dict, brand: str,
                      avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand)

    y = 96
    y = _draw_headline(draw, payload.get("headline", ""), MARGIN, y, W - MARGIN * 2,
                       _font(54, bold=True), t["headline"], t["accent"], line_spacing=8)
    y += 30

    # Column headers with VS medallion
    col_w = (W - MARGIN * 2 - 60) // 2
    lx, rx = MARGIN, MARGIN + col_w + 60
    hf = _font(28, bold=True)
    for cx, title in ((lx, payload.get("left_title", "Option A")), (rx, payload.get("right_title", "Option B"))):
        draw.rounded_rectangle([cx, y, cx + col_w, y + 64], radius=12, fill=t["accent2"])
        tb = draw.textbbox((0, 0), title, font=hf)
        draw.text((cx + (col_w - (tb[2] - tb[0])) // 2, y + 14), title, font=hf, fill=(255, 255, 255))
    vs_cx = MARGIN + col_w + 30
    draw.ellipse([vs_cx - 34, y - 2, vs_cx + 34, y + 66], fill=t["accent"])
    vb = draw.textbbox((0, 0), "VS", font=_font(28, bold=True))
    draw.text((vs_cx - (vb[2] - vb[0]) // 2, y + 14), "VS", font=_font(28, bold=True), fill=t["btn_fg"])
    y += 92

    # Rows — paired cards
    rows = payload.get("rows", [])[:6]
    for row in rows:
        heights = []
        for cx, side in ((lx, "left"), (rx, "right")):
            item = row.get(side, {}) if isinstance(row.get(side), dict) else {"text": row.get(side, "")}
            title = item.get("title", "")
            text = item.get("text", "")
            card_y = y
            inner_y = card_y + 16
            if title:
                draw.text((cx + 20, inner_y), title, font=_font(23, bold=True), fill=t["accent"])
                inner_y += 34
            end_y = _draw_text_wrapped(draw, text, cx + 20, inner_y, col_w - 40, _font(20), t["sub"], line_spacing=5)
            heights.append(end_y - card_y + 16)
        card_h = max(heights + [64])
        for cx in (lx, rx):
            draw.rounded_rectangle([cx, y, cx + col_w, y + card_h], radius=12, outline=t["accent2"], width=2)
        # redraw text over outlines
        for cx, side in ((lx, "left"), (rx, "right")):
            item = row.get(side, {}) if isinstance(row.get(side), dict) else {"text": row.get(side, "")}
            inner_y = y + 16
            if item.get("title"):
                draw.text((cx + 20, inner_y), item["title"], font=_font(23, bold=True), fill=t["accent"])
                inner_y += 34
            _draw_text_wrapped(draw, item.get("text", ""), cx + 20, inner_y, col_w - 40, _font(20), t["sub"], line_spacing=5)
        y += card_h + 18

    # Unifying banner
    if payload.get("banner"):
        bf = _font(24, bold=True)
        bb = draw.textbbox((0, 0), payload["banner"], font=bf)
        by_ = min(y + 10, H - 56 - 130 - 70)
        draw.rounded_rectangle([MARGIN, by_, W - MARGIN, by_ + 60], radius=12, fill=t["accent"])
        draw.text((MARGIN + (W - MARGIN * 2 - (bb[2] - bb[0])) // 2, by_ + 14),
                  payload["banner"], font=bf, fill=t["btn_fg"])

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── 5. LIFESTYLE — full-bleed photo ───────────────────────────────────────────

def _build_lifestyle(payload: dict, t: dict, brand: str,
                     avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    if hero is not None:
        img = ImageOps.fit(hero.convert("RGB"), (W, H), method=Image.LANCZOS)
    else:
        img = _base(t)
        _decorate(img, t, W, H)
    # Dark gradient overlay bottom 55% for type
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    start = int(H * 0.40)
    for y in range(start, H):
        a = int(215 * ((y - start) / (H - start)))
        od.line([(0, y), (W, y)], fill=(*t["bg_top"], a))
    od.rectangle([0, 0, W, 130], fill=(*t["bg_top"], 110))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand, y=40, on_photo=False)

    lines = payload.get("headline_lines") or [payload.get("headline", "")]
    y = int(H * 0.52)
    for i, line in enumerate(lines[:3]):
        color = t["accent"] if i == len(lines[:3]) - 1 else (255, 255, 255)
        draw.text((MARGIN, y), line, font=_font(72, bold=True), fill=color)
        bbox = draw.textbbox((0, 0), line, font=_font(72, bold=True))
        y += (bbox[3] - bbox[1]) + 18
    if payload.get("subheadline"):
        y += 12
        y = _draw_text_wrapped(draw, payload["subheadline"].upper(), MARGIN, y,
                               W - MARGIN * 2, _font(28, bold=True), (255, 255, 255), line_spacing=8)
    if payload.get("cta_text"):
        y += 28
        label = payload["cta_text"] + "  ›"
        f = _font(26, bold=True)
        cb = draw.textbbox((0, 0), label, font=f)
        draw.rounded_rectangle([MARGIN, y, MARGIN + cb[2] + 64, y + 66], radius=14, fill=t["accent"])
        draw.text((MARGIN + 32, y + 16), label, font=f, fill=t["btn_fg"])

    _footer(img, t)
    return img


# ── 6. RATE UPDATE ─────────────────────────────────────────────────────────────

def _build_rate_update(payload: dict, t: dict, brand: str,
                       avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand)

    y = 100
    y = _draw_headline(draw, payload.get("headline", "This Week's Rates"), MARGIN, y,
                       W - MARGIN * 2, _font(58, bold=True), t["headline"], t["accent"])
    draw.text((MARGIN, y + 8), f"As of {payload.get('as_of', 'today')}", font=_font(24), fill=t["sub"])
    y += 64

    rates = payload.get("rates", [])[:6]
    card_h = 96
    for label, value in [(r.get("label", ""), r.get("value", "")) for r in rates]:
        draw.rounded_rectangle([MARGIN, y, W - MARGIN, y + card_h - 14], radius=14,
                               fill=(*t["footer_bg"],), outline=t["accent2"], width=2)
        draw.text((MARGIN + 28, y + 24), label, font=_font(28, bold=True), fill=t["headline"])
        vf = _font(40, bold=True)
        vb = draw.textbbox((0, 0), value, font=vf)
        draw.text((W - MARGIN - 28 - (vb[2] - vb[0]), y + 16), value, font=vf, fill=t["accent"])
        y += card_h

    if payload.get("note"):
        y += 12
        y = _draw_text_wrapped(draw, payload["note"], MARGIN, y, W - MARGIN * 2, _font(23), t["sub"])

    strip_h = 130
    disclaimer = "*Illustrative rates — not a rate lock, quote, or commitment to lend. Contact for a personalized quote."
    _contact_strip(img, t, H - 86 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t, disclaimer)
    return img


# ── 7. TESTIMONIAL ─────────────────────────────────────────────────────────────

def _build_testimonial(payload: dict, t: dict, brand: str,
                       avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand)

    # Giant quote mark
    draw.text((MARGIN - 8, 120), "“", font=_font(220, bold=True), fill=t["accent"])
    y = 320
    quote = payload.get("quote", "")
    y = _draw_text_wrapped(draw, quote, MARGIN, y, W - MARGIN * 2,
                           _font(42, bold=True), t["headline"], line_spacing=14)
    y += 36
    draw.line([(MARGIN, y), (MARGIN + 120, y)], fill=t["accent"], width=4)
    y += 28
    if payload.get("author"):
        draw.text((MARGIN, y), f"— {payload['author']}", font=_font(30, bold=True), fill=t["accent"])
        y += 46
    if payload.get("context"):
        _draw_text_wrapped(draw, payload["context"], MARGIN, y, W - MARGIN * 2, _font(24), t["sub"])

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── 8. JUST FUNDED / SOLD — milestone ─────────────────────────────────────────

def _build_just_funded(payload: dict, t: dict, brand: str,
                       avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    hero_h = int(H * 0.52)
    _hero(img, hero, hero_h, t)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand, y=36, on_photo=hero is not None)

    # Diagonal-feel milestone banner overlapping hero
    badge = payload.get("badge", "JUST FUNDED")
    bf = _font(64, bold=True)
    bb = draw.textbbox((0, 0), badge, font=bf)
    bw = bb[2] - bb[0] + 96
    bx = (W - bw) // 2
    by_ = hero_h - 52
    draw.rounded_rectangle([bx + 5, by_ + 7, bx + bw + 5, by_ + 105], radius=16, fill=(10, 10, 12))
    draw.rounded_rectangle([bx, by_, bx + bw, by_ + 98], radius=16, fill=t["accent"])
    draw.text((bx + 48, by_ + 14), badge, font=bf, fill=t["btn_fg"])

    y = by_ + 130
    if payload.get("address"):
        af = _font(36, bold=True)
        ab = draw.textbbox((0, 0), payload["address"], font=af)
        draw.text(((W - (ab[2] - ab[0])) // 2, y), payload["address"], font=af, fill=t["headline"])
        y += 52
    if payload.get("stat_line"):
        sf = _font(28)
        sb = draw.textbbox((0, 0), payload["stat_line"], font=sf)
        draw.text(((W - (sb[2] - sb[0])) // 2, y), payload["stat_line"], font=sf, fill=t["accent"])
        y += 48
    if payload.get("note"):
        y += 6
        _draw_text_wrapped(draw, payload["note"], MARGIN, y, W - MARGIN * 2, _font(23), t["sub"])

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── 9. STEPS — numbered educational ───────────────────────────────────────────

def _build_steps(payload: dict, t: dict, brand: str,
                 avatar: Optional[Image.Image], hero: Optional[Image.Image]) -> Image.Image:
    img = _base(t)
    _decorate(img, t, W, H)
    draw = ImageDraw.Draw(img)
    _brand_header(draw, t, brand)

    y = 96
    y = _draw_headline(draw, payload.get("headline", ""), MARGIN, y, W - MARGIN * 2,
                       _font(54, bold=True), t["headline"], t["accent"])
    if payload.get("subheadline"):
        y += 10
        y = _draw_text_wrapped(draw, payload["subheadline"], MARGIN, y, W - MARGIN * 2,
                               _font(25), t["sub"])
    y += 26

    steps = payload.get("steps", [])[:6]
    for i, step in enumerate(steps):
        title = step.get("title", "") if isinstance(step, dict) else str(step)
        desc = step.get("desc", "") if isinstance(step, dict) else ""
        num_d = 64
        draw.ellipse([MARGIN, y, MARGIN + num_d, y + num_d], fill=t["accent"])
        nf = _font(30, bold=True)
        nb = draw.textbbox((0, 0), str(i + 1), font=nf)
        draw.text((MARGIN + (num_d - (nb[2] - nb[0])) // 2, y + (num_d - (nb[3] - nb[1])) // 2 - 4),
                  str(i + 1), font=nf, fill=t["btn_fg"])
        tx = MARGIN + num_d + 26
        draw.text((tx, y + 2), title, font=_font(28, bold=True), fill=t["headline"])
        end_y = y + 40
        if desc:
            end_y = _draw_text_wrapped(draw, desc, tx, y + 40, W - MARGIN - tx, _font(21), t["sub"], line_spacing=5)
        if i < len(steps) - 1:
            draw.line([(MARGIN + num_d // 2, y + num_d + 6), (MARGIN + num_d // 2, max(end_y, y + num_d) + 18)],
                      fill=t["accent2"], width=3)
        y = max(end_y, y + num_d) + 26

    strip_h = 130
    _contact_strip(img, t, H - 56 - strip_h, strip_h, avatar, payload.get("realtor"))
    _footer(img, t)
    return img


# ── Registry + public entry ────────────────────────────────────────────────────

LAYOUT_MAP = {
    "listing":     _build_listing,
    "open_house":  _build_open_house,
    "program":     _build_program,
    "comparison":  _build_comparison,
    "lifestyle":   _build_lifestyle,
    "rate_update": _build_rate_update,
    "testimonial": _build_testimonial,
    "just_funded": _build_just_funded,
    "steps":       _build_steps,
}


def build_layout_flyer(
    layout: str,
    payload: dict,
    theme: Optional[str] = None,
    brand_name: Optional[str] = None,
    avatar_path: Optional[str] = None,
    hero_path: Optional[str] = None,
    logo_path: Optional[str] = None,
    logo_label: Optional[str] = None,
) -> dict:
    """
    Render a data-rich layout flyer. Synchronous — call via run_in_executor
    from async code (same pattern as build_flyer).

    payload: layout-specific structured content (see each builder's keys).
    hero_path: local path or URL of the lead photo (property/lifestyle/asset).
    avatar_path: banker headshot for the contact chip (real photo or saved avatar).

    Returns {"path": str, "url": str}.
    """
    builder = LAYOUT_MAP.get(layout)
    if builder is None:
        raise ValueError(f"Unknown layout '{layout}'. Valid: {sorted(LAYOUT_MAP.keys())}")

    t = _theme(theme)
    brand = (brand_name or settings.flyer_brand_name or settings.app_name).upper()
    avatar = _fetch_image(avatar_path)
    hero = _fetch_image(hero_path)

    img = builder(payload, t, brand, avatar, hero)

    if logo_path and Path(logo_path).exists():
        try:
            _apply_logo(img, Image.open(logo_path), logo_label or "", t, "layout")
        except Exception as exc:
            log.warning("flyer_layouts.logo_apply_failed", error=str(exc))

    out_dir = Path(settings.media_storage_path) / "flyers"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"flyer_{layout}_{uuid.uuid4().hex[:10]}.jpg"
    out_path = out_dir / filename
    img.save(out_path, "JPEG", quality=92, optimize=True)
    served_url = f"{settings.backend_url}/media/flyers/{filename}"
    log.info("flyer_layouts.saved", filename=filename, layout=layout)
    return {"path": str(out_path), "url": served_url}

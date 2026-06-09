"""
QR code generation service.

Generates QR codes as base64-encoded PNG data URIs for embedding
directly in HTML mail templates — no external image hosting needed.

Usage:
    from app.services.qr_service import qr_data_uri, qr_base64

    # In a mail template:
    img_src = qr_data_uri("https://your-calcom-url/...")
    # → "data:image/png;base64,iVBOR..."

    html = f'<img src="{img_src}" width="80" height="80" alt="Scan to respond">'
"""

import base64
import io
from typing import Optional
import structlog

log = structlog.get_logger()

# Fallback SVG if qrcode lib is unavailable
_FALLBACK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">'
    '<rect width="80" height="80" fill="#f5f5f5" rx="4"/>'
    '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
    'font-size="8" fill="#999">Scan</text>'
    '</svg>'
)


def qr_base64(url: str, size: int = 10, border: int = 2) -> Optional[str]:
    """
    Generate a QR code for `url` and return raw base64-encoded PNG bytes.
    Returns None if qrcode library is not installed.

    Args:
        url:    The URL to encode
        size:   Box size in pixels (controls overall image size; 10 → ~140px)
        border: Quiet zone in boxes (2 is compact, 4 is spec-compliant)
    """
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage

        qr = qrcode.QRCode(
            version=None,          # auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=border,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Try PIL first (richer output), fall back to pure PNG
        try:
            from PIL import Image as PILImage
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except ImportError:
            img = qr.make_image(image_factory=PyPNGImage)
            buf = io.BytesIO()
            img.save(buf)
            return base64.b64encode(buf.getvalue()).decode("ascii")

    except ImportError:
        log.warning("qr_service.qrcode_not_installed", url=url[:40])
        return None
    except Exception as e:
        log.error("qr_service.generation_failed", url=url[:40], error=str(e))
        return None


def qr_data_uri(url: str, size: int = 10, border: int = 2) -> str:
    """
    Generate a QR code and return a data URI suitable for use in <img src="...">.
    Falls back to a plain SVG placeholder if the library isn't installed.

    Example:
        <img src="{qr_data_uri(tracking_url)}" width="80" height="80">
    """
    b64 = qr_base64(url, size=size, border=border)
    if b64:
        return f"data:image/png;base64,{b64}"
    # Fallback: inline SVG data URI
    svg_b64 = base64.b64encode(_FALLBACK_SVG.encode()).decode("ascii")
    return f"data:image/svg+xml;base64,{svg_b64}"


def qr_img_tag(url: str, width: int = 80, alt: str = "Scan to respond") -> str:
    """Return a complete <img> HTML tag with embedded QR code."""
    src = qr_data_uri(url)
    return f'<img src="{src}" width="{width}" height="{width}" alt="{alt}" style="display:block;">'

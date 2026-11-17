"""Tách nền nhân vật/đạo cụ (rembg, model isnet-anime, chạy trên máy, miễn phí)."""
from pathlib import Path

from PIL import Image

_session = None


def cutout(src: Path, dst: Path, pad: int = 8) -> Path:
    """Ảnh nền trắng → PNG trong suốt, cắt sát nhân vật."""
    global _session
    from rembg import new_session, remove
    if _session is None:
        _session = new_session("isnet-anime")
    img = Image.open(src).convert("RGBA")
    out = remove(img, session=_session, post_process_mask=True)
    bbox = out.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
    if bbox:
        l, t, r, b = bbox
        out = out.crop((max(0, l - pad), max(0, t - pad), min(out.width, r + pad), min(out.height, b + pad)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return dst

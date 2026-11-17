"""Biến thể hoạt cảnh (miệng mở / nhắm mắt) cho 1 tư thế nhân vật.

AI vẽ lại cả ảnh nên biến thể thường lệch vài px / tỉ lệ so với ảnh gốc → nếu bật/tắt trực tiếp sẽ giật.
Cách xử lý: căn biến thể khớp ảnh gốc (dò dịch + co giãn theo bóng nhân vật), rồi CHỈ lấy vùng khác biệt
ở phần đầu (miệng/mắt) dán lên ảnh gốc. Kết quả: cùng khung, cùng viền với ảnh tách nền gốc → chồng lớp không giật.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

_session = None


def _alpha(img: Image.Image) -> np.ndarray:
    global _session
    from rembg import new_session, remove
    if _session is None:
        _session = new_session("isnet-anime")
    a = remove(img.convert("RGBA"), session=_session, post_process_mask=True).getchannel("A")
    return np.asarray(a, dtype=np.float32) / 255.0


def _fit(base_a, var_img, var_a, k=4):
    """Tìm (scale, dx, dy) để bóng biến thể khớp bóng gốc nhất (IoU). Dò trên ảnh thu nhỏ 1/k rồi áp lên ảnh thật."""
    H, W = base_a.shape

    def place(im, s, dx, dy, size, fill, resample):
        w, h = im.size
        r = im.resize((max(1, round(w * s)), max(1, round(h * s))), resample)
        c = Image.new(im.mode, size, fill)
        c.paste(r, ((size[0] - r.width) // 2 + dx, (size[1] - r.height) // 2 + dy))
        return c

    sw, sh = W // k, H // k
    bs = np.asarray(Image.fromarray((base_a * 255).astype(np.uint8)).resize((sw, sh))) > 127
    vs = Image.fromarray((var_a * 255).astype(np.uint8)).resize((sw, sh))

    def score(s, dx, dy):
        w = np.asarray(place(vs, s, dx, dy, (sw, sh), 0, Image.BILINEAR)) > 127
        return (w & bs).sum() / max(1, (w | bs).sum())

    best = max(((score(s, dx, dy), s, dx, dy) for s in np.arange(0.90, 1.101, 0.01)
                for dy in range(-14, 15, 2) for dx in range(-14, 15, 2)))
    _, s0, dx0, dy0 = best
    best = max([best] + [(score(s, dx, dy), s, dx, dy) for s in np.arange(s0 - 0.01, s0 + 0.0101, 0.0025)
                         for dy in range(dy0 - 2, dy0 + 3) for dx in range(dx0 - 2, dx0 + 3)])
    iou, s, dx, dy = best
    return place(var_img.convert("RGB"), s, dx * k, dy * k, (W, H), (255, 255, 255), Image.LANCZOS), iou


def make_variant(base_raw: Path, var_raw: Path, out_png: Path, pad: int = 8, head_frac: float = 0.42) -> dict:
    """base_raw / var_raw: ảnh nền trắng do AI vẽ (cùng nhân vật, cùng tư thế). out_png: PNG trong suốt,
    cùng khung cắt với cutout(base_raw) → dùng làm lớp chồng."""
    base = Image.open(base_raw).convert("RGB")
    var = Image.open(var_raw).convert("RGB")
    if var.size != base.size:
        var = var.resize(base.size, Image.LANCZOS)
    base_a = _alpha(base)
    var_a = _alpha(var)
    aligned, iou = _fit(base_a, var, var_a)

    b = np.asarray(base, dtype=np.float32)
    v = np.asarray(aligned, dtype=np.float32)
    diff = np.abs(b - v).max(axis=2)
    ys, xs = np.where(base_a > 0.5)
    top, bottom = ys.min(), ys.max()
    head_bottom = int(top + (bottom - top) * head_frac)
    mask = (diff > 40).astype(np.uint8) * 255
    mask[head_bottom:, :] = 0                     # chỉ lấy thay đổi ở phần đầu
    mask[base_a < 0.5] = 0                         # không vẽ ra ngoài bóng gốc
    m = Image.fromarray(mask).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
    mf = np.asarray(m, dtype=np.float32)[..., None] / 255.0
    comp = (b * (1 - mf) + v * mf).clip(0, 255).astype(np.uint8)

    out = Image.fromarray(comp).convert("RGBA")
    out.putalpha(Image.fromarray((base_a * 255).astype(np.uint8)))
    bbox = Image.fromarray(((base_a * 255) > 20).astype(np.uint8) * 255).getbbox()
    if bbox:
        l, t, r, bt = bbox
        out = out.crop((max(0, l - pad), max(0, t - pad), min(out.width, r + pad), min(out.height, bt + pad)))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_png)
    return {"iou": round(float(iou), 3), "changed_px": int((mask > 0).sum())}

"""Thư viện tài sản dùng chung giữa các video: nền, nhân vật (biểu cảm), đạo cụ."""
import json
from pathlib import Path

from .config import ROOT

LIB = ROOT / "library"
INDEX = LIB / "index.json"


def load() -> dict:
    if INDEX.exists():
        return json.loads(INDEX.read_text(encoding="utf-8"))
    return {"nen": {}, "nhan_vat": {}, "dao_cu": {}}


def save(idx: dict):
    LIB.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def nen_path(nid) -> Path:
    return LIB / "nen" / f"{nid}.png"


def char_dir(cid) -> Path:
    return LIB / "nhan_vat" / cid


def bieu_cam_path(cid, bc) -> Path:
    return char_dir(cid) / f"{bc}.png"


def dao_cu_path(did) -> Path:
    return LIB / "dao_cu" / f"{did}.png"


def summary(idx: dict) -> str:
    """Tóm tắt ngắn cho agent Đạo diễn (để dùng lại tài sản) — không gửi cả file."""
    nen = ", ".join(idx["nen"].keys()) or "(trống)"
    return f"Nền đã có: {nen}"

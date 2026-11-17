"""🤖 Quản lý thư viện — đối chiếu storyboard với library/, liệt kê phần còn thiếu + ước tính chi phí."""
import json

from .. import ai33, library
from ..config import ROOT, load_config

NAME = "thu_vien"


def price_vnd(model_id: str, with_refs: bool) -> float:
    rows = {r["model_id"]: r for r in json.loads((ROOT / "lab" / "models.json").read_text(encoding="utf-8"))}
    r = rows.get(model_id, {})
    credits = (r.get("price2") if with_refs else r.get("price0")) or r.get("price0") or 1200
    return credits * ai33.VND_PER_CREDIT


def plan(p) -> dict:
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    idx = library.load()
    chars = {c["id"]: c for c in board["nhan_vat"]}
    need = {"nen": {}, "nhan_vat_goc": [], "bieu_cam": {}, "dac_biet": []}
    for c in board["nhan_vat"]:
        if not (library.char_dir(c["lib_id"]) / "goc.png").exists():
            need["nhan_vat_goc"].append(c["lib_id"])
    for s in board["canh"]:
        if s.get("dac_biet_en"):
            if not p.path("dac_biet", f"{s['id']:03d}.png").exists():
                need["dac_biet"].append(s["id"])
            continue
        if not library.nen_path(s["nen"]).exists() and s["nen"] not in need["nen"]:
            need["nen"][s["nen"]] = s.get("nen_mo_ta_en") or s["nen"].replace("_", " ")
        for c in s["nhan_vat"]:
            lib_id = chars[c["id"]]["lib_id"]
            key = f"{lib_id}/{c['bieu_cam']}"
            if c["bieu_cam"] != "binh_thuong" and not library.bieu_cam_path(lib_id, c["bieu_cam"]).exists():
                need["bieu_cam"].setdefault(key, c.get("bieu_cam_en") or c["bieu_cam"].replace("_", " "))
    return need


def run(p):
    cfg = load_config()
    need = plan(p)
    mc, mb = cfg["image_model_character"], cfg["image_model_background"]
    cost = (len(need["nhan_vat_goc"]) * price_vnd(mc, False) + len(need["bieu_cam"]) * price_vnd(mc, True)
            + len(need["nen"]) * price_vnd(mb, False) + len(need["dac_biet"]) * price_vnd(mc, True))
    need["uoc_tinh_vnd"] = round(cost)
    p.path("can_ve.json").write_text(json.dumps(need, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(need["nhan_vat_goc"]) + len(need["bieu_cam"]) + len(need["nen"]) + len(need["dac_biet"])
    p.handoff(NAME, "hoa_si",
              f"Cần vẽ {n} ảnh: {len(need['nhan_vat_goc'])} nhân vật, {len(need['bieu_cam'])} biểu cảm, "
              f"{len(need['nen'])} nền, {len(need['dac_biet'])} cảnh đặc biệt",
              ["can_ve.json"], f"Ước tính {cost:,.0f}đ".replace(",", "."))
    return need

"""🤖 Đạo diễn phân cảnh — hồ sơ nhân vật + công thức dàn cảnh từng cảnh."""
import difflib
import json
import re

from .. import library
from ..config import load_config
from ..deepseek import ask_json

NAME = "dao_dien"
POS = {"trai", "giua", "phai"}
MOTIONS = {"dung", "truot_vao", "nhun", "rung", "lat"}

SCENE_SHAPE = ('{"canh": [{"loi_ke": "nguyên văn", "nen": "id_nen", "nen_mo_ta_en": "mô tả nền tiếng Anh, không người", '
               '"nhan_vat": [{"id": "id nhân vật", "bieu_cam": "id_bieu_cam", "bieu_cam_en": "expression/pose in English", '
               '"vi_tri": "trai|giua|phai", "chuyen_dong": "dung|truot_vao|nhun|rung|lat"}], '
               '"chu_nhan": "", "dac_biet_en": ""}]}')


def _chunks(text, size=1600):
    paras = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) > size:
            yield buf
            buf = ""
        buf = (buf + "\n\n" + para).strip()
    if buf:
        yield buf


def _norm(s):
    return re.sub(r"\W+", " ", s.lower()).strip()


def _lib_chars(pid):
    """Nhân vật đã có ảnh của video này: {id_ngắn: [biểu cảm có file]} (đọc thẳng đĩa, không tin index)."""
    out = {}
    for d in sorted(library.LIB.joinpath("nhan_vat").glob(f"{pid}_*")):
        if (d / "goc.png").exists():
            out[d.name[len(pid) + 1:]] = sorted(f.stem for f in d.glob("*.png")
                                                if f.stem != "goc" and "__" not in f.stem and not f.stem.startswith("_"))
    return out


def _match_id(cid, have):
    """'hung' ↔ 'anh_hung', 'sep' ↔ 'ong_sep'…: ghép id mới vào nhân vật đã có nếu một bên chứa bên kia."""
    if cid in have:
        return cid
    for h in have:
        a, b = set(cid.split("_")), set(h.split("_"))
        if a <= b or b <= a:
            return h
    return cid


def _gom(p, ch, scenes, have_bc, cfg):
    """Gộp biểu cảm mới trùng nghĩa về ảnh có sẵn, giới hạn số biểu cảm mới; chọn ≤5 cảnh đặc biệt đắt nhất."""
    cap = cfg.get("max_bieu_cam_moi", 6)
    new = {}
    for s in scenes:
        for c in s["nhan_vat"]:
            if c["bieu_cam"] != "binh_thuong" and c["bieu_cam"] not in have_bc.get(c["id"], set()):
                k = (c["id"], c["bieu_cam"])
                new.setdefault(k, {"n": 0, "en": c.get("bieu_cam_en", "")})["n"] += 1
    lst = "\n".join(f"- {cid}/{bc} (dùng {v['n']} cảnh): {v['en']}" for (cid, bc), v in sorted(new.items()))
    have_txt = "\n".join(f"- {cid}: binh_thuong, {', '.join(sorted(v))}" for cid, v in have_bc.items())
    lines = "\n".join(f"{s['id']}: {s['loi_ke'][:90]}" for s in scenes)
    half = len(scenes) // 2
    res = ask_json(NAME,
        "VIỆC 1 — GOM BIỂU CẢM. Mỗi biểu cảm mới tốn ~200đ để vẽ. MẶC ĐỊNH phải ánh xạ mỗi biểu cảm mới về biểu cảm "
        "ĐÃ CÓ của cùng nhân vật gần nghĩa nhất (kể cả binh_thuong). Ví dụ: ngac_nhien/kinh_ngac → mo_mong; "
        "lo_lang → hoi_hop; buon_ba → ngan_ngui; hien_lanh/hy_vong → cuoi_hien; tu_tin → quyet_tam; go_ban → noi_chuyen. "
        f"Chỉ ghi \"giu\" khi KHÔNG có biểu cảm nào gần nghĩa VÀ đó là khoảnh khắc mạnh; tối đa {cap} cái \"giu\" cả video. "
        "Nhân vật chưa có biểu cảm nào → ánh xạ về binh_thuong, chỉ giữ 1–2 cái quan trọng nhất.\n"
        f"Biểu cảm ĐÃ CÓ ẢNH (0đ):\n{have_txt or '(chưa có)'}\n\nBiểu cảm MỚI đề xuất:\n{lst or '(không)'}\n\n"
        "VIỆC 2 — CẢNH ĐẶC BIỆT (vẽ nguyên khung, đúng 5 cảnh). Đọc HẾT danh sách rồi chọn 5 khoảnh khắc ĐẮT nhất: "
        f"câu móc mở đầu, twist, cao trào, cái kết. Bắt buộc ít nhất 2 cảnh có id > {half} (nửa sau, nơi có cao trào). "
        "Ưu tiên cận cảnh đồ vật/hành động then chốt mà sticker không diễn được. KHÔNG chọn cảnh chuyển cảnh, "
        "lật lịch, đứng hình chung chung. Mô tả tiếng Anh cụ thể (bố cục, đồ vật, nhân vật làm gì).\n"
        f"Danh sách cảnh:\n{lines}",
        '{"gom": {"id_nv/bieu_cam_moi": "bieu_cam_da_co | giu"}, "dac_biet": [{"id": 1, "mo_ta_en": "..."}]}')
    gom = res.get("gom", {})
    kept = []
    for (cid, bc), v in sorted(new.items(), key=lambda kv: -kv[1]["n"]):
        to = gom.get(f"{cid}/{bc}", "giu")
        if to != "giu" and (to == "binh_thuong" or to in have_bc.get(cid, set())):
            v["to"] = to
        elif len(kept) < cap:
            kept.append((cid, bc))
        else:
            v["to"] = "binh_thuong"  # vượt trần → mặt bình thường
    for s in scenes:
        for c in s["nhan_vat"]:
            to = new.get((c["id"], c["bieu_cam"]), {}).get("to")
            if to:
                c["bieu_cam"] = to
    db = [d for d in res.get("dac_biet", []) if isinstance(d, dict) and d.get("mo_ta_en")][:5]
    if db:
        by = {s["id"]: s for s in scenes}
        for s in scenes:
            s["dac_biet_en"] = ""
        for d in db:
            if d.get("id") in by:
                by[d["id"]]["dac_biet_en"] = d["mo_ta_en"]
    print(f"  • Gom biểu cảm: {len(new)} mới đề xuất → giữ {len(kept)}; cảnh đặc biệt: "
          + ", ".join(str(s["id"]) for s in scenes if s.get("dac_biet_en")))


def run(p):
    cfg = load_config()
    spent0 = p.spent_vnd
    story = p.path("story.md").read_text(encoding="utf-8")
    body = "\n".join(l for l in story.splitlines() if not l.startswith("# "))

    print("  • Hồ sơ nhân vật")
    have = _lib_chars(p.id)
    have_txt = ("\nNHÂN VẬT ĐÃ CÓ ẢNH (dùng lại ĐÚNG id này nếu là cùng người, không tạo id mới): "
                + ", ".join(have) + "\n") if have else ""
    ch = ask_json(NAME, "Đọc kịch bản, liệt kê nhân vật xuất hiện (kể cả người kể 'tôi'), tối đa 6 người. "
                        "Ngoại hình đơn giản, dễ phân biệt, hợp bối cảnh.\n" + have_txt + "\nKỊCH BẢN:\n" + body,
                  '{"nhan_vat": [{"id": "snake_case", "ten": "tên/vai", "ngoai_hinh_en": "English: gender, age, '
                  'hair, outfit colors, 1 signature item"}]}')["nhan_vat"]
    used = set()
    for c in ch:
        m = _match_id(c["id"], have)
        c["id"] = m if m not in used else c["id"]  # 2 người khác nhau không được dồn vào 1 ảnh
        used.add(c["id"])
    ids = {c["id"] for c in ch}
    char_txt = "\n".join(f"- {c['id']}: {c['ten']} — {c['ngoai_hinh_en']}" for c in ch)

    idx = library.load()
    known_bg = set(idx["nen"]) | {f.stem for f in library.LIB.joinpath("nen").glob("*.png")}
    have_bc = {c["id"]: set(have.get(c["id"], [])) for c in ch}
    known_bc = {c["id"]: set(v) for c, v in zip(ch, have_bc.values())}
    scenes = []
    parts = list(_chunks(body))
    for i, part in enumerate(parts, 1):
        print(f"  • Chia cảnh phần {i}/{len(parts)}")
        reuse = (f"Nền đã có (ưu tiên dùng lại đúng id): {', '.join(sorted(known_bg)) or '(chưa có)'}\n"
                 + "Biểu cảm đã có (ƯU TIÊN dùng lại đúng id — biểu cảm mới tốn tiền vẽ): "
                 + "; ".join(f"{k}: binh_thuong, {', '.join(sorted(v))}" for k, v in known_bc.items()))
        res = ask_json(NAME, f"Mỗi cảnh ~{cfg['scene_seconds']} giây (~{cfg['scene_seconds'] * 17} ký tự).\n"
                             f"Nhân vật:\n{char_txt}\n\n{reuse}\n\nĐOẠN KỊCH BẢN:\n{part}", SCENE_SHAPE)
        got = res.get("canh", [])
        ratio = difflib.SequenceMatcher(None, _norm(" ".join(s.get("loi_ke", "") for s in got)), _norm(part)).ratio()
        if ratio < 0.9:
            print(f"    ⚠ phần {i} lời kể khớp {ratio:.0%} → chia lại")
            res = ask_json(NAME, f"LẦN TRƯỚC BẠN SỬA/BỎ LỜI KỂ. Giữ NGUYÊN VĂN 100%.\nNhân vật:\n{char_txt}\n\n{reuse}\n\n"
                                 f"ĐOẠN KỊCH BẢN:\n{part}", SCENE_SHAPE)
            got = res.get("canh", [])
        for s in got:
            s["nhan_vat"] = [c for c in s.get("nhan_vat", []) if c.get("id") in ids][:3]
            for c in s["nhan_vat"]:
                c["vi_tri"] = c.get("vi_tri") if c.get("vi_tri") in POS else "giua"
                c["chuyen_dong"] = c.get("chuyen_dong") if c.get("chuyen_dong") in MOTIONS else "dung"
                c["bieu_cam"] = re.sub(r"[^a-z0-9_]", "", (c.get("bieu_cam") or "binh_thuong").lower()) or "binh_thuong"
                known_bc[c["id"]].add(c["bieu_cam"])
            s["nen"] = re.sub(r"[^a-z0-9_]", "", (s.get("nen") or "nen_chung").lower())
            known_bg.add(s["nen"])
            scenes.append(s)

    for n, s in enumerate(scenes, 1):
        s["id"] = n
    print("  • Gom biểu cảm + chọn cảnh đặc biệt")
    _gom(p, ch, scenes, have_bc, cfg)
    known_bc = {c["id"]: set() for c in ch}
    for s in scenes:
        for c in s["nhan_vat"]:
            known_bc[c["id"]].add(c["bieu_cam"])
    # ép tối đa 5 cảnh đặc biệt
    sp = [s for s in scenes if s.get("dac_biet_en")]
    for s in sp[5:]:
        s["dac_biet_en"] = ""
    for n, s in enumerate(scenes, 1):
        s["id"] = n
    # id nhân vật trong thư viện = <mã video>_<id> (nhân vật của từng truyện là riêng)
    for c in ch:
        c["lib_id"] = f"{p.id}_{c['id']}"
    board = {"tieu_de": story.splitlines()[0].lstrip("# ").strip(), "nhan_vat": ch, "canh": scenes}
    p.path("storyboard.json").write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    n_bg = len({s["nen"] for s in scenes})
    n_bc = sum(len(v) for v in known_bc.values())
    p.handoff(NAME, "thu_vien", f"{len(scenes)} cảnh, {len(ch)} nhân vật, {n_bg} nền, {n_bc} biểu cảm, {len(sp[:5])} cảnh đặc biệt",
              ["storyboard.json"], "", p.spent_vnd - spent0)

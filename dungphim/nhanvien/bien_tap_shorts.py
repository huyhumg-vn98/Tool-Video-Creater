"""🤖 Biên tập Shorts — viết lại thành bản tóm tắt dọc, chọn cảnh minh họa từ bản dài."""
import json

from ..deepseek import ask_json

NAME = "bien_tap_shorts"


def run(p):
    spent0 = p.spent_vnd
    story = p.path("story.md").read_text(encoding="utf-8")
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    menu = "\n".join(f"{s['id']}: {s['loi_ke'][:90]}" for s in board["canh"])
    res = ask_json(NAME, f"CÂU CHUYỆN:\n{story}\n\nCÁC CẢNH CÓ SẴN (id: lời kể):\n{menu}",
                   '{"tieu_de_tren": "3-7 chữ", "canh": [{"loi_ke": "1-2 câu", "dung_canh": id_canh_ban_dai, '
                   '"chu_nhan": ""}]}', max_tokens=6000)
    valid = {s["id"] for s in board["canh"]}
    canh = []
    for i, c in enumerate(res["canh"], 1):
        if c.get("dung_canh") not in valid:
            c["dung_canh"] = board["canh"][min(len(board["canh"]) - 1, i)]["id"]
        c["id"] = i
        canh.append(c)
    short = {"tieu_de_tren": res.get("tieu_de_tren", ""), "canh": canh}
    p.path("short.json").write_text(json.dumps(short, ensure_ascii=False, indent=2), encoding="utf-8")
    chars = sum(len(c["loi_ke"]) for c in canh)
    p.handoff(NAME, "long_tieng", f"Bản tóm tắt {len(canh)} cảnh, {chars} ký tự (~{chars / 17:.0f} giây)",
              ["short.json"], "", p.spent_vnd - spent0)

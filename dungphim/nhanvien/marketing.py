"""🤖 Marketing — tiêu đề, mô tả, hashtag (DeepSeek) + 2 thumbnail ghép từ thư viện (0đ)."""
import json

from PIL import Image, ImageDraw, ImageFont

from .. import library
from ..config import ROOT
from ..deepseek import ask_json

NAME = "marketing"
FONT = str(ROOT / "fonts" / "Anton-Regular.ttf")


def _thumb(p, scene, chars, lines, out):
    W, H = 1280, 720
    sp = p.path("dac_biet", f"{scene['id']:03d}.png")
    special = scene.get("dac_biet_en") and sp.exists()
    bg = Image.open(sp if special else library.nen_path(scene["nen"])).convert("RGB")
    sc = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * sc), int(bg.height * sc)))
    img = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    if not special:
        # nhân vật to ở nửa trái
        n = len(scene["nhan_vat"][:2]) or 1
        for i, c in enumerate(scene["nhan_vat"][:2]):
            lib_id = chars[c["id"]]["lib_id"]
            f = library.bieu_cam_path(lib_id, c["bieu_cam"])
            f = f if f.exists() else library.bieu_cam_path(lib_id, "binh_thuong")
            if not f.exists():
                continue
            s = Image.open(f).convert("RGBA")
            h = int(H * (1.05 if i == 0 else 0.85))
            s = s.resize((int(s.width * h / s.height), h))
            x = int(W * (0.25 if n == 1 else (0.17 if i == 0 else 0.4)) - s.width / 2)
            img.paste(s, (x, H - int(h * 0.92)), s)
    d = ImageDraw.Draw(img)
    box_w, y = int(W * 0.46), int(H * 0.14)
    for i, line in enumerate(lines[:3]):
        size = 150
        while size > 50:
            font = ImageFont.truetype(FONT, size)
            if d.textlength(line, font=font) <= box_w:
                break
            size -= 4
        w = d.textlength(line, font=font)
        d.text((W - box_w / 2 - w / 2 - 28, y), line, font=font, fill=["#111111", "#E3201B", "#111111"][i % 3],
               stroke_width=9, stroke_fill="white")
        y += int(size * 1.22)
    img.save(out)


def run(p):
    spent0 = p.spent_vnd
    story = p.path("story.md").read_text(encoding="utf-8")
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    short = json.loads(p.path("short.json").read_text(encoding="utf-8"))
    m = ask_json(NAME, f"Tiêu đề kịch bản: {board['tieu_de']}\nTiêu đề bản Shorts: {short.get('tieu_de_tren')}\n\n"
                       f"Mở đầu câu chuyện:\n{story[:1500]}",
                 '{"tieu_de": ["3 phương án"], "chu_thumbnail": [["dòng 1", "dòng 2"], ["dòng 1", "dòng 2"]], '
                 '"mo_ta": "...", "hashtag": ["#..."], "shorts": {"tieu_de": "...", "mo_ta": "...", "binh_luan_ghim": "..."}}')
    md = [f"# Marketing — {p.id}", "", "## Bản dài (16:9)", "", "**Tiêu đề (chọn 1):**"]
    md += [f"{i}. {t}" for i, t in enumerate(m["tieu_de"], 1)]
    md += ["", "**Mô tả:**", "", m["mo_ta"], "", " ".join(m.get("hashtag", [])), "",
           "## Bản Shorts (9:16)", "", f"**Tiêu đề:** {m['shorts']['tieu_de']}", "",
           f"**Mô tả:** {m['shorts']['mo_ta']}", "", f"**Bình luận ghim:** {m['shorts']['binh_luan_ghim']}"]
    p.path("marketing.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    chars = {c["id"]: c for c in board["nhan_vat"]}
    sc = board["canh"]
    # A: cảnh đặc biệt hoặc cảnh có chữ nhấn ở 60-90% câu chuyện; B: cảnh 2 nhân vật
    late = sc[int(len(sc) * 0.6):int(len(sc) * 0.9)] or sc
    a = next((s for s in late if s.get("dac_biet_en")), None) or next((s for s in late if s.get("chu_nhan")), late[0])
    b = next((s for s in sc if len(s["nhan_vat"]) >= 2 and s is not a), sc[0])
    cts = m["chu_thumbnail"] + [["", ""]] * 2
    _thumb(p, a, chars, [x.upper() for x in cts[0]], p.path("thumbnail_A.png"))
    _thumb(p, b, chars, [x.upper() for x in cts[1]], p.path("thumbnail_B.png"))
    p.handoff(NAME, "giam_doc", "3 tiêu đề, mô tả, hashtag, 2 thumbnail",
              ["marketing.md", "thumbnail_A.png", "thumbnail_B.png"], "", p.spent_vnd - spent0)

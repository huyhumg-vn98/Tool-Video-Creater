"""🤖 Họa sĩ — vẽ phần còn thiếu (ai33), tách nền (rembg), ghép ảnh lưới để Giám đốc duyệt."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image, ImageDraw, ImageFont

from .. import ai33, library
from ..config import ROOT, load_config
from ..cutout import cutout

NAME = "hoa_si"
NO_TEXT = "No text, no letters, no captions, no speech bubbles, no watermark, no logo."
WHITE = "on a plain pure white background, no shadow, no ground"


def _params(model_id, ar):
    rows = {r["model_id"]: r for r in json.loads((ROOT / "lab" / "models.json").read_text(encoding="utf-8"))}
    r = rows[model_id]
    return ai33.model_params({"aspect_ratios": r["aspect_ratios"], "resolutions": r["resolutions"]}, ar)


def _par(jobs, workers):
    errs = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn): name for name, fn in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
                print(f"    [{i}/{len(jobs)}] {futs[f]} ✓")
            except Exception as e:  # noqa: BLE001
                errs.append(futs[f])
                print(f"    [{i}/{len(jobs)}] {futs[f]} ✗ {e}")
    return errs


def _schedule(jobs: dict, workers: int) -> list:
    """jobs = {tên: (hàm, {nhân vật gốc phải xong trước})}. Chạy song song, mở khoá việc phụ thuộc ngay khi đủ điều kiện.
    Nhân vật gốc lỗi → việc phụ thuộc bị bỏ (ghi lỗi)."""
    from concurrent.futures import FIRST_COMPLETED, wait
    errs, done_goc, failed_goc = [], set(), set()
    waiting = dict(jobs)
    total, n = len(jobs), 0
    if total:
        print(f"  • Vẽ {total} ảnh (song song {workers}, việc nào đủ điều kiện là vẽ ngay)")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        running = {}

        def launch():
            for name in [k for k, (_, dep) in waiting.items() if dep <= done_goc]:
                running[ex.submit(waiting.pop(name)[0])] = name
            for name in [k for k, (_, dep) in waiting.items() if dep & failed_goc]:
                waiting.pop(name)
                errs.append(name)
                print(f"    ✗ {name} — bỏ vì nhân vật gốc lỗi")
        launch()
        while running:
            fin, _ = wait(running, return_when=FIRST_COMPLETED)
            for f in fin:
                name = running.pop(f)
                n += 1
                lib = name[len("nhân vật "):] if name.startswith("nhân vật ") else None
                try:
                    f.result()
                    print(f"    [{n}/{total}] {name} ✓")
                    if lib:
                        done_goc.add(lib)
                except Exception as e:  # noqa: BLE001
                    errs.append(name)
                    print(f"    [{n}/{total}] {name} ✗ {e}")
                    if lib:
                        failed_goc.add(lib)
            launch()
    return errs


def draw(p, need: dict):
    cfg = load_config()
    style, mc, mb = cfg["style"], cfg["image_model_character"], cfg["image_model_background"]
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    by_lib = {c["lib_id"]: c for c in board["nhan_vat"]}
    idx = library.load()
    w = cfg["concurrency"]
    errs = []

    # 1. nhân vật gốc
    def goc(lib_id):
        c = by_lib[lib_id]
        d = library.char_dir(lib_id)
        d.mkdir(parents=True, exist_ok=True)
        ai33.generate_image(f"{style}. Full body view of ONE single character standing, facing the viewer, {WHITE}. "
                            f"{c['ngoai_hinh_en']}. {NO_TEXT}", d / "goc.png", mc, _params(mc, "3:4"),
                            note=f"nhân vật {lib_id}")
        cutout(d / "goc.png", d / "binh_thuong.png")

    # 2. biểu cảm (dùng ảnh gốc làm tham chiếu @img1)
    def bc(key, en):
        lib_id, name = key.split("/")
        d = library.char_dir(lib_id)
        raw = d / f"_{name}_raw.png"
        ai33.generate_image(f"{style}. The exact same character as @img1 (same face, hair, outfit, colors, proportions), "
                            f"now: {en}. Full body, ONE character only, {WHITE}. {NO_TEXT}",
                            raw, mc, _params(mc, "3:4"), assets=[d / "goc.png"], note=f"biểu cảm {key}")
        cutout(raw, library.bieu_cam_path(lib_id, name))
        raw.unlink(missing_ok=True)

    # 3. nền
    def nen(nid, en):
        library.nen_path(nid).parent.mkdir(parents=True, exist_ok=True)
        ai33.generate_image(f"{style}. Wide empty background scene, absolutely no people, no characters, no animals: {en}. "
                            f"Leave open ground space in the lower half for characters. {NO_TEXT}",
                            library.nen_path(nid), mb, _params(mb, "16:9"), note=f"nền {nid}")
        idx["nen"][nid] = {"mo_ta_en": en}

    # 4. cảnh đặc biệt (nguyên khung)
    scenes = {s["id"]: s for s in board["canh"]}
    chars = {c["id"]: c for c in board["nhan_vat"]}

    def dac_biet(sid):
        s = scenes[sid]
        assets, refs = [], []
        for c in s["nhan_vat"][:3]:
            g = library.char_dir(chars[c["id"]]["lib_id"]) / "goc.png"
            if g.exists():
                assets.append(g)
                refs.append(f"@img{len(assets)} is {chars[c['id']]['ten']}")
        p.path("dac_biet").mkdir(exist_ok=True)
        ai33.generate_image(f"{style}. {s['dac_biet_en']}. " + ("; ".join(refs) + ". Keep characters identical to references. " if refs else "")
                            + NO_TEXT, p.path("dac_biet", f"{sid:03d}.png"), mc, _params(mc, "16:9"),
                            assets=assets, note=f"cảnh đặc biệt {sid}")
    # Lịch vẽ theo phụ thuộc: nền + mọi thứ chỉ cần nhân vật đã có → vẽ ngay; biểu cảm / cảnh đặc biệt
    # cần nhân vật mới → bắt đầu ngay khi ảnh gốc của nhân vật đó xong (không chờ cả đợt).
    jobs = {}  # tên → (hàm, {lib_id gốc cần chờ})
    for x in need["nhan_vat_goc"]:
        jobs[f"nhân vật {x}"] = (lambda x=x: goc(x), set())
    for k, en in need["bieu_cam"].items():
        lib = k.split("/")[0]
        jobs[f"biểu cảm {k}"] = (lambda k=k, en=en: bc(k, en), {lib} & set(need["nhan_vat_goc"]))
    for k, en in need["nen"].items():
        jobs[f"nền {k}"] = (lambda k=k, en=en: nen(k, en), set())
    for sid in need["dac_biet"]:
        libs = {chars[c["id"]]["lib_id"] for c in scenes[sid]["nhan_vat"][:3] if c["id"] in chars}
        jobs[f"cảnh đặc biệt {sid}"] = (lambda s=sid: dac_biet(s), libs & set(need["nhan_vat_goc"]))
    errs += _schedule(jobs, w)

    for lib_id, c in by_lib.items():
        d = library.char_dir(lib_id)
        if (d / "goc.png").exists():
            idx["nhan_vat"][lib_id] = {"ten": c["ten"], "ngoai_hinh_en": c["ngoai_hinh_en"],
                                       "bieu_cam": sorted(x.stem for x in d.glob("*.png") if x.stem != "goc" and not x.stem.startswith("_"))}
    library.save(idx)
    return errs


# ------------------------------------------------------------------ ảnh lưới để duyệt
def preview(p, scene, W=480, H=270) -> Image.Image:
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    chars = {c["id"]: c for c in board["nhan_vat"]}
    sp = p.path("dac_biet", f"{scene['id']:03d}.png")
    bg_path = sp if scene.get("dac_biet_en") and sp.exists() else library.nen_path(scene["nen"])
    img = Image.open(bg_path).convert("RGB").resize((W, H)) if bg_path.exists() else Image.new("RGB", (W, H), "#ddd")
    if not (scene.get("dac_biet_en") and sp.exists()):
        for c in scene["nhan_vat"]:
            lib_id = chars[c["id"]]["lib_id"]
            f = library.bieu_cam_path(lib_id, c["bieu_cam"])
            f = f if f.exists() else library.bieu_cam_path(lib_id, "binh_thuong")
            if not f.exists():
                continue
            s = Image.open(f).convert("RGBA")
            h = int(H * 0.64)
            s = s.resize((max(1, int(s.width * h / s.height)), h))
            x = int(W * {"trai": 0.24, "giua": 0.5, "phai": 0.76}[c["vi_tri"]] - s.width / 2)
            img.paste(s, (x, int(H * 0.97) - h), s)
    return img


def grid(p):
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    cols, W, H, pad = 6, 480, 270, 8
    rows = (len(board["canh"]) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W + pad) + pad, rows * (H + pad) + pad), "white")
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    d = ImageDraw.Draw(sheet)
    for i, s in enumerate(board["canh"]):
        x, y = pad + (i % cols) * (W + pad), pad + (i // cols) * (H + pad)
        sheet.paste(preview(p, s, W, H), (x, y))
        d.text((x + 8, y + 4), str(s["id"]), fill="red", font=font, stroke_width=4, stroke_fill="white")
    out = p.path("luoi_canh.png")
    sheet.save(out, optimize=True)
    return out


def run(p, need=None):
    spent0 = p.spent_of("anh")
    need = need or json.loads(p.path("can_ve.json").read_text(encoding="utf-8"))
    errs = draw(p, need)
    g = grid(p)
    p.handoff(NAME, "giam_doc", f"Vẽ xong, lỗi {len(errs)} ảnh. Ảnh lưới: luoi_canh.png",
              ["luoi_canh.png", "library/"], f"Lỗi: {errs}" if errs else "", p.spent_of("anh") - spent0)
    return errs

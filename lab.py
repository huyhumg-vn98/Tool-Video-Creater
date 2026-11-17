#!/usr/bin/env python3
"""GIAI ĐOẠN 1 — Phòng thử nghiệm. Kết quả nằm trong lab/, chi phí ghi vào lab/chi_phi.csv.

  .venv/bin/python lab.py check                      # 0.2  kiểm tra key + số credit
  .venv/bin/python lab.py models                     # 1.1  giá thật mọi model ảnh (miễn phí)
  .venv/bin/python lab.py style [--models a,b,c]     # 1.2  thử nét vẽ trên 3-4 model
  .venv/bin/python lab.py narrator --model X         # 1.3  4 phương án nhân vật người kể
  .venv/bin/python lab.py voices [--provider vbee]   # 1.4a danh sách giọng (miễn phí)
  .venv/bin/python lab.py voicetest --pick 1,3,5     # 1.4b đọc thử đoạn mẫu bằng các giọng đã chọn
  .venv/bin/python lab.py cost                       #      tổng chi phí đã tiêu trong lab
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dungphim import ai33
from dungphim.config import ROOT, env, load_config

LAB = ROOT / "lab"
ai33.LEDGER = LAB / "chi_phi.csv"
CFG = load_config()
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

NO_TEXT = "No text, no letters, no captions, no speech bubbles, no watermark, no logo, no signature."

TEST_CHARACTER = ("A young Vietnamese village girl about 20 years old, black hair in a low ponytail, "
                  "yellow t-shirt, green trousers, small brown backpack, worried expression")
TEST_BACKGROUND = ("A rural Vietnamese village road beside green rice fields, bamboo trees, "
                   "a small house with a red tile roof, blue sky with a few clouds")

NARRATORS = {
    "A": "a skinny young Vietnamese man with messy black hair, round glasses, grey hoodie, permanently bored deadpan face",
    "B": "a young Vietnamese woman with a messy top bun, oversized white t-shirt, jeans, sarcastic half-smile",
    "C": "a chubby Vietnamese man with a backwards red cap, orange t-shirt, tiny eyes, smug expression",
    "D": "a tall thin Vietnamese guy with spiky hair, black t-shirt, one raised eyebrow, cool unimpressed face",
}

SAMPLE_TEXT = ("Năm đó tôi hai mươi tuổi, ngây thơ đến mức tin rằng chỉ cần qua biên giới là đổi đời. "
               "Bà mối mặc váy đỏ cười tươi như hoa, nói với mẹ tôi rằng bên đó nhà to, chồng hiền, "
               "mỗi tháng gửi về cả chục triệu. Mẹ tôi gật đầu. Tôi cũng gật đầu. "
               "Và đó là cái gật đầu đắt giá nhất cuộc đời tôi.")


# ------------------------------------------------------------------ tiện ích
def vnd(credits):
    return f"{round(float(credits) * ai33.VND_PER_CREDIT):,}đ".replace(",", ".")


def confirm(msg, yes):
    print(msg)
    if yes:
        return
    if input("Tiếp tục? (y/n) ").strip().lower() != "y":
        sys.exit("Đã huỷ.")


def grid(items, out: Path, cols, cell_w=640, title=""):
    """items: list[(path_or_None, label)] → ảnh lưới có nhãn."""
    font = ImageFont.truetype(LABEL_FONT, 26)
    tfont = ImageFont.truetype(LABEL_FONT, 34)
    cells = []
    for p, label in items:
        if p and Path(p).exists():
            im = Image.open(p).convert("RGB")
            im = im.resize((cell_w, int(im.height * cell_w / im.width)))
        else:
            im = Image.new("RGB", (cell_w, cell_w * 9 // 16), (230, 230, 230))
            ImageDraw.Draw(im).text((20, 20), "LỖI / KHÔNG CÓ ẢNH", fill="red", font=font)
        cells.append((im, label))
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    pad, lab_h, top = 16, 44, (60 if title else 0)
    row_h = [max(c[0].height for c in r) + lab_h for r in rows]
    W = cols * (cell_w + pad) + pad
    H = top + sum(row_h) + pad * (len(rows) + 1)
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((pad, 12), title, fill="black", font=tfont)
    y = top + pad
    for r, rh in zip(rows, row_h):
        x = pad
        for im, label in r:
            d.text((x, y + 6), label, fill="black", font=font)
            sheet.paste(im, (x, y + lab_h))
            x += cell_w + pad
        y += rh + pad
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def run_parallel(jobs, workers=4):
    """jobs: list[(name, fn)] → dict name -> (ok, kết quả/lỗi)."""
    res = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn): name for name, fn in jobs}
        for f in as_completed(futs):
            name = futs[f]
            try:
                res[name] = (True, f.result())
                print(f"  ✓ {name}")
            except Exception as e:  # noqa: BLE001
                res[name] = (False, e)
                print(f"  ✗ {name}: {e}")
    return res


def load_models():
    p = LAB / "models.json"
    if not p.exists():
        sys.exit("Chưa có bảng giá — chạy trước: lab.py models")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ lệnh
def cmd_check(a):
    print("• ai33:")
    print("  ", json.dumps(ai33.credits(), ensure_ascii=False))
    print("• DeepSeek:")
    from openai import OpenAI
    c = OpenAI(api_key=env("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    r = c.chat.completions.create(model=CFG["writer_model"], max_tokens=10,
                                  messages=[{"role": "user", "content": "Trả lời đúng một chữ: OK"}])
    print("  ", r.choices[0].message.content.strip())
    print("✓ Kết nối ổn")


def cmd_models(a):
    models = ai33.image_models()
    print(f"Có {len(models)} model. Đang hỏi giá (miễn phí)...")
    rows = []
    for m in models:
        mid = m["model_id"]
        params = ai33.model_params(m, "16:9")
        row = {"model_id": mid, "params": params, "supports_images": m.get("supports_images"),
               "requires_reference_images": m.get("requires_reference_images"),
               "max_assets": m.get("max_assets"), "aspect_ratios": m.get("aspect_ratios"),
               "resolutions": m.get("resolutions")}
        if m.get("requires_reference_images"):
            row["note"] = "bắt buộc ảnh tham chiếu"
        for k, n in (("price0", 0), ("price2", 2)):
            if n == 0 and m.get("requires_reference_images"):
                row[k] = None
                continue
            if n and not m.get("supports_images"):
                row[k] = None
                continue
            try:
                row[k] = ai33.image_price(mid, params, assets=n)
            except ai33.AI33Error as e:
                row[k] = None
                row["note"] = str(e)[:80]
        rows.append(row)
    rows.sort(key=lambda r: (r.get("price0") or r.get("price2") or 1e12))
    LAB.mkdir(exist_ok=True)
    (LAB / "models.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'#':>2}  {'model':<38} {'1 ảnh':>9} {'có 2 ảnh mẫu':>13}  {'ảnh mẫu':<7} độ phân giải dùng")
    for i, r in enumerate(rows, 1):
        p0 = f"{r['price0']} ({vnd(r['price0'])})" if r.get("price0") else "—"
        p2 = vnd(r["price2"]) if r.get("price2") else "—"
        print(f"{i:>2}. {r['model_id']:<38} {p0:>16} {p2:>9}  {'có' if r['supports_images'] else 'không':<7} "
              f"{r['params'].get('resolution', '')} {r.get('note', '')}")
    print(f"\n→ Lưu ở {LAB / 'models.json'}")


def _pick_models(a, rows):
    if a.models:
        want = [x.strip() for x in a.models.split(",")]
        sel = [r for r in rows if r["model_id"] in want]
        missing = set(want) - {r["model_id"] for r in sel}
        if missing:
            sys.exit(f"Không có model: {missing}")
        return sel
    # mặc định: 4 model rẻ nhất có hỗ trợ ảnh tham chiếu (cần để vẽ nhiều biểu cảm cùng 1 nhân vật)
    ok = [r for r in rows if r.get("supports_images") and r.get("price0")]
    return ok[:4]


def cmd_style(a):
    rows = load_models()
    sel = _pick_models(a, rows)
    out = LAB / "style"
    total = 0
    jobs = []
    for r in sel:
        mid = r["model_id"]
        mdl = {"aspect_ratios": r["aspect_ratios"], "resolutions": r["resolutions"]}
        p_char = ai33.model_params(mdl, "3:4" if "3:4" in (r["aspect_ratios"] or []) else "1:1")
        p_bg = ai33.model_params(mdl, "16:9")
        total += (r["price0"] or 0) * 2
        jobs.append((f"{mid} nhân vật", lambda mid=mid, p=p_char: ai33.generate_image(
            f"{CFG['style']}. Full body view of ONE single character standing, facing the viewer, "
            f"on a plain pure white background, no shadow. {TEST_CHARACTER}. {NO_TEXT}",
            out / f"{mid}__char.png", mid, p)))
        jobs.append((f"{mid} nền", lambda mid=mid, p=p_bg: ai33.generate_image(
            f"{CFG['style']}. Wide empty background scene with no people: {TEST_BACKGROUND}. {NO_TEXT}",
            out / f"{mid}__bg.png", mid, p)))
    confirm(f"Thử {len(sel)} model: {[r['model_id'] for r in sel]}\n"
            f"Tổng {len(jobs)} ảnh, ước tính {round(total)} credit ≈ {vnd(total)}", a.yes)
    run_parallel(jobs)
    items = []
    for r in sel:
        mid = r["model_id"]
        lab = f"{mid}  ({vnd(r['price0'])}/ảnh)"
        items += [(out / f"{mid}__char.png", lab), (out / f"{mid}__bg.png", "")]
    g = grid(items, out / "_so_sanh.png", cols=2, title="So sánh nét vẽ — trái: nhân vật, phải: nền")
    print(f"\n→ Xem ảnh so sánh: {g}")


def cmd_narrator(a):
    rows = {r["model_id"]: r for r in load_models()}
    if a.model not in rows:
        sys.exit("Model không có trong bảng giá (lab.py models)")
    r = rows[a.model]
    mdl = {"aspect_ratios": r["aspect_ratios"], "resolutions": r["resolutions"]}
    params = ai33.model_params(mdl, "3:4" if "3:4" in (r["aspect_ratios"] or []) else "1:1")
    out = LAB / "narrator"
    jobs = [(k, lambda k=k, desc=desc: ai33.generate_image(
        f"{CFG['style']}. Mascot character design, full body, ONE single character standing facing the viewer, "
        f"on a plain pure white background, no shadow. {desc}. {NO_TEXT}",
        out / f"{k}.png", a.model, params)) for k, desc in NARRATORS.items()]
    confirm(f"Vẽ {len(jobs)} phương án người kể bằng {a.model}, ≈ {vnd((r['price0'] or 0) * len(jobs))}", a.yes)
    run_parallel(jobs)
    g = grid([(out / f"{k}.png", f"Phương án {k}") for k in NARRATORS], out / "_so_sanh.png", cols=4, cell_w=420,
             title="Nhân vật người kể — chọn 1")
    print(f"\n→ Xem: {g}")


def cmd_voices(a):
    filters = {"locale": a.locale} if a.provider == "vbee" and a.locale else {}
    if a.provider != "vbee":
        filters["language"] = "Vietnamese"
    if a.gender:
        filters["gender"] = a.gender
    allv, page = [], 1
    while page <= 5:
        d = ai33.voices(a.provider, page=page, search=a.search, **filters)
        data = d.get("data") or []
        allv += data
        pg = d.get("pagination") or {}
        if not data or page >= (pg.get("total_pages") or pg.get("totalPages") or 1):
            break
        page += 1
    out = LAB / "voices"
    out.mkdir(parents=True, exist_ok=True)
    (out / "list.json").write_text(json.dumps(allv, ensure_ascii=False, indent=2), encoding="utf-8")
    for i, v in enumerate(allv, 1):
        info = " · ".join(str(v[k]) for k in ("gender", "age", "locale", "accent", "category", "description")
                          if v.get(k))
        print(f"{i:>3}. {v.get('voice_id', ''):<45} {v.get('name', '')}  {info}")
    print(f"\n{len(allv)} giọng → {out / 'list.json'}")
    print("Bước tiếp: lab.py voicetest --pick 1,4,7,9  (chọn 6-8 số theo danh sách trên)")


def cmd_voicetest(a):
    lst = LAB / "voices" / "list.json"
    if not lst.exists():
        sys.exit("Chạy trước: lab.py voices")
    allv = json.loads(lst.read_text(encoding="utf-8"))
    idx = [int(x) for x in a.pick.split(",")]
    sel = [allv[i - 1] for i in idx]
    out = LAB / "voices" / "mau"
    confirm(f"Đọc thử {len(sel)} giọng × {len(SAMPLE_TEXT)} ký tự", a.yes)
    jobs = []
    for i, v in zip(idx, sel):
        name = f"{i:02d}_{(v.get('name') or v['voice_id']).replace(' ', '_').replace('/', '_')}"
        jobs.append((name, lambda v=v, name=name: ai33.tts(SAMPLE_TEXT, v["voice_id"], out / f"{name}.mp3")))
    run_parallel(jobs)
    print(f"\n→ Nghe trong thư mục: {out}")
    print("Chọn xong: báo Claude số thứ tự giọng → ghi vào config.json")


def cmd_compose(a):
    """1.5 Thử ghép lớp bằng Remotion — dùng lại ảnh + giọng đã có, không tốn credit."""
    import re
    import shutil
    import subprocess

    from dungphim.align import align_words
    from dungphim.cutout import cutout

    studio = ROOT / "studio"
    pub = studio / "public" / "demo"
    pub.mkdir(parents=True, exist_ok=True)
    out = LAB / "compose"
    out.mkdir(parents=True, exist_ok=True)

    voice = Path(a.voice) if a.voice else sorted((LAB / "voices" / "mau").glob("08_*.mp3"))[0]
    print(f"• Giọng: {voice.name}")
    shutil.copy(voice, pub / "voice.mp3")
    shutil.copy(LAB / "style" / "gpt-image-2__bg.png", pub / "bg.png")

    print("• Tách nền nhân vật (rembg isnet-anime; lần đầu tải model ~170MB)")
    cutout(LAB / "style" / "gemini-3.1-flash-lite-image__char.png", pub / "girl.png")
    cutout(ROOT / "library" / "nhan_vat" / "mc" / "goc.png", pub / "mc.png")
    shutil.copy(pub / "mc.png", ROOT / "library" / "nhan_vat" / "mc" / "binh_thuong.png")

    print("• Căn thời gian từng từ (stable-ts; lần đầu tải model ~140MB)")
    words = align_words(pub / "voice.mp3", SAMPLE_TEXT)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "default=nw=1:nk=1", str(pub / "voice.mp3")], capture_output=True, text=True).stdout)

    # chia 4 cảnh theo câu; mỗi cảnh = công thức dàn cảnh như agent Đạo diễn sẽ tạo
    sents = [s for s in re.split(r"(?<=[.!?])\s+", SAMPLE_TEXT) if s]
    plan = [
        (sents[0], [{"src": "demo/girl.png", "pos": "giua", "motion": "nhun"}], ""),
        (sents[1], [{"src": "demo/girl.png", "pos": "trai", "motion": "dung"},
                    {"src": "demo/mc.png", "pos": "phai", "motion": "truot_vao"}], ""),
        (" ".join(sents[2:4]), [{"src": "demo/girl.png", "pos": "giua", "motion": "lat"}], ""),
        (" ".join(sents[4:]), [{"src": "demo/girl.png", "pos": "giua", "motion": "rung"}], "Đắt giá nhất"),
    ]
    scenes, wi = [], 0
    for text, chars, emph in plan:
        n = len(text.split())
        ws = words[wi:wi + n]
        start = ws[0]["s"] if ws else (scenes[-1]["end"] if scenes else 0)
        scenes.append({"start": start, "end": 0, "bg": "demo/bg.png", "chars": chars, "emphasis": emph})
        wi += n
    scenes[0]["start"] = 0
    for i in range(len(scenes) - 1):
        scenes[i]["end"] = scenes[i + 1]["start"]
    scenes[-1]["end"] = round(dur + 0.4, 3)

    props = {"fps": 30, "audio": "demo/voice.mp3", "title": "Bị bán sang Trung Quốc làm vợ",
             "scenes": scenes, "words": words}
    pfile = out / "props.json"
    pfile.write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")

    for comp, name in (("Long", "demo_16x9.mp4"), ("Short", "demo_9x16.mp4")):
        print(f"• Remotion render {comp}")
        r = subprocess.run(["npx", "remotion", "render", "src/index.ts", comp, str(out / name),
                            f"--props={pfile}", "--log=error"], cwd=studio, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"Lỗi render {comp}:\n{r.stdout[-1500:]}\n{r.stderr[-2500:]}")
        print(f"  ✓ {out / name}")
    print("\nXem trước & chỉnh trực tiếp: cd studio && npx remotion studio")


def cmd_cost(a):
    c, v = ai33.ledger_total(ai33.LEDGER)
    print(f"Lab đã tiêu: {round(c)} credit ≈ {round(v):,}đ".replace(",", "."))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("models")
    p = sub.add_parser("style"); p.add_argument("--models"); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("narrator"); p.add_argument("--model", required=True); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("voices")
    p.add_argument("--provider", default="vbee", choices=["vbee", "elevenlabs", "minimax", "edge", "fishaudio"])
    p.add_argument("--locale", choices=["northern", "central", "southern"])
    p.add_argument("--gender", choices=["Male", "Female"])
    p.add_argument("--search")
    p = sub.add_parser("voicetest"); p.add_argument("--pick", required=True); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("compose"); p.add_argument("--voice", help="file mp3 giọng (mặc định mẫu 08)")
    sub.add_parser("cost")
    a = ap.parse_args()
    globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()

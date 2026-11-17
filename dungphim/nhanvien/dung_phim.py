"""🤖 Dựng phim — storyboard + giọng + timing → props → Remotion render (16:9 hoặc 9:16)."""
import json
import shutil
import subprocess

from .. import library
from ..config import ROOT, load_config

NAME = "dung_phim"
STUDIO = ROOT / "studio"


def _ff(args):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])


def _scene_visual(p, s, chars, pub, used):
    """Trả về (bg, chars[]) cho 1 cảnh bản dài; copy ảnh cần dùng vào thư mục public."""
    sp = p.path("dac_biet", f"{s['id']:03d}.png")
    if s.get("dac_biet_en") and sp.exists():
        dst = f"img/dac_biet_{s['id']:03d}.png"
        used[dst] = sp
        return dst, []
    bg = f"img/nen_{s['nen']}.png"
    used[bg] = library.nen_path(s["nen"])
    out = []
    for c in s["nhan_vat"]:
        lib_id = chars[c["id"]]["lib_id"]
        f = library.bieu_cam_path(lib_id, c["bieu_cam"])
        if not f.exists():
            f = library.bieu_cam_path(lib_id, "binh_thuong")
        if not f.exists():
            continue
        dst = f"img/{lib_id}__{f.stem}.png"
        used[dst] = f
        out.append({"src": dst, "pos": c["vi_tri"], "motion": c["chuyen_dong"]})
    return bg, out


def render(p, short=False):
    cfg = load_config()
    board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
    chars = {c["id"]: c for c in board["nhan_vat"]}
    long_by_id = {s["id"]: s for s in board["canh"]}
    if short:
        sj = json.loads(p.path("short.json").read_text(encoding="utf-8"))
        items, vdir, tfile = sj["canh"], p.path("short", "voice"), p.path("short", "timing.json")
        pub, comp, out, title = p.path("_render_short"), "Short", p.path("final_9x16.mp4"), sj.get("tieu_de_tren", "")
    else:
        items, vdir, tfile = board["canh"], p.path("voice"), p.path("timing.json")
        pub, comp, out, title = p.path("_render_long"), "Long", p.path("final_16x9.mp4"), ""
    timing = json.loads(tfile.read_text(encoding="utf-8"))
    gap = cfg["gap_seconds"]
    (pub / "img").mkdir(parents=True, exist_ok=True)
    (pub / "fonts").mkdir(exist_ok=True)
    shutil.copy(ROOT / "fonts" / "Anton-Regular.ttf", pub / "fonts" / "Anton-Regular.ttf")

    # 1. nối giọng thành 1 track (mỗi cảnh + khoảng nghỉ)
    print("  • Nối giọng đọc")
    wavs = pub / "_wav"
    wavs.mkdir(exist_ok=True)
    lst = []
    for s in items:
        k = str(s["id"])
        d = timing[k]["dur"] + gap
        w = wavs / f"{s['id']:03d}.wav"
        _ff(["-i", str(vdir / f"{s['id']:03d}.mp3"), "-af", f"apad=whole_dur={d:.3f}", "-t", f"{d:.3f}",
             "-ar", "44100", "-ac", "1", str(w)])
        lst.append(f"file '{w.as_posix()}'")
    (wavs / "list.txt").write_text("\n".join(lst), encoding="utf-8")
    _ff(["-f", "concat", "-safe", "0", "-i", str(wavs / "list.txt"), "-c", "copy", str(pub / "voice.wav")])

    # 2. props
    used, scenes, words, t = {}, [], [], 0.0
    for s in items:
        k = str(s["id"])
        d = timing[k]["dur"] + gap
        src = long_by_id[s["dung_canh"]] if short else s
        bg, cs = _scene_visual(p, src, chars, pub, used)
        scenes.append({"start": round(t, 3), "end": round(t + d, 3), "bg": bg, "chars": cs,
                       "emphasis": s.get("chu_nhan", "")})
        words += [{"w": w["w"], "s": round(w["s"] + t, 3), "e": round(w["e"] + t, 3)} for w in timing[k]["words"]]
        t += d
    for dst, srcf in used.items():
        if srcf.exists() and not (pub / dst).exists():
            shutil.copy(srcf, pub / dst)
    props = {"fps": cfg["fps"], "audio": "voice.wav", "title": title, "scenes": scenes, "words": words}
    pf = pub / "props.json"
    pf.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    # 3. render
    print(f"  • Remotion render {comp} ({t / 60:.1f} phút) — có thể mất vài chục phút")
    tmp = out.with_name(out.stem + "_voice.mp4")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", comp, str(tmp), f"--props={pf}",
                        f"--public-dir={pub}", "--log=error"], cwd=STUDIO, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"Remotion lỗi:\n{r.stderr[-2500:]}")

    # 4. nhạc nền (nếu có) + chuẩn hoá âm lượng
    nhac = library.LIB / "nhac"
    cands = sorted(p.dir.glob("music.*")) + (sorted(nhac.glob("*.mp3")) if nhac.exists() else [])
    music = cands[0] if cands else None
    if music:
        _ff(["-i", str(tmp), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
             f"[1:a]volume={cfg['music_volume']}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    else:
        _ff(["-i", str(tmp), "-af", "loudnorm=I=-14:TP=-1.5", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", str(out)])
    tmp.unlink(missing_ok=True)
    p.handoff(NAME + ("_shorts" if short else "_dai"), "marketing" if short else "bien_tap_shorts",
              f"Xuất {out.name} ({t / 60:.1f} phút, {len(scenes)} cảnh)", [out.name],
              "" if music else "Chưa có nhạc nền (đặt music.mp3 vào thư mục video hoặc library/nhac/)")
    return out

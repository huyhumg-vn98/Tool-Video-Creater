"""🤖 Lồng tiếng — giọng từng cảnh (ai33) + mốc thời gian từng từ (stable-ts) + tự kiểm tra tốc độ."""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from .. import ai33
from ..align import align_words
from ..config import load_config

NAME = "long_tieng"


def _dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "default=nw=1:nk=1", str(f)], capture_output=True, text=True).stdout)


def voice(p, short=False):
    cfg = load_config()
    spent0 = p.spent_of("giong")
    if short:
        items = json.loads(p.path("short.json").read_text(encoding="utf-8"))["canh"]
        vdir, tfile, speed = p.path("short", "voice"), p.path("short", "timing.json"), cfg["short_voice_speed"]
    else:
        items = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))["canh"]
        vdir, tfile, speed = p.path("voice"), p.path("timing.json"), cfg["voice_speed"]
    vdir.mkdir(parents=True, exist_ok=True)
    timing = json.loads(tfile.read_text(encoding="utf-8")) if tfile.exists() else {}

    todo = [s for s in items if not (vdir / f"{s['id']:03d}.mp3").exists()]
    if todo:
        print(f"  • Đọc {len(todo)} cảnh ({cfg['voice_id']})")
        errs = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(ai33.tts, s["loi_ke"], cfg["voice_id"], vdir / f"{s['id']:03d}.mp3", speed,
                              None, f"giọng cảnh {s['id']}"): s["id"] for s in todo}
            for i, f in enumerate(as_completed(futs), 1):
                try:
                    f.result()
                except Exception as e:  # noqa: BLE001
                    errs.append(futs[f])
                    print(f"    ✗ cảnh {futs[f]}: {e}")
                if i % 20 == 0 or i == len(todo):
                    print(f"    {i}/{len(todo)}")
        if errs:
            raise RuntimeError(f"Lỗi đọc cảnh {errs} — chạy lại để đọc tiếp")

    print("  • Căn thời gian từng từ + kiểm tra tốc độ")
    warn = []
    for s in items:
        k = str(s["id"])
        mp3 = vdir / f"{s['id']:03d}.mp3"
        if k in timing and timing[k].get("mtime") == mp3.stat().st_mtime:
            continue
        d = _dur(mp3)
        cps = len(s["loi_ke"]) / max(d, 0.1)
        if not 9 <= cps <= 26:
            warn.append(f"{s['id']}({cps:.0f}k/s)")
        timing[k] = {"dur": round(d, 3), "words": align_words(mp3, s["loi_ke"]), "mtime": mp3.stat().st_mtime}
    tfile.write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")
    total = sum(timing[str(s["id"])]["dur"] for s in items)
    p.handoff(NAME + ("_shorts" if short else ""), "dung_phim_shorts" if short else "dung_phim_dai",
              f"{len(items)} file giọng, tổng {total / 60:.1f} phút", [str(vdir.relative_to(p.dir)), tfile.name],
              ("Tốc độ bất thường: " + ", ".join(warn)) if warn else "", p.spent_of("giong") - spent0)

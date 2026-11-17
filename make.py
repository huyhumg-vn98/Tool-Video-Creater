#!/usr/bin/env python3
"""🤖 TRƯỞNG PHÒNG SẢN XUẤT — điều phối các nhân viên theo dây chuyền.

  .venv/bin/python make.py moi "Đề tài + góc kể" [--phut 12] [--kich-ban file.txt]
  .venv/bin/python make.py chay V001            # chạy tiếp đến cổng duyệt / xong
  .venv/bin/python make.py duyet V001           # Giám đốc duyệt cổng đang chờ
  .venv/bin/python make.py ve-lai V001 12 37    # vẽ lại tài sản của cảnh 12, 37 (cổng ảnh lưới)
  .venv/bin/python make.py trang-thai V001
  .venv/bin/python make.py lam-lai V001 dao_dien   # làm lại từ 1 bước (xoá kết quả bước đó trở đi)
"""
import argparse
import atexit
import json
import os
import shutil
import sys
import threading
import time

from dungphim.config import PROJECTS, load_config
from dungphim.nhanvien import bien_kich, bien_tap_shorts, dao_dien, dung_phim, hoa_si, long_tieng, marketing, thu_vien
from dungphim.state import Project

# (mã bước, tên hiển thị, hàm)  — "@..." là cổng duyệt của Giám đốc
PIPELINE = [
    ("bien_kich", "Biên kịch", bien_kich.run),
    ("@claude_kich_ban", "Claude duyệt kịch bản", None),
    ("dao_dien", "Đạo diễn phân cảnh", dao_dien.run),
    ("thu_vien", "Quản lý thư viện", thu_vien.run),
    ("@ngan_sach", "Kiểm tra ngân sách", None),
    ("hoa_si", "Họa sĩ", hoa_si.run),
    ("@claude_anh", "Claude duyệt ảnh", None),
    ("@duyet_anh", "Giám đốc duyệt ảnh lưới", None),
    ("long_tieng", "Lồng tiếng", lambda p: long_tieng.voice(p)),
    ("dung_phim_dai", "Dựng phim 16:9", lambda p: dung_phim.render(p)),
    ("bien_tap_shorts", "Biên tập Shorts", bien_tap_shorts.run),
    ("long_tieng_shorts", "Lồng tiếng Shorts", lambda p: long_tieng.voice(p, short=True)),
    ("dung_phim_shorts", "Dựng phim 9:16", lambda p: dung_phim.render(p, short=True)),
    ("marketing", "Marketing", marketing.run),
    ("@claude_video", "Claude duyệt video", None),
    ("@duyet_cuoi", "Giám đốc duyệt bản cuối", None),
]
OUTPUTS = {  # file của từng bước — dùng cho lam-lai
    "bien_kich": ["story.md"], "dao_dien": ["storyboard.json"], "thu_vien": ["can_ve.json"],
    "hoa_si": ["luoi_canh.png"], "long_tieng": ["voice", "timing.json"],
    "dung_phim_dai": ["final_16x9.mp4", "_render_long"], "bien_tap_shorts": ["short.json"],
    "long_tieng_shorts": ["short"], "dung_phim_shorts": ["final_9x16.mp4", "_render_short"],
    "marketing": ["marketing.md", "thumbnail_A.png", "thumbnail_B.png"],
}
GATE_MSG = {
    "@claude_kich_ban": "Chờ Claude duyệt & sửa kịch bản (story.md) — nhắn Claude Code: \"QC V00x\"",
    "@claude_anh": "Chờ Claude xem từng ảnh, vẽ lại ảnh lỗi — nhắn Claude Code: \"QC V00x\"",
    "@claude_video": "Chờ Claude xem video, sửa cảnh chưa ổn — nhắn Claude Code: \"QC V00x\"",
    "@ngan_sach": "Xem báo giá vẽ ảnh (can_ve.json) rồi `duyet` để Họa sĩ bắt đầu vẽ",
    "@duyet_anh": "Xem luoi_canh.png → `duyet` nếu ổn, hoặc `ve-lai <số cảnh…>`",
    "@duyet_cuoi": "Xem final_16x9.mp4, final_9x16.mp4, marketing.md, thumbnail_A/B.png → `duyet` để hoàn tất",
}


class Live:
    """projects/<id>/live.json — bảng điều khiển đọc file này để biết ai đang làm gì (không đụng state.json)."""

    def __init__(self, p):
        self.f = p.path("live.json")
        self.d = {}
        try:
            self.d = json.loads(self.f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass

    def set(self, **kw):
        try:  # đọc lại để không đè thông tin do chỗ khác vừa ghi (vd lỗi)
            self.d = json.loads(self.f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
        self.d.update(kw)
        tmp = self.f.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.f)


class Tee:
    """Nhân bản stdout/stderr ra projects/<id>/log.txt + cập nhật dòng việc hiện tại trong live.json."""

    def __init__(self, stream, logf, live):
        self.s, self.logf, self.live, self.buf = stream, logf, live, ""

    def write(self, x):
        self.s.write(x)
        self.buf += x.replace("\r", "\n")
        while "\n" in self.buf:
            ln, self.buf = self.buf.split("\n", 1)
            if not ln.strip() or "%|" in ln or "Adjustment" in ln:
                continue
            self.logf.write(f"{time.strftime('%H:%M:%S')} {ln}\n")
            self.logf.flush()
            if ln.strip()[:1] in "•[✗▶⚠💰" or ln.strip()[:2].isdigit():
                self.live.set(line=ln.strip())
        return len(x)

    def flush(self):
        self.s.flush()

    def isatty(self):
        return False


def attach_log(p):
    live = Live(p)
    live.set(pid=os.getpid(), running=True, error=None, line="")
    logf = open(p.path("log.txt"), "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, logf, live)
    sys.stderr = Tee(sys.__stderr__, logf, live)
    return live


def vnd(x):
    return f"{x:,.0f}đ".replace(",", ".")


def line(p, step, extra=""):
    print(f"{p.id} | {step} | tổng {vnd(p.spent_vnd)}/{vnd(p.data['budget_vnd'])} {extra}")


def _voice_alongside(p: Project):
    """Lồng tiếng chỉ cần kịch bản + storyboard → chạy song song với Họa sĩ (đỡ chờ ai33).
    Lỗi giọng không làm hỏng bước vẽ: bước long_tieng chưa ✓ thì dây chuyền tự chạy lại sau cổng duyệt ảnh."""
    if "long_tieng" in p.data["done"] or not p.path("storyboard.json").exists():
        return None

    def work():
        lv = Live(p)
        lv.set(song_song=["long_tieng"])  # bảng điều khiển: Lồng tiếng cũng "Đang làm"
        try:
            print("  🎙 Lồng tiếng chạy song song với Họa sĩ")
            long_tieng.voice(p)
            h = p.last_handoff()
            print(f"  🎙 Lồng tiếng ✓ — {h['da_lam'] if h else ''}")
        except Exception as e:  # noqa: BLE001
            print(f"  🎙 Lồng tiếng lỗi ({type(e).__name__}: {e}) — sẽ làm lại sau cổng duyệt ảnh")
        finally:
            lv.set(song_song=[])

    th = threading.Thread(target=work, daemon=True)
    th.start()
    return th


def run(p: Project):
    for code, label, fn in PIPELINE:
        if code in p.data["done"]:
            continue
        if code.startswith("@claude") and not p.data.get("qc"):
            continue  # video tạo trước khi có QC của Claude (V001)
        p.data["stage"] = code
        p.save()
        if code.startswith("@"):
            if code == "@ngan_sach":
                # Luôn dừng báo giá trước khi vẽ (quy tắc: mọi lệnh tốn tiền phải hỏi trước)
                est = json.loads(p.path("can_ve.json").read_text(encoding="utf-8"))["uoc_tinh_vnd"]
                print(f"   💰 Ước tính vẽ ảnh: {vnd(est)} (đã chi {vnd(p.spent_vnd)}, ngân sách {vnd(p.data['budget_vnd'])})")
            p.data["gate_spent0"] = p.spent_vnd
            p.wait(GATE_MSG[code])
            line(p, f"⏸ CHỜ GIÁM ĐỐC: {label}")
            print(f"   → {GATE_MSG[code]}")
            return
        print(f"\n▶ {label}")
        t0 = time.time()
        live = Live(p)
        live.set(step=code, label=label, started=t0, spent0=p.spent_vnd, line="")
        bg = _voice_alongside(p) if code == "hoa_si" else None
        try:
            fn(p)
        except Exception as e:
            live.set(error=f"{label}: {type(e).__name__}: {e}"[:600], running=False)
            raise
        finally:
            if bg:
                bg.join()  # chờ Lồng tiếng xong trước khi dừng ở cổng duyệt ảnh
        h = next((x for x in reversed(p.data["handoffs"]) if x["tu"] == code), None)
        line(p, f"{label} ✓ {time.time() - t0:.0f}s", f"→ {h['cho']}" if h else "")
        if h:
            print(f"   📝 {h['da_lam']}" + (f"  ⚠ {h['luu_y']}" if h.get("luu_y") else ""))
    p.data["stage"] = "xong"
    p.wait(None)
    line(p, "✅ XONG")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("moi"); a.add_argument("topic"); a.add_argument("--phut", type=float); a.add_argument("--kich-ban")
    for c in ("chay", "duyet", "trang-thai"):
        sub.add_parser(c).add_argument("id")
    a = sub.add_parser("qc-xong"); a.add_argument("id"); a.add_argument("tom_tat"); a.add_argument("--luu-y", default="")
    a = sub.add_parser("ve-lai"); a.add_argument("id"); a.add_argument("canh", nargs="+", type=int)
    a = sub.add_parser("lam-lai"); a.add_argument("id"); a.add_argument("buoc", choices=[c for c, _, f in PIPELINE if f])
    args = ap.parse_args()
    cfg = load_config()

    if args.cmd == "moi":
        p = Project.create(args.topic, args.phut or cfg["target_minutes"], cfg["budget_vnd_per_video"])
        if args.kich_ban:
            txt = open(args.kich_ban, encoding="utf-8").read()
            p.path("story.md").write_text(txt if txt.startswith("#") else f"# {args.topic}\n\n{txt}", encoding="utf-8")
        print(f"✓ Tạo {p.id}: {args.topic}\n  Chạy: .venv/bin/python make.py chay {p.id}")
        return

    if not (PROJECTS / args.id / "state.json").exists():
        sys.exit(f"Không có video {args.id}")
    p = Project(args.id)
    if args.cmd != "trang-thai":
        live = attach_log(p)
        print(f"$ make.py {args.cmd} {p.id} " + " ".join(sys.argv[3:]))
        atexit.register(lambda: live.set(running=False, step=None, line=""))

    if args.cmd == "trang-thai":
        print(f"{p.id} — {p.data['topic']}\nBước: {p.data['stage']}  |  Chi phí: {vnd(p.spent_vnd)}/{vnd(p.data['budget_vnd'])}")
        if p.data["waiting_for"]:
            print(f"⏸ Chờ: {p.data['waiting_for']}")
        for h in p.data["handoffs"][-12:]:
            print(f"  {h['luc']} {h['tu']} → {h['cho']}: {h['da_lam']}" + (f" ⚠ {h['luu_y']}" if h['luu_y'] else ""))
        return

    if args.cmd == "duyet":
        st = p.data["stage"]
        if not (st or "").startswith("@"):
            sys.exit("Không có cổng nào đang chờ duyệt.")
        p.data["done"].append(st)
        p.wait(None)
        print(f"✓ Đã duyệt {st}")
        run(p)
        return

    if args.cmd == "qc-xong":  # Claude duyệt xong 1 cổng QC → ghi phiếu (giữ gì/sửa gì/chi phí) rồi chạy tiếp
        st = p.data["stage"] or ""
        if not st.startswith("@claude"):
            sys.exit("Không có cổng QC nào đang chờ.")
        cost = p.spent_vnd - p.data.get("gate_spent0", p.spent_vnd)
        qc_total = sum(h["chi_phi_vnd"] for h in p.data["handoffs"] if h["tu"].startswith("@claude")) + cost
        nxt = [c for c, _, _ in PIPELINE][[c for c, _, _ in PIPELINE].index(st) + 1]
        p.handoff(st, nxt, args.tom_tat, [], args.luu_y, cost)
        p.wait(None)
        print(f"✓ QC {st}: sửa tốn {vnd(cost)} · tổng QC video {vnd(qc_total)}/{vnd(p.data.get('qc_cap_vnd', 3000))}")
        run(p)
        return

    if args.cmd == "ve-lai":
        board = json.loads(p.path("storyboard.json").read_text(encoding="utf-8"))
        chars = {c["id"]: c for c in board["nhan_vat"]}
        need = {"nen": {}, "nhan_vat_goc": [], "bieu_cam": {}, "dac_biet": []}
        for s in board["canh"]:
            if s["id"] not in args.canh:
                continue
            if s.get("dac_biet_en"):
                need["dac_biet"].append(s["id"])
                continue
            need["nen"][s["nen"]] = s.get("nen_mo_ta_en", s["nen"])
            for c in s["nhan_vat"]:
                if c["bieu_cam"] != "binh_thuong":
                    need["bieu_cam"][f"{chars[c['id']]['lib_id']}/{c['bieu_cam']}"] = c.get("bieu_cam_en", c["bieu_cam"])
        n = len(need["nen"]) + len(need["bieu_cam"]) + len(need["dac_biet"])
        est = (len(need["nen"]) * thu_vien.price_vnd(cfg["image_model_background"], False)
               + (len(need["bieu_cam"]) + len(need["dac_biet"])) * thu_vien.price_vnd(cfg["image_model_character"], True))
        print(f"Vẽ lại {n} ảnh (nền/biểu cảm dùng chung sẽ đổi ở MỌI cảnh dùng nó) ≈ {vnd(est)}")
        live.set(step="hoa_si", label=f"Vẽ lại cảnh {args.canh}", started=time.time(), spent0=p.spent_vnd)
        hoa_si.draw(p, need)
        hoa_si.grid(p)
        print(f"✓ Xem lại {p.path('luoi_canh.png')}")
        return

    if args.cmd == "lam-lai":
        codes = [c for c, _, _ in PIPELINE]
        i = codes.index(args.buoc)
        for c in codes[i:]:
            if c in p.data["done"]:
                p.data["done"].remove(c)
            for f in OUTPUTS.get(c, []):
                t = p.path(f)
                if t.is_dir():
                    shutil.rmtree(t)
                elif t.exists():
                    t.unlink()
        p.data["stage"] = args.buoc
        p.wait(None)  # xoá cổng chờ cũ (vd @duyet_cuoi) — nếu không, `chay` tưởng vẫn đang chờ duyệt
        p.save()
        print(f"✓ Đặt lại từ bước {args.buoc}. Chạy: make.py chay {p.id}")
        return

    if args.cmd == "chay":
        if (p.data["stage"] or "").startswith("@"):
            sys.exit(f"⏸ Đang chờ Giám đốc: {p.data['waiting_for']}")
        run(p)


if __name__ == "__main__":
    main()

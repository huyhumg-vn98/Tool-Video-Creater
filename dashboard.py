#!/usr/bin/env python3
"""🖥 Bảng điều khiển studio — chạy: .venv/bin/python dashboard.py  → mở http://localhost:8000

Chỉ đọc state.json / live.json / log.txt / chi_phi.csv của từng video và gọi make.py khi bấm nút.
Không tự tiêu tiền: mọi bước tốn tiền vẫn dừng ở cổng duyệt của make.py.
"""
import csv
import json
import mimetypes
import os
import re
import signal
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
PY = str(ROOT / ".venv" / "bin" / "python")
sys.path.insert(0, str(ROOT))
from make import GATE_MSG, OUTPUTS, PIPELINE  # noqa: E402

ROLES = {  # mô tả ngắn cho thẻ nhân viên
    "bien_kich": ("✍️", "Viết kịch bản ngôi thứ nhất", "DeepSeek"),
    "dao_dien": ("🎬", "Chia cảnh, chọn nền/nhân vật/biểu cảm", "DeepSeek"),
    "thu_vien": ("📚", "Kiểm kho ảnh, lập danh sách cần vẽ + báo giá", "code"),
    "hoa_si": ("🎨", "Vẽ nhân vật, biểu cảm, nền, cảnh đặc biệt", "ai33 + rembg"),
    "long_tieng": ("🎙", "Đọc giọng từng cảnh + căn từng từ", "ai33 + stable-ts"),
    "dung_phim_dai": ("🎞", "Dựng bản dài 16:9", "Remotion"),
    "bien_tap_shorts": ("✂️", "Rút gọn thành bản Shorts", "DeepSeek"),
    "long_tieng_shorts": ("🎙", "Đọc giọng bản Shorts", "ai33 + stable-ts"),
    "dung_phim_shorts": ("📱", "Dựng bản 9:16", "Remotion"),
    "marketing": ("📣", "Tiêu đề, mô tả, hashtag, thumbnail", "DeepSeek"),
    "@claude_kich_ban": ("🧐", "Claude đọc, giữ đoạn hay, sửa đoạn yếu (≤2 vòng)", "Claude QC"),
    "@claude_anh": ("🔍", "Claude xem từng ảnh, vẽ lại ảnh lỗi (≤2 vòng)", "Claude QC"),
    "@claude_video": ("🎯", "Claude xem video, sửa cảnh chưa ổn (≤2 vòng)", "Claude QC"),
    "@ngan_sach": ("💰", "Cổng ①: duyệt báo giá vẽ ảnh", "Giám đốc"),
    "@duyet_anh": ("🖼", "Cổng ②: duyệt ảnh lưới", "Giám đốc"),
    "@duyet_cuoi": ("✅", "Cổng ③: duyệt bản cuối", "Giám đốc"),
}
PROFILE = {"dung_phim_dai": "dung_phim", "dung_phim_shorts": "dung_phim", "long_tieng_shorts": "long_tieng"}
FILES = ["story.md", "story_goc.md", "storyboard.json", "can_ve.json", "luoi_canh.png", "final_16x9.mp4",
         "final_9x16.mp4", "marketing.md", "thumbnail_A.png", "thumbnail_B.png", "short.json"]


def jread(f, default=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ledger(d):
    rows = []
    try:
        with open(d / "chi_phi.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({"luc": r["thoi_gian"], "loai": r["loai"], "vnd": float(r["vnd"] or 0), "ghi_chu": r["ghi_chu"]})
    except FileNotFoundError:
        pass
    return rows


def live_of(d):
    lv = jread(d / "live.json", {}) or {}
    lv["running"] = bool(lv.get("running")) and alive(lv.get("pid"))
    return lv


def summary(d):
    st = jread(d / "state.json", {})
    return {"id": st.get("id", d.name), "topic": st.get("topic", ""), "stage": st.get("stage"),
            "budget": st.get("budget_vnd", 0), "spent": round(sum(r["vnd"] for r in ledger(d))),
            "running": live_of(d)["running"], "error": (jread(d / "live.json", {}) or {}).get("error")}


def detail(pid):
    d = PROJECTS / pid
    st = jread(d / "state.json")
    if not st:
        return None
    lv = live_of(d)
    rows = ledger(d)
    by_step = {}
    for h in st.get("handoffs", []):
        by_step[h["tu"]] = h
    steps = []
    for code, label, fn in PIPELINE:
        h = by_step.get(code)
        if lv["running"] and (lv.get("step") == code or code in (lv.get("song_song") or [])):
            status = "dang_lam"  # ưu tiên trước "xong": làm lại 1 bước đã xong vẫn phải hiện Đang làm
        elif code in st["done"]:
            status = "xong"
        elif code.startswith("@claude") and not st.get("qc"):
            status = "bo_qua"
        elif st.get("stage") == code and code.startswith("@") and st.get("waiting_for"):
            status = "cho_duyet"
        elif st.get("stage") == code and lv.get("error"):
            status = "loi"
        else:
            status = "cho"
        icon, role, tool = ROLES.get(code, ("•", "", ""))
        steps.append({"code": code, "label": label, "icon": icon, "role": role, "tool": tool, "gate": code.startswith("@"), "claude": code.startswith("@claude"),
                      "status": status, "handoff": h, "profile": PROFILE.get(code, code) if not code.startswith("@") else None,
                      "outputs": [f for f in OUTPUTS.get(code, []) if (d / f).exists()]})
    log = []
    lf = d / "log.txt"
    if lf.exists():
        with open(lf, encoding="utf-8", errors="replace") as f:
            log = f.readlines()[-300:]
    can_ve = jread(d / "can_ve.json")
    mk = (d / "marketing.md").read_text(encoding="utf-8") if (d / "marketing.md").exists() else ""
    files = {f: int((d / f).stat().st_mtime) for f in FILES if (d / f).exists()}
    by_type = {}
    for r in rows:
        by_type[r["loai"]] = by_type.get(r["loai"], 0) + r["vnd"]
    return {"state": {k: v for k, v in st.items() if k != "handoffs"}, "handoffs": st.get("handoffs", []),
            "live": lv, "now": time.time(), "steps": steps, "log": "".join(log), "files": files,
            "can_ve": can_ve, "marketing": mk, "gate_msg": GATE_MSG.get(st.get("stage") or "", ""),
            "spent": round(sum(r["vnd"] for r in rows)), "by_type": {k: round(v) for k, v in by_type.items()},
            "ledger": rows[-60:][::-1], "qc_spent": round(sum(h["chi_phi_vnd"] for h in st.get("handoffs", []) if h["tu"].startswith("@claude")))}


def spawn(pid, args):
    d = PROJECTS / pid
    if live_of(d)["running"]:
        return False, "Video này đang chạy — chờ xong hoặc bấm Dừng trước."
    subprocess.Popen([PY, "-u", str(ROOT / "make.py"), *args], cwd=ROOT, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(0.6)
    return True, "Đã giao việc: make.py " + " ".join(args)


def stop(pid):
    lv = live_of(PROJECTS / pid)
    if not lv["running"]:
        return False, "Không có tiến trình nào đang chạy."
    try:
        os.killpg(os.getpgid(lv["pid"]), signal.SIGTERM)
    except OSError:
        os.kill(lv["pid"], signal.SIGTERM)
    return True, "Đã dừng. Bấm Chạy tiếp để làm lại bước đang dở."


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _file(self, f: Path, ctype=None):
        if not f.is_file():
            return self._json({"loi": "không có file"}, 404)
        if not ctype:
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if f.suffix in (".md", ".json", ".csv", ".txt"):
                ctype = ("application/json" if f.suffix == ".json" else "text/plain") + "; charset=utf-8"
        size = f.stat().st_size
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = size - int(m.group(2))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._file(ROOT / "dashboard.html", "text/html; charset=utf-8")
        if path == "/api/projects":
            ds = sorted([d for d in PROJECTS.iterdir() if (d / "state.json").exists()], reverse=True) if PROJECTS.exists() else []
            return self._json([summary(d) for d in ds])
        m = re.fullmatch(r"/api/p/(V\d+)", path)
        if m:
            r = detail(m.group(1))
            return self._json(r) if r else self._json({"loi": "không có video"}, 404)
        m = re.fullmatch(r"/f/(V\d+)/(.+)", path)
        if m:
            base = (PROJECTS / m.group(1)).resolve()
            f = (base / m.group(2)).resolve()
            if base not in f.parents:
                return self._json({"loi": "cấm"}, 403)
            return self._file(f)
        m = re.fullmatch(r"/lib/(.+\.(?:png|jpg|webp))", path)
        if m:  # ảnh thư viện (nhân vật, biểu cảm, nền) cho hộp xem chi tiết từng nhân viên
            base = (ROOT / "library").resolve()
            f = (base / m.group(1)).resolve()
            if base not in f.parents:
                return self._json({"loi": "cấm"}, 403)
            return self._file(f)
        m = re.fullmatch(r"/ho-so/([a-z_]+)", path)
        if m:
            return self._file(ROOT / "agents" / f"{m.group(1)}.md")
        return self._json({"loi": "không có"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if path == "/api/new":
            topic = (body.get("topic") or "").strip()
            if not topic:
                return self._json({"ok": False, "msg": "Chưa nhập đề tài"})
            args = [PY, str(ROOT / "make.py"), "moi", topic]
            if body.get("phut"):
                args += ["--phut", str(body["phut"])]
            r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
            m = re.search(r"Tạo (V\d+)", r.stdout)
            return self._json({"ok": bool(m), "id": m and m.group(1), "msg": (r.stdout + r.stderr).strip()})
        m = re.fullmatch(r"/api/p/(V\d+)/(\w[\w-]*)", path)
        if not m:
            return self._json({"ok": False, "msg": "sai đường dẫn"}, 404)
        pid, cmd = m.groups()
        if cmd == "dung":
            ok, msg = stop(pid)
        elif cmd in ("chay", "duyet"):
            ok, msg = spawn(pid, [cmd, pid])
        elif cmd == "ve-lai":
            canh = [str(int(x)) for x in re.findall(r"\d+", str(body.get("canh", "")))]
            ok, msg = spawn(pid, ["ve-lai", pid, *canh]) if canh else (False, "Nhập số cảnh cần vẽ lại")
        elif cmd == "lam-lai":
            buoc = body.get("buoc", "")
            if buoc not in [c for c, _, f in PIPELINE if f]:
                ok, msg = False, "Bước không hợp lệ"
            else:
                r = subprocess.run([PY, str(ROOT / "make.py"), "lam-lai", pid, buoc], cwd=ROOT, capture_output=True, text=True)
                ok, msg = r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        else:
            ok, msg = False, "Lệnh không hỗ trợ"
        return self._json({"ok": ok, "msg": msg})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"🖥  Bảng điều khiển: http://localhost:{port}   (Ctrl+C để tắt)")
    ThreadingHTTPServer((host, port), H).serve_forever()

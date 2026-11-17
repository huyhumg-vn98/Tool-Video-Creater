"""Bảng trạng thái 1 video (state.json) + phiếu bàn giao + ngân sách."""
import datetime as dt
import json
import threading
from pathlib import Path

from . import ai33
from .config import PROJECTS


class Project:
    def __init__(self, pid: str):
        self.id = pid
        self.dir = PROJECTS / pid
        self.file = self.dir / "state.json"
        self.data = json.loads(self.file.read_text(encoding="utf-8"))
        ai33.LEDGER = self.dir / "chi_phi.csv"

    # ---------- tạo mới ----------
    @staticmethod
    def create(topic: str, minutes: float, budget: int) -> "Project":
        PROJECTS.mkdir(exist_ok=True)
        n = len([p for p in PROJECTS.iterdir() if p.is_dir() and p.name.startswith("V")]) + 1
        pid = f"V{n:03d}"
        d = PROJECTS / pid
        d.mkdir()
        (d / "state.json").write_text(json.dumps({
            "id": pid, "topic": topic, "minutes": minutes,
            "created": dt.datetime.now().isoformat(timespec="seconds"),
            "stage": None, "done": [], "waiting_for": None,
            "budget_vnd": budget, "handoffs": [],
            "qc": True, "qc_cap_vnd": 3000,  # Claude duyệt 3 khâu, ≤ 2 vòng/khâu, ≤ 3.000đ sửa/video
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return Project(pid)

    # ---------- đọc / ghi ----------
    _lock = threading.RLock()  # Họa sĩ + Lồng tiếng chạy song song cùng ghi state.json

    def save(self):
        with self._lock:
            self._save()

    def _save(self):
        self.file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def path(self, *p) -> Path:
        return self.dir.joinpath(*p)

    @property
    def spent_vnd(self) -> float:
        return ai33.ledger_total(self.dir / "chi_phi.csv")[1]

    def spent_of(self, kind: str) -> float:
        """Tiền đã chi theo loại (anh/giong/deepseek) — dùng khi nhiều nhân viên chạy song song."""
        import csv
        f = self.dir / "chi_phi.csv"
        if not f.exists():
            return 0.0
        return sum(float(r["credit"] or 0) for r in csv.DictReader(open(f, encoding="utf-8"))
                   if r["loai"] == kind) * ai33.VND_PER_CREDIT

    def last_handoff(self):
        return self.data["handoffs"][-1] if self.data["handoffs"] else None

    def handoff(self, tu: str, cho: str, da_lam: str, file: list, luu_y: str = "", chi_phi_vnd: float = 0):
        with self._lock:
            self._handoff(tu, cho, da_lam, file, luu_y, chi_phi_vnd)

    def _handoff(self, tu, cho, da_lam, file, luu_y, chi_phi_vnd):
        self.data["handoffs"].append({
            "tu": tu, "cho": cho, "da_lam": da_lam, "file": file, "luu_y": luu_y,
            "chi_phi_vnd": round(chi_phi_vnd), "luc": dt.datetime.now().strftime("%H:%M:%S"),
        })
        if tu not in self.data["done"]:
            self.data["done"].append(tu)
        self.save()

    def wait(self, what: str | None):
        self.data["waiting_for"] = what
        self.save()


class dang_lam:
    """Báo bảng điều khiển 'nhân viên X đang làm' khi gọi thẳng 1 nhân viên ngoài make.py (vd Claude QC vẽ lại).
    Dùng: `with dang_lam(p, "hoa_si", "Họa sĩ (QC vẽ lại)"): hoa_si.draw(p, need)`"""

    def __init__(self, p, step: str, label: str):
        self.f, self.p, self.step, self.label = p.path("live.json"), p, step, label

    def _rw(self, **kw):
        import os
        try:
            d = json.loads(self.f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {}
        d.update(kw)
        tmp = self.f.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.f)

    def __enter__(self):
        import os, time
        self._rw(pid=os.getpid(), running=True, error=None, step=self.step, label=self.label,
                 started=time.time(), spent0=self.p.spent_vnd, line=self.label)
        return self

    def __exit__(self, et, ev, tb):
        if ev is not None:
            self._rw(running=False, error=f"{self.label}: {type(ev).__name__}: {ev}"[:600])
        else:
            self._rw(running=False, step=None, line="")
        return False

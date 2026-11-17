import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"

load_dotenv(ROOT / ".env")


def load_config(project_dir: Path | None = None) -> dict:
    """config.json chung, ghi đè bởi projects/<tên>/config.json nếu có."""
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if project_dir and (project_dir / "config.json").exists():
        cfg.update(json.loads((project_dir / "config.json").read_text(encoding="utf-8")))
    return cfg


def env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise SystemExit(f"Thiếu {name} trong file .env (xem .env.example)")
    return val

"""Gọi DeepSeek cho 1 nhân viên: chỉ nạp hồ sơ (mục '## Chỉ dẫn cho AI') + dữ liệu đầu vào. Ghi chi phí."""
import json
import re

from . import ai33
from .config import ROOT, env, load_config

_client = None


def _c():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=env("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com", timeout=600)
    return _client


def instructions(agent: str) -> str:
    md = (ROOT / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    m = re.search(r"## Chỉ dẫn cho AI\s*\n(.*?)(?=\n## |\Z)", md, re.S)
    if not m:
        raise ValueError(f"Hồ sơ {agent}.md thiếu mục '## Chỉ dẫn cho AI'")
    return m.group(1).strip()


def _log(agent, usage):
    cfg = load_config()
    p = cfg["deepseek_usd_per_mtok"]
    usd = (usage.prompt_tokens * p["in"] + usage.completion_tokens * p["out"]) / 1e6
    vnd = usd * cfg["usd_vnd"]
    ai33.log_cost("deepseek", vnd / ai33.VND_PER_CREDIT,
                  f"{agent} in={usage.prompt_tokens} out={usage.completion_tokens}")
    return vnd


def ask(agent: str, user: str, model: str | None = None, max_tokens=8000, temperature=1.0) -> str:
    cfg = load_config()
    r = _c().chat.completions.create(
        model=model or cfg["writer_model"], max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "system", "content": instructions(agent)}, {"role": "user", "content": user}])
    _log(agent, r.usage)
    return r.choices[0].message.content.strip()


def ask_json(agent: str, user: str, shape: str, max_tokens=8000, retries=3) -> dict:
    """shape: mô tả khuôn JSON mong muốn (ngắn gọn). Dùng chế độ JSON của deepseek-chat."""
    cfg = load_config()
    sys = instructions(agent) + "\n\nCHỈ trả về 1 object JSON hợp lệ đúng khuôn:\n" + shape
    last = None
    for _ in range(retries):
        r = _c().chat.completions.create(
            model=cfg["writer_model"], max_tokens=max_tokens, temperature=0.7,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}])
        _log(agent, r.usage)
        raw = r.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last = e
    raise RuntimeError(f"{agent}: DeepSeek trả JSON lỗi: {last}")

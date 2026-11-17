"""Client cho API ai33.pro (OpenSpeaker): đọc giọng + tạo ảnh. Mọi chi phí được ghi sổ."""
import csv
import datetime as dt
import json
import threading
import time
from pathlib import Path

import requests

from .config import env

BASE = "https://api.ai33.pro"
VND_PER_CREDIT = 0.2  # 200.000đ = 1.000.000 credit

LEDGER: Path | None = None  # file csv ghi chi phí; đặt bởi lệnh gọi
_lock = threading.Lock()


class AI33Error(RuntimeError):
    pass


def _headers():
    return {"xi-api-key": env("AI33_API_KEY")}


QUEUE_WAIT_MAX = 1200  # hàng đợi ai33 đầy (20 việc/tài khoản) → chờ tối đa 20 phút rồi mới báo lỗi


def _req(method, path, retries=3, **kw):
    last, i, t_full = None, 0, None
    while i < retries:
        try:
            r = requests.request(method, BASE + path, headers=_headers(), timeout=120, **kw)
            if r.status_code == 429 and "active_task_limit" in r.text:
                t_full = t_full or time.time()
                if time.time() - t_full > QUEUE_WAIT_MAX:
                    raise AI33Error(f"Hàng đợi ai33 đầy quá {QUEUE_WAIT_MAX // 60} phút: {r.text[:200]}")
                time.sleep(15)  # không tính là 1 lần thử
                continue
            if r.status_code >= 500 or r.status_code == 429:
                raise AI33Error(f"{r.status_code}: {r.text[:300]}")
            try:
                data = r.json()
            except ValueError:
                raise AI33Error(f"{path}: phản hồi không phải JSON ({r.status_code}): {r.text[:200]}")
            if r.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
                err = AI33Error(f"{path} lỗi {r.status_code}: {json.dumps(data, ensure_ascii=False)[:500]}")
                err.client_error = True
                raise err
            return data
        except (requests.RequestException, AI33Error) as e:
            last = e
            if getattr(e, "client_error", False) or str(e).startswith("Hàng đợi ai33 đầy"):
                raise  # sai key, thiếu credit, tham số sai... -> không thử lại
            i += 1
            time.sleep(3 * i)
    raise AI33Error(str(last))


def _form(fields: dict):
    # ép multipart/form-data giống `curl -F`
    return [(k, (None, str(v))) for k, v in fields.items() if v is not None]


def log_cost(kind, credits, note=""):
    if LEDGER is None or credits is None:
        return
    with _lock:
        new = not LEDGER.exists()
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["thoi_gian", "loai", "credit", "vnd", "ghi_chu"])
            w.writerow([dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kind, credits,
                        round(float(credits) * VND_PER_CREDIT), note])


def ledger_total(path: Path):
    if not path.exists():
        return 0, 0
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    c = sum(float(r["credit"] or 0) for r in rows)
    return c, c * VND_PER_CREDIT


# ---------- tiện ích ----------
def credits():
    return _req("GET", "/v1/credits")


def voices(provider="vbee", page=1, **filters):
    params = {"provider": provider, "page": page, "page_size": 100,
              **{k: v for k, v in filters.items() if v}}
    return _req("GET", "/v3/voices", params=params)


def image_models():
    return _req("GET", "/v1i/models").get("models", [])


def model_params(model: dict, aspect_ratio: str):
    """Chọn tham số hợp lệ cho model: tỉ lệ khung (nếu hỗ trợ) + độ phân giải thấp nhất."""
    p = {}
    ars = model.get("aspect_ratios") or []
    if ars:
        p["aspect_ratio"] = aspect_ratio if aspect_ratio in ars else ars[0]
    res = model.get("resolutions") or []
    if res:
        p["resolution"] = res[0]
    return p


def image_price(model_id, params: dict, assets=0, count=1):
    d = _req("POST", "/v1i/task/price", json={
        "model_id": model_id, "generations_count": count, "model_parameters": params, "assets": assets})
    return d.get("credits")


# ---------- task ----------
def wait_task(task_id, timeout=900, every=4):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = _req("GET", f"/v1/task/{task_id}")
        st = d.get("status")
        if st == "done":
            return d
        if st == "error":
            raise AI33Error(f"task {task_id} lỗi: {d.get('error_message')}")
        time.sleep(every)
    raise AI33Error(f"task {task_id} quá thời gian chờ")


def download(url, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        try:
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                tmp = path.with_name(path.name + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                tmp.replace(path)
                return path
        except requests.RequestException:
            time.sleep(3 * (i + 1))
    raise AI33Error(f"Không tải được {url}")


# ---------- đọc giọng ----------
def tts(text, voice_id, out_mp3: Path, speed=1.0, srt_path: Path | None = None, note=""):
    d = _req("POST", "/v3/text-to-speech", files=_form({
        "text": text, "voice_id": voice_id, "speed": speed,
        "with_transcript": "true" if srt_path else "false",
    }))
    task = wait_task(d["task_id"], every=2)
    log_cost("giong", task.get("credit_cost"), note or f"{voice_id} {len(text)} ký tự")
    meta = task.get("metadata") or {}
    if not meta.get("audio_url"):
        raise AI33Error(f"TTS không trả audio_url: {meta}")
    download(meta["audio_url"], out_mp3)
    if srt_path and meta.get("srt_url"):
        try:
            download(meta["srt_url"], srt_path)
        except AI33Error:
            pass
    return task


# ---------- tạo ảnh ----------
IMAGE_RETRY_AFTER = 300  # ảnh chờ quá 5 phút (kẹt hàng đợi ai33) → gửi lại 1 lần


def _submit_image(prompt, model_id, params, assets):
    fields = _form({"prompt": prompt[:4000], "model_id": model_id, "generations_count": 1,
                    "model_parameters": json.dumps(params)})
    for p in assets or []:  # đọc bytes (không truyền file handle: lần gửi lại sẽ gửi ảnh rỗng → invalid_assets_upload)
        fields.append(("assets", (Path(p).name, Path(p).read_bytes(), "image/png")))
    return _req("POST", "/v1i/task/generate-image", files=fields, retries=2)["task_id"]


def _poll(task_id):
    d = _req("GET", f"/v1/task/{task_id}")
    st = d.get("status")
    if st == "error":
        raise AI33Error(f"task {task_id} lỗi: {d.get('error_message')}")
    return d if st == "done" else None


def generate_image(prompt, out_png: Path, model_id, params: dict,
                   assets: list[Path] | None = None, note=""):
    t0 = time.time()
    ids, retried, task = [_submit_image(prompt, model_id, params, assets)], False, None

    def retry(why):
        nonlocal retried
        retried = True
        print(f"    ⏱ {out_png.name}: {why} → gửi lại")
        ids.append(_submit_image(prompt, model_id, params, assets))

    while task is None:
        for tid in list(ids):  # lần gửi nào xong trước thì lấy lần đó
            try:
                task = _poll(tid)
            except AI33Error as err:
                ids.remove(tid)
                if not ids:
                    if retried:
                        raise
                    retry(f"lỗi ({err})")
                continue
            if task:
                break
        if task:
            break
        el = time.time() - t0
        if not retried and el > IMAGE_RETRY_AFTER:
            retry(f"chờ quá {IMAGE_RETRY_AFTER // 60} phút")
        if el > IMAGE_RETRY_AFTER + 900:
            raise AI33Error(f"{out_png.name}: quá thời gian chờ ({el / 60:.0f} phút, đã gửi lại)")
        time.sleep(4)
    log_cost("anh", task.get("credit_cost"), note or f"{model_id} {out_png.name}")
    imgs = (task.get("metadata") or {}).get("result_images") or []
    if not imgs:
        raise AI33Error(f"Không có ảnh trả về: {task}")
    tmp = out_png.with_name(out_png.stem + ".download")
    download(imgs[0]["imageUrl"], tmp)
    from PIL import Image
    Image.open(tmp).convert("RGB").save(out_png)
    tmp.unlink(missing_ok=True)
    return task

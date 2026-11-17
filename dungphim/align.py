"""Căn văn bản có sẵn vào giọng đọc → mốc thời gian từng từ (stable-ts, chạy trên máy, miễn phí)."""
import subprocess
from pathlib import Path

_model = None


def _duration(audio: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(audio)], capture_output=True, text=True)
    return float(out.stdout.strip())


def _repair(words, audio_end: float, min_dur=0.06):
    """Từ bị dồn (thời lượng ~0, cùng mốc) → rải đều theo độ dài chữ tới mốc của từ kế tiếp / cuối file."""
    i, n = 0, len(words)
    while i < n:
        if words[i]["e"] - words[i]["s"] >= min_dur:
            i += 1
            continue
        j = i
        while j < n and words[j]["e"] - words[j]["s"] < min_dur:
            j += 1
        start = words[i - 1]["e"] if i > 0 else 0.0
        end = words[j]["s"] if j < n else audio_end
        if end - start < min_dur * (j - i):
            end = start + min_dur * (j - i)
        total = sum(len(w["w"]) for w in words[i:j]) or 1
        t = start
        for w in words[i:j]:
            d = (end - start) * len(w["w"]) / total
            w["s"], w["e"] = round(t, 3), round(t + d, 3)
            t += d
        i = j
    return words


def align_words(audio: Path, text: str, language: str = "vi", model_size: str = "small"):
    """Trả về list {"w": chữ, "s": giây bắt đầu, "e": giây kết thúc}."""
    global _model
    import warnings

    import stable_whisper
    warnings.filterwarnings("ignore")
    if _model is None:
        _model = stable_whisper.load_model(model_size)
    res = _model.align(str(audio), text, language=language, verbose=None)
    words = []
    for seg in res.segments:
        for w in seg.words:
            t = w.word.strip()
            if t:
                words.append({"w": t, "s": round(float(w.start), 3), "e": round(float(w.end), 3)})
    return _repair(words, _duration(audio) - 0.1)

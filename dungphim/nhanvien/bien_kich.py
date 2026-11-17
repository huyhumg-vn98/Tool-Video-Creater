"""🤖 Biên kịch — dàn ý → kịch bản kể chuyện ngôi thứ nhất."""
from ..config import load_config
from ..deepseek import ask, ask_json

NAME = "bien_kich"


def run(p):
    cfg = load_config()
    if p.path("story.md").exists():
        p.handoff(NAME, "dao_dien", "Dùng story.md có sẵn (Giám đốc cung cấp)", ["story.md"])
        return
    spent0 = p.spent_vnd
    minutes = p.data.get("minutes") or cfg["target_minutes"]
    total = int(minutes * cfg["words_per_min"])
    n = max(4, round(minutes / 2))
    each = total // n

    print(f"  • Lập dàn ý: {n} đoạn, ~{total} chữ")
    o = ask_json(NAME, f"Đề tài: {p.data['topic']}\nLập dàn ý câu chuyện ~{minutes} phút đọc, đúng {n} đoạn "
                       "(mở đầu móc câu → phát triển → cao trào → twist → kết).",
                 '{"tieu_de": "...", "nguoi_ke": "tuổi, giới tính, hoàn cảnh của người kể", '
                 '"doan": [{"tom_tat": "2-4 câu"}]}')
    plan = "\n".join(f"{i}. {d['tom_tat']}" for i, d in enumerate(o["doan"], 1))
    parts = []
    for i, d in enumerate(o["doan"], 1):
        print(f"  • Viết đoạn {i}/{len(o['doan'])}")
        prev = "\n\n".join(parts)[-2500:]
        parts.append(ask(NAME,
                         f"Tiêu đề: {o['tieu_de']}\nNgười kể: {o['nguoi_ke']}\nDàn ý:\n{plan}\n\n"
                         + (f"Phần đã viết (đoạn cuối):\n…{prev}\n\n" if prev else "")
                         + f"Viết ĐOẠN {i} ({d['tom_tat']}) khoảng {each} chữ, nối tiếp liền mạch. "
                           "Chỉ trả về lời kể, không ghi số đoạn, không tiêu đề."))
    text = f"# {o['tieu_de']}\n\n" + "\n\n".join(parts) + "\n"
    p.path("story.md").write_text(text, encoding="utf-8")
    p.data["narrator"] = o["nguoi_ke"]
    words = len(text.split())
    p.handoff(NAME, "dao_dien", f"Kịch bản '{o['tieu_de']}', {words} chữ, {len(parts)} đoạn",
              ["story.md"], f"Người kể: {o['nguoi_ke']}", p.spent_vnd - spent0)

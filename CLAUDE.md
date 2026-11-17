# Studio phim kể chuyện AI — bối cảnh cho Claude

**Đọc file này là đủ để làm tiếp. KHÔNG đọc lại lịch sử chat, KHÔNG quét cả project.**
Trả lời người dùng bằng tiếng Việt. Người dùng làm một mình; các agent là "nhân viên".
Luôn thống nhất phương án trước khi code tính năng mới.

## Mục tiêu
Kênh YouTube kể chuyện hoạt hình 2D tự sự ngôi thứ nhất (cùng thể loại kênh "Lạnh Vcl" nhưng nhân vật/nhận diện RIÊNG).
Mỗi đề tài → **bản dài 16:9 (10–15 phút)** + **bản tóm tắt 9:16 (≤ 3 phút, đủ ý, độ dài tự quyết)**.

## Quyết định đã chốt
- **Claude (phiên Claude Code) là kiểm duyệt chất lượng (QC)** từ V002: 3 cổng `@claude_kich_ban` / `@claude_anh` / `@claude_video`. Giữ phần hay, tự sửa phần yếu, **tối đa 2 vòng/khâu, ≤ 3.000đ sửa/video** (vượt → hỏi Giám đốc). Quy trình: `agents/claude_qc.md`. Khi Giám đốc nhắn "duyệt V00x"/"QC" → làm theo file đó.
- **Kịch bản: Giám đốc giao Claude viết lại TOÀN BỘ khi bản DeepSeek chưa cuốn** (ngoại lệ của luật "chỉ sửa phần yếu" ở cổng `@claude_kich_ban`). Công thức cuốn: câu móc = con số/nghịch lý + hứa một bất ngờ · nhân vật phụ có bí mật (twist giữa phim) · gag cụ thể (vd sửa 12 bản → chọn bản 1) · cao trào bằng hành động, không bằng lời · kết callback đồ vật, ≤ 2 đoạn, không giảng đạo · không lặp ý.
- Bản dài: 10–15 phút là mức tham khảo, **không cố định** — dài hơn chút (vd ~16 phút) vẫn OK.
- Chỉ dùng **DeepSeek API** (deepseek-chat viết, deepseek-reasoner chấm/cấu trúc) + **ai33.pro** (giọng + ảnh) + **ffmpeg**. Không có Claude API, không có model đọc ảnh → Giám đốc duyệt ảnh bằng ảnh lưới.
- Nét vẽ: meme đơn giản (đầu to, tay chân que, viền đen dày, màu phẳng). **Ghép lớp**: thư viện nền + nhân vật sticker (nhiều biểu cảm) + đạo cụ, chuyển động nhẹ. Chỉ ≤ 5 cảnh đặc biệt/video vẽ nguyên khung.
- Ngân sách **5.000–10.000đ/video**; 1 credit ai33 = 0,2đ. Mọi lệnh tốn tiền phải báo giá + hỏi trước.
- Giọng: Vbee (người dùng chọn sau khi nghe thử). Bot Telegram ở giai đoạn 3.
- Bộ công cụ: **Remotion** (`studio/`, dựng 16:9 + 9:16 từ cùng dữ liệu) · **rembg** `isnet-anime` (tách nền) · **stable-ts** (căn văn bản có sẵn vào giọng → mốc từng từ) · python-telegram-bot (GĐ3) · google-api-python-client (GĐ4). KHÔNG dùng CrewAI/LangGraph: dây chuyền tuyến tính + `state.json` rẻ hơn.
- Giá ảnh ai33 thật: ~150–200đ/ảnh (bảng ở `lab/models.json`).
- Model ảnh: **nhân vật/biểu cảm/đạo cụ = `gemini-3.1-flash-lite-image`**, **nền = `gpt-image-2`** (`config.json → image_model_character / image_model_background`).
- MC kênh = phương án A (kính tròn, hoodie xám, mặt chán đời) → `library/nhan_vat/mc/goc.png`, mô tả trong `config.json → mc`.
- 3 cổng duyệt của Giám đốc: ① chọn đề tài · ② ảnh lưới · ③ bản cuối.

## Bản đồ file (chỉ mở file cần cho việc đang làm)
| File | Nội dung |
|---|---|
| `ROADMAP.md` | Lộ trình + ô trạng thái ☐/☑ + nhật ký. **Cập nhật sau mỗi bước.** |
| `agents/README.md` | Danh sách nhân viên, dây chuyền, **quy tắc bàn giao**, cấu trúc thư mục video |
| `agents/<mã>.md` | Hồ sơ 1 nhân viên; mục `## Chỉ dẫn cho AI` = system prompt. Chỉ mở khi làm agent đó |
| `config.json` | Cài đặt chung (model, giọng, style, ngân sách, font) |
| `dungphim/ai33.py` | Client ai33 + sổ chi phí (đã viết lại, dùng được) |
| `lab.py` | Công cụ giai đoạn 1 (check, models, style, narrator, voices, voicetest, compose, cost) |
| `studio/src/Story.tsx` | **Bộ dựng Remotion** (Long 16:9 / Short 9:16): props = {fps, audio, title, scenes[{start,end,bg,chars[{src,pos,motion}],emphasis,cam}], words[{w,s,e}]}. Render: `npx remotion render src/index.ts Long out.mp4 --props=x.json` (cwd `studio/`, ảnh/giọng đặt trong `studio/public/`) |
| `dungphim/cutout.py`, `dungphim/align.py` | Tách nền (rembg) · căn từng từ (stable-ts small + sửa từ bị dồn) — dùng lại ở GĐ2 |
| `dashboard.py` + `dashboard.html` | **Bảng điều khiển** http://localhost:8000 (stdlib, không cài thêm; bấm thẻ nhân viên = xem kết quả; link `#xem=<mã bước>` mở thẳng hộp): xem nhân viên đang làm gì, duyệt cổng, xem video, chạy/dừng/làm lại. Đọc `projects/<id>/live.json` + `log.txt` (do `make.py` ghi) |
| `make.py` | **Trưởng phòng**: `moi`, `chay`, `duyet`, `ve-lai`, `trang-thai`, `lam-lai`; PIPELINE + cổng duyệt `@ngan_sach`, `@duyet_anh`, `@duyet_cuoi` |
| `dungphim/nhanvien/<mã>.py` | Code từng nhân viên (bien_kich, dao_dien, thu_vien, hoa_si, long_tieng, dung_phim, bien_tap_shorts, marketing) |
| `dungphim/{state,deepseek,library}.py` | state.json + phiếu bàn giao · gọi DeepSeek chỉ với hồ sơ agent + ghi chi phí · thư viện `library/` |

API ai33 (đã xác minh từ tài liệu): header `xi-api-key`, base `https://api.ai33.pro`; TTS `POST /v3/text-to-speech` (form: text, voice_id có tiền tố `vbee_`…, speed, with_transcript) → task; ảnh `POST /v1i/task/generate-image` (form: prompt, model_id, generations_count, model_parameters JSON, assets[] + `@img1` trong prompt); giá `POST /v1i/task/price`; model `GET /v1i/models`; giọng `GET /v3/voices?provider=`; task `GET /v1/task/{id}` → metadata.audio_url / result_images[].imageUrl; credit `GET /v1/credits`.

Môi trường: Python `.venv` (3.11, uv) · ffmpeg 9 **không có** filter subtitles/drawtext → vẽ chữ bằng Pillow rồi overlay · font Arial Black thiếu dấu tiếng Việt → dùng `fonts/Anton-Regular.ttf`.

## Trạng thái hiện tại
→ Xem mục đầu tiên còn ☐ trong `ROADMAP.md`.
Key OK, đã cài rembg 2.0.87 / stable-ts / torch 2.15 / Remotion 4 (`studio/`). GĐ1 xong (giọng tạm 08 Anh Khôi). GĐ2 code xong + chạy thử giả OK. Tiếp: Giám đốc chọn đề tài → `make.py moi "..."` → `make.py chay V001`.

## Cách làm việc tiết kiệm token
- Mỗi bước: đọc mục tương ứng trong ROADMAP + hồ sơ agent liên quan → làm → đánh ☑ + 1 dòng nhật ký → báo người dùng ngắn gọn.
- Không mở ảnh/mp4/`.venv`/`lab/*` trừ khi cần kiểm tra kết quả cụ thể.
- Quyết định mới của người dùng → ghi ngay vào mục "Quyết định đã chốt" ở trên.

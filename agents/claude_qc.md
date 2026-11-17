# Claude — Kiểm duyệt chất lượng (QC)
Phòng: Ban giám đốc · Công cụ: phiên Claude Code (đọc văn bản + **xem ảnh**) + `make.py` · Báo cáo cho: Giám đốc

Áp dụng cho video có `"qc": true` trong `state.json` (từ V002). Dây chuyền dừng ở 3 cổng:
`@claude_kich_ban` (sau Biên kịch) · `@claude_anh` (sau Họa sĩ, trước cổng ② của Giám đốc) · `@claude_video` (sau Marketing, trước cổng ③).
Giám đốc nhắn "QC V00x" → xem `make.py trang-thai V00x` để biết đang ở cổng nào → làm đúng mục dưới.

## Luật
- **Trước khi đổi biểu cảm/ảnh thay thế: ghép ảnh xem tận mắt**, đừng đoán theo tên mã (vd `toi/mo_mong` = "mơ mộng" nằm nệm, không phải "mồm mở"; `toi/tram_ngam` = đứng mắt thâm).
- **Gọi thẳng nhân viên ngoài `make.py` → luôn bọc `with dang_lam(p, "<mã bước>", "<tên>")`** để bảng điều khiển hiện "Đang làm".
- **Giữ phần hay, chỉ sửa phần yếu.** Không viết lại / vẽ lại cả mẻ.
- **Tối đa 2 vòng sửa mỗi khâu.** Vòng = xem → sửa → xem lại. Sau vòng 2 vẫn chưa ổn → ghi vào `--luu-y` để Giám đốc quyết.
- **Ngân sách sửa ≤ 3.000đ/video** (`qc_cap_vnd`), cộng dồn cả 3 khâu. Báo giá trong đầu trước khi gọi ai33; sắp vượt → dừng, hỏi Giám đốc.
- Sửa chữ do Claude tự làm (0đ) — không gọi DeepSeek viết lại.
- Xong cổng: `.venv/bin/python make.py qc-xong V00x "Giữ: …; Sửa: …" --luu-y "…"` → tự ghi phiếu + chi phí rồi chạy tiếp dây chuyền (chạy nền nếu bước sau lâu).
- Báo Giám đốc 3–5 dòng: giữ gì, sửa gì, tốn bao nhiêu, còn gì đáng lưu ý.

## ① Kịch bản (`projects/V00x/story.md`)
Trước khi sửa: `cp story.md story_v0.md`.
Chấm (ghi nhận xét ngắn cho từng mục):
1. **Mở đầu 30 giây** có móc người xem không (tình huống/câu hỏi/nghịch lý ngay câu đầu)?
2. **Nhịp**: có đoạn lê thê, lặp ý, liệt kê khô? Câu có quá dài khi đọc thành tiếng?
3. **Cao trào & kết**: có leo thang, có twist/khoảnh khắc đắt giá, kết có dư âm/bài học tự nhiên (không giảng đạo)?
4. **Logic & nhất quán**: tên, tuổi, số tiền, mốc thời gian, nhân vật khớp nhau.
5. **Giọng văn**: tự sự ngôi thứ nhất, đời thường, hài nhẹ chua chát; không văn mẫu, không từ ngữ AI ("hành trình", "bài học quý giá"...).
6. **Đọc thành tiếng**: số viết bằng chữ khi khó đọc, bỏ ký hiệu, ngoặc, emoji.
7. **Đúng đề tài** đã chọn.
Sửa trực tiếp bằng Edit (giữ dòng `# tiêu đề`). Vòng 2: đọc lại toàn bộ một lượt.

## ② Ảnh
Xem: `projects/V00x/luoi_canh.png` (tổng quan) rồi **từng ảnh** đã vẽ cho video này (`can_ve.json` liệt kê):
`library/nhan_vat/<lib_id>/goc.png` + `<bieu_cam>.png` · `library/nen/<id>.png` · `projects/V00x/dac_biet/<id>.png`.
Lỗi cần bắt: sai/khác mặt so với `goc.png` (tóc, áo, kính) · biểu cảm không đúng tên · thừa tay/chân/người · chữ linh tinh trong ảnh · tách nền lẹm/sót viền trắng · nền có người hoặc không hợp bối cảnh · nét vẽ lệch phong cách meme (đầu to, viền đen dày, màu phẳng) · cảnh đặc biệt sai nội dung.
Vẽ lại ĐÚNG ảnh lỗi (~200đ/ảnh): đổi tên ảnh lỗi thành `_loi_<tên>.png`, rồi
```python
from dungphim.state import Project, dang_lam; from dungphim.nhanvien import hoa_si
p = Project("V00x")
need = {"nen": {"id_nen": "mô tả EN sửa lại"}, "nhan_vat_goc": [], "bieu_cam": {"<lib_id>/<bieu_cam>": "mô tả EN sửa lại"}, "dac_biet": [id_canh]}
with dang_lam(p, "hoa_si", "Họa sĩ (QC vẽ lại)"): hoa_si.draw(p, need); hoa_si.grid(p)
```
(Cảnh đặc biệt: sửa `dac_biet_en` trong `storyboard.json` trước nếu mô tả là nguyên nhân lỗi.) Xem lại ảnh mới; vòng 2 chỉ cho ảnh vẫn lỗi.

## ③ Video (`final_16x9.mp4`, `final_9x16.mp4`, thumbnail, `marketing.md`)
1. Cắt khung hình xem nhanh (0đ), vd mỗi 20s một ảnh ghép lưới:
   `ffmpeg -i final_16x9.mp4 -vf "fps=1/20,scale=480:-1,tile=4x4" -frames:v 1 /tmp/.../luoi_video.png` (lặp với `-ss` cho đoạn sau), xem bằng Read.
2. `timing.json`: cảnh có tốc độ đọc bất thường (< 9 hoặc > 26 ký tự/giây) = giọng lỗi/đọc vấp.
3. Đối chiếu `storyboard.json`: biểu cảm/vị trí/chuyển động có hợp lời kể không; cảnh liên tiếp có đơn điệu (cùng nền + cùng tư thế quá lâu)?
4. Shorts: đủ ý, mở đầu mạnh, ≤ 3 phút. Thumbnail: chữ đọc được, mặt nhân vật rõ. Marketing: tiêu đề hấp dẫn, không giật tít sai sự thật.
Sửa:
- Đổi biểu cảm/vị trí/chuyển động/chữ nhấn → sửa `storyboard.json` (hoặc `short.json`) → dựng lại (0đ):
  `python -c "from dungphim.state import Project, dang_lam; from dungphim.nhanvien import dung_phim; p=Project('V00x');\nwith dang_lam(p,'dung_phim_dai','Dựng phim 16:9 (QC)'): dung_phim.render(p)"` (`render(p, short=True)` cho 9:16). Biểu cảm mới chưa có → vẽ như mục ②.
- Sửa lời một cảnh → sửa `loi_ke`, xoá `voice/<id 3 số>.mp3` → `long_tieng.voice(p)` (chỉ đọc cảnh thiếu, vài chục đồng) → dựng lại.
- Thumbnail/marketing → sửa `marketing.md` trực tiếp; thumbnail chạy lại `marketing.run(p)`.
Dựng lại lâu (≈ 6 phút bản dài) → chạy nền.

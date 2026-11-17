# LỘ TRÌNH — Studio phim kể chuyện AI

> Bạn = Giám đốc. Các agent = nhân sự. File này là **bảng theo dõi tiến độ**: mỗi bước có
> lệnh chạy, kết quả mong đợi, chi phí và tiêu chí "đạt". Ô ☐ → ☑ khi xong.
>
> Mỗi đề tài ra **2 sản phẩm**: bản dài **16:9 (10–15 phút)** + bản tóm tắt **9:16 (tối đa 3 phút, đủ ý)**.
> Ngân sách mục tiêu: **5.000–10.000đ / đề tài**. (1 credit ai33 = 0,2đ)

---

## Tổng quan

| Giai đoạn | Mục tiêu | Thời gian | Chi phí | Trạng thái |
|---|---|---|---|---|
| **0. Chuẩn bị** | Điền key, kiểm tra kết nối | 10 phút | 0đ | ☑ |
| **1. Thử nghiệm** | Chốt model ảnh, nét vẽ, giọng, cách ghép lớp | 1–2 ngày | ~3.000đ | ☑ (giọng tạm 08) |
| **2. Dây chuyền tối thiểu** | Ra **video đầu tiên** hoàn chỉnh (cả 2 bản) | 3–5 ngày | ~10.000đ | ⏳ code xong, chờ đề tài V001 |
| **3. Tự động hoá** | Agent kiểm tra + bot Telegram, bạn chỉ duyệt 3 cổng | 3–5 ngày | ~10.000đ/video | ☐ |
| **4. Vận hành & cải tiến** | Chạy đều 5–7 video/tuần, agent đề tài + phân tích | liên tục | 5–10k/video | ☐ |

---

## Giai đoạn 0 — Chuẩn bị (bạn làm)

| # | Việc | Ai | Trạng thái |
|---|---|---|---|
| 0.1 | Mở file `.env`, điền `AI33_API_KEY` và `DEEPSEEK_API_KEY` (**không dán key vào chat**) | Bạn | ☑ |
| 0.2 | Chạy `.venv/bin/python lab.py check` → thấy số credit ai33 + DeepSeek trả lời "OK" | Bạn/Claude | ☑ |
| 0.3 | Cài công cụ trên máy: **rembg** (tách nền), **stable-ts** (căn phụ đề), **Remotion** (`studio/`, dựng phim) | Claude | ☑ |

---

## Giai đoạn 1 — Thử nghiệm (chốt "bộ nhận diện kênh")

Kết quả nằm trong thư mục `lab/`. Mọi chi phí ghi vào `lab/chi_phi.csv`.

| # | Bước | Lệnh | Kết quả bạn nhận | Chi phí | Tiêu chí đạt | ☐ |
|---|---|---|---|---|---|---|
| 1.1 | Lấy **giá thật** mọi model ảnh | `lab.py models` | Bảng model xếp từ rẻ → đắt, giá 1 ảnh (đ) | 0đ | Có ≥ 2 model ≤ 350 credit/ảnh hỗ trợ ảnh tham chiếu | ☑ |
| 1.2 | **Thử nét vẽ**: 3–4 model × (1 nhân vật + 1 nền) | `lab.py style` | Ảnh so sánh `lab/style/_so_sanh.png` | ~2.000đ | Bạn chọn được 1 model + nét vẽ ưng ý | ☑ |
| 1.3 | **Thiết kế nhân vật người kể** riêng của kênh (3–4 phương án) | `lab.py narrator` | `lab/narrator/_so_sanh.png` | ~1.000đ | Bạn chọn 1 nhân vật đại diện kênh | ☑ |
| 1.4 | **Thử giọng**: 6–8 giọng Vbee đọc cùng 1 đoạn | `lab.py voices` rồi `lab.py voicetest` | File mp3 trong `lab/voices/` | ~300đ | Bạn chọn 1 giọng cố định cho kênh | ☐ |
| 1.5 | **Thử ghép lớp** (Remotion + rembg + stable-ts): 1 nền + 2 nhân vật + chuyển động + phụ đề, cả 16:9 và 9:16 | `lab.py compose` | `lab/compose/demo_16x9.mp4`, `demo_9x16.mp4` | ~500đ | Nhìn tự nhiên, phụ đề khớp từng từ, đúng dấu | ☑ (Giám đốc duyệt 16/11) |

**Bạn quyết định ở cuối giai đoạn 1:** model ảnh · nét vẽ · nhân vật người kể · giọng đọc.
→ Claude ghi các lựa chọn vào `config.json`.

---

## Giai đoạn 2 — Dây chuyền tối thiểu (video đầu tiên)

Mỗi agent = 1 bước trong lệnh `make.py`. Chạy từng bước để bạn xem kết quả từng "nhân viên".

| # | Agent (nhân sự) | Việc | Đầu ra | ☐ |
|---|---|---|---|---|
| 2.1 | 🤖 Trưởng phòng (Điều phối) | `state.json`, chạy tiếp khi dừng, trần ngân sách, sổ chi phí | `projects/<video>/state.json` | ☑ (V001 chạy thật OK) |
| 2.2 | 🤖 Biên kịch | Dàn ý → kịch bản kể ngôi thứ nhất 10–15 phút | `story.md` | ☑ (V001 chạy thật OK) |
| 2.3 | 🤖 Đạo diễn phân cảnh | Hồ sơ nhân vật + **công thức dàn cảnh** từng cảnh (nền, nhân vật, biểu cảm, vị trí, chuyển động) | `storyboard.json` | ☑ (V001 chạy thật OK) |
| 2.4 | 🤖 Quản lý thư viện | So storyboard với `library/` → danh sách nền/biểu cảm/đạo cụ còn thiếu | `can_ve.json` | ☑ (V001 chạy thật OK) |
| 2.5 | 🤖 Họa sĩ | Chỉ vẽ phần thiếu + tách nền nhân vật + vài cảnh đặc biệt | `library/…png` | ☑ (V001 chạy thật OK) |
| 2.6 | 🤖 Lồng tiếng | Giọng từng cảnh + kiểm tra độ dài | `voice/*.mp3` | ☑ (V001 chạy thật OK) |
| 2.7 | 🤖 Dựng | Ghép lớp + chuyển động + phụ đề + chữ nhấn + nhạc → **bản 16:9** | `final_16x9.mp4` | ☑ (V001 chạy thật OK) |
| 2.8 | 🤖 Biên tập Shorts | Viết lại bản tóm tắt (đủ ý, ≤ 3 phút) + chọn cảnh | `short.json` | ☑ (V001 chạy thật OK) |
| 2.9 | 🤖 Dựng (dọc) | Bố cục 9:16 → **bản tóm tắt** | `final_9x16.mp4` | ☑ (V001 chạy thật OK) |
| 2.10 | 🤖 Marketing | 3 tiêu đề, thumbnail, mô tả, hashtag | `marketing.md`, `thumbnail.png` | ☑ (V001 chạy thật OK) |

**Mốc đạt:** 1 đề tài thật → 2 video xem được, chi phí ≤ 10.000đ (ghi trong `chi_phi.csv`).

---

## Giai đoạn 3 — Tự động hoá (bạn chỉ còn 3 cổng duyệt)

| # | Việc | ☐ |
|---|---|---|
| 3.1 | 🤖 Biên tập (chấm kịch bản theo thang điểm, sửa tối đa 2 vòng, cờ nội dung nhạy cảm) | ☐ |
| 3.2 | 🤖 Biên tập Shorts tự chấm 5 câu hỏi chất lượng | ☐ |
| 3.3 | Bot **Telegram**: báo tiến độ, gửi ảnh lưới các cảnh, video xem thử, nút [Duyệt] [Sửa] [Huỷ] | ☐ |
| 3.4 | Lệnh `make.py auto "<đề tài>"` chạy trọn từ đầu → cuối, dừng ở cổng duyệt | ☐ |
| 3.5 | Chạy 3 video liên tiếp không cần sửa code | ☐ |

**3 cổng duyệt của bạn:** ① chọn đề tài · ② xem ảnh lưới (gõ số cảnh cần vẽ lại) · ③ duyệt bản cuối + chọn thumbnail.

---

## Giai đoạn 4 — Vận hành & cải tiến

| # | Việc | ☐ |
|---|---|---|
| 4.1 | 🤖 Đề tài: mỗi thứ Hai gửi 10–15 đề tài qua Telegram | ☐ |
| 4.2 | 🤖 Phân tích: đọc số liệu YouTube → bài học cho agent Đề tài / Biên tập | ☐ |
| 4.3 | Thư viện nền/nhân vật lớn dần → chi phí/video giảm dần | ☐ |

**Lịch tuần của bạn khi vận hành:** Thứ Hai 10 phút chọn đề tài → trong tuần nhận Telegram, mỗi video ~30 phút duyệt + đăng.

---

## Chi phí dự kiến / đề tài (cập nhật sau giai đoạn 1)

| Hạng mục | Video đầu | Video sau (có thư viện) |
|---|---|---|
| Ảnh (nền + nhân vật + cảnh đặc biệt + thumbnail) | ~35 ảnh | ~15 ảnh |
| Giọng đọc (bản dài + Shorts) | đo ở bước 1.4 | |
| DeepSeek | ~1.000–2.000đ | ~1.000–2.000đ |
| **Tổng** | **mục tiêu ≤ 10.000đ** | **mục tiêu ≤ 7.000đ** |

Giá thật ai33 (16/11/2026): rẻ nhất ~150–200đ/ảnh (`lab/models.json`) → ảnh video đầu ≈ 6–7k, video sau ≈ 3k.

---

## Nhật ký

| Ngày | Việc | Ghi chú |
|---|---|---|
| 2026-11-16 | Chốt phương án: 1 người + đội agent, 2 định dạng, phong cách ghép lớp | Chỉ dùng DeepSeek + ai33 (chưa có Claude API key → kiểm tra ảnh bằng mắt qua ảnh lưới) |
| 2026-11-16 | Xong công cụ giai đoạn 1 (`lab.py`), sổ chi phí tự động (`lab/chi_phi.csv`) | `make.py` + `dungphim/story,media,render,llm.py` là bản nháp cũ, sẽ viết lại ở giai đoạn 2 theo kiểu ghép lớp |
| 2026-11-16 | Lập hồ sơ 12 nhân viên (`agents/`), quy tắc bàn giao, `CLAUDE.md` | Mỗi agent chỉ đọc hồ sơ + đầu vào + phiếu bàn giao; phiên Claude mới chỉ cần đọc `CLAUDE.md` |
| 2026-11-16 | Key OK (1.431.683 credit). Bảng giá 22 model: 149–588đ/ảnh. Chốt bộ công cụ: Remotion (dựng), rembg (tách nền), stable-ts (phụ đề từng từ), python-telegram-bot (GĐ3), YouTube API (GĐ4). Không dùng CrewAI/LangGraph (tốn token) | |
| 2026-11-16 | 1.2 thử nét vẽ 4 model (1.399đ). Chốt: nhân vật/biểu cảm/đạo cụ = gemini-3.1-flash-lite-image (183đ), nền = gpt-image-2 (174đ). Loại seedream-4, flux-2-pro (tự vẽ thêm người vào nền) | |
| 2026-11-16 | 1.3 vẽ 4 phương án người kể (gemini, ~730đ); 1.4 lấy 100 giọng Vbee, đọc thử 8 giọng (504đ; giá giọng ~1,1 credit/ký tự ở mọi hạng). Tổng lab 2.636đ. Chờ Giám đốc chọn người kể + giọng | |
| 2026-11-16 | Chốt MC kênh = phương án A (kính tròn, hoodie xám) → `library/nhan_vat/mc/goc.png` | |
| 2026-11-16 | 1.5 ghép lớp OK (0đ, dùng lại ảnh): Remotion `studio/src/Story.tsx` (Long/Short), rembg `dungphim/cutout.py`, stable-ts `dungphim/align.py` (model small + sửa từ bị dồn). Video: `lab/compose/demo_16x9.mp4`, `demo_9x16.mp4` | Còn chờ: chọn giọng |
| 2026-11-16 | GĐ2: viết xong 9 nhân viên (`dungphim/nhanvien/*.py`) + Trưởng phòng (`make.py`). Chạy thử miễn phí (dữ liệu giả) qua lồng tiếng→dựng 16:9/9:16→ảnh lưới→thumbnail: OK. Giọng tạm: 08 Anh Khôi | Chờ Giám đốc chọn đề tài V001 |
| 2026-11-16 | Giám đốc xem demo ghép lớp 1.5: duyệt ("quá ổn") | Tiếp: chọn đề tài V001 |
| 2026-11-16 | V001 "Lần đầu đi làm bị sếp bắt OT không lương" chạy hết dây chuyền: 112 cảnh, 4 nhân vật, 31/32 ảnh (lỗi `V001_toi/ngai_ngung` → dùng mặt bình thường). Bản dài 13,2 phút + Shorts 1,7 phút + marketing. Tổng **10.614đ** (ảnh ~6.500đ, giọng ~3.400đ, DeepSeek ~700đ). `make.py`: cổng `@ngan_sach` nay luôn dừng báo giá | Chưa có nhạc nền. Chờ Giám đốc duyệt bản cuối (cổng ③) |
| 2026-11-17 | V001 kéo dài: chèn 26 cảnh (đêm OT + đối chất sếp) sau cảnh 45, vẽ lại `ngai_ngung`. Bảng điều khiển `dashboard.py` (localhost:8000); `make.py` ghi `log.txt` + `live.json` | Bản dài không cố định 15 phút |
| 2026-11-17 | Claude làm QC từ V002: 3 cổng `@claude_kich_ban/@claude_anh/@claude_video`, ≤2 vòng/khâu, ≤3.000đ sửa/video. Quy trình `agents/claude_qc.md`, lệnh `make.py qc-xong`. Bảng điều khiển hiện cổng QC | V001 bỏ qua QC (tạo trước) |
| 2026-11-17 | Claude viết lại toàn bộ kịch bản V001 (0đ): bỏ lặp/lệch mốc thời gian, mở bằng "197 tiếng", twist anh Hùng 3 cuốn sổ, gag banner 12 bản, kết callback. 2.751 chữ ≈ 11,5 phút. Bản cũ `story_v0.md` | Chờ Giám đốc duyệt lời → dựng lại (~4.000đ) |
| 2026-11-17 | V001 dựng lại từ đạo diễn: 91 cảnh. Ép storyboard dùng ảnh có sẵn (anh Hùng trùng mã, biểu cảm trùng nghĩa) → vẽ 6.996đ → 2.570đ; cảnh đặc biệt đổi sang 2,3,48,74,79. Sửa `lam-lai` xoá cổng chờ cũ; thêm `state.dang_lam()` để bảng điều khiển hiện "Đang làm" khi gọi thẳng nhân viên | Chờ duyệt ngân sách vẽ |
| 2026-11-17 | Sửa Đạo diễn: đọc ảnh có sẵn trên đĩa (nhân vật/biểu cảm/nền), tự ghép id gần giống (hung→anh_hung), bước "gom biểu cảm + chọn cảnh đặc biệt" (≤ `max_bieu_cam_moi`=6, ≥2 cảnh ĐB ở nửa sau). Thử trên phân cảnh lỗi: 20 biểu cảm mới → 4, cảnh ĐB 3/7/28/69/90 (~90đ tiền thử) | Áp dụng từ lần chạy Đạo diễn sau |
| 2026-11-17 | Tăng tốc: (A) `make.py` chạy Lồng tiếng song song với Họa sĩ, chờ xong trước cổng duyệt ảnh, lỗi giọng → làm lại sau cổng; (B) Họa sĩ vẽ theo phụ thuộc (`_schedule`): nền/cảnh không cần nhân vật mới vẽ ngay, biểu cảm mở khoá ngay khi gốc xong. Chi phí bước tính theo loại (`Project.spent_of`), khoá ghi state.json. Bảng điều khiển hiện cả việc song song (`live.json → song_song`) | |
| 2026-11-17 | ai33 `generate_image`: ảnh chờ quá 5 phút (`IMAGE_RETRY_AFTER`) hoặc lỗi → gửi lại 1 lần, lấy bản xong trước. V001: dừng lượt vẽ cũ (kẹt 10 phút), vẽ tiếp 8 ảnh còn thiếu bằng code mới | Lần gửi đầu nếu ai33 vẫn tính tiền thì sổ chi phí không ghi được |
| 2026-11-17 | Phát hiện ai33 giới hạn **20 việc/tài khoản trong hàng đợi** (lỗi 429 active_task_limit) = nguyên nhân chậm/lỗi; sửa `_req` chờ khi hàng đợi đầy; sửa lỗi gửi lại mất ảnh tham chiếu (invalid_assets_upload). Giám đốc dừng vẽ: V001 dựng bằng ảnh trong kho (giữ ĐB 48, 4 cảnh ĐB + 3 biểu cảm thay bằng ảnh có sẵn + chữ nhấn) | Đang dựng |
| 2026-11-17 | QC V001 bằng ảnh lưới khung hình: phát hiện `toi/mo_mong` (= nằm nệm) bị dùng cho cảnh sốc → 19 cảnh nằm giữa văn phòng. Sửa → `hoi_hop`/`tram_ngam`, dựng lại 16:9 + 9:16 (0đ). Sửa marketing ghi nhầm người kể là "cô gái" | Chờ Giám đốc duyệt bản cuối |
| 2026-11-17 | Bảng điều khiển: bấm thẻ nhân viên → xem ngay kết quả (kịch bản, bảng cảnh có ảnh nền + nhân vật, ảnh theo nhóm, nghe từng câu thoại + đánh dấu tốc độ lạ, video, Shorts, marketing). Route `/lib/` cho ảnh thư viện; link `#xem=<mã bước>` mở thẳng hộp. Sửa: "Đang làm" ưu tiên hơn "Xong", hết nháy | |
| 2026-11-17 | ✅ **V001 chốt** (Giám đốc duyệt bản cuối). Tổng 16.276đ (bản đầu ~10.600đ + làm lại ~5.700đ). Để nâng cấp sau: nhạc nền, cảnh "sếp nhìn bốn cuốn sổ" dùng `sep/soc`, vẽ 4 cảnh ĐB còn thiếu | Tiếp: V002 (có QC Claude) hoặc nâng cấp "người khác dùng không cần Claude" |

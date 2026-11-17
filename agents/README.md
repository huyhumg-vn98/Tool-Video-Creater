# Nhân sự studio & quy tắc bàn giao

Mỗi agent = 1 nhân viên, có **1 file hồ sơ** trong thư mục này. Code chỉ nạp đúng hồ sơ của nhân viên
đang làm (mục `## Chỉ dẫn cho AI` là system prompt) — không nạp lịch sử, không nạp cả project.

## Danh sách nhân viên

| Mã | Nhân viên | Phòng | Công cụ | Giai đoạn |
|---|---|---|---|---|
| `truong_phong` | Trưởng phòng sản xuất (điều phối) | Ban giám đốc | code + Telegram (GĐ3) | 2 |
| `de_tai` | Chuyên viên đề tài | Nội dung | deepseek-reasoner | 4 |
| `bien_kich` | Biên kịch | Nội dung | deepseek-chat | 2 |
| `bien_tap` | Biên tập (chấm & sửa kịch bản) | Nội dung | deepseek-reasoner | 3 |
| `dao_dien` | Đạo diễn phân cảnh | Hình ảnh | deepseek-chat (JSON) | 2 |
| `thu_vien` | Quản lý thư viện | Hình ảnh | code | 2 |
| `hoa_si` | Họa sĩ | Hình ảnh | ai33 + rembg | 2 |
| `long_tieng` | Lồng tiếng | Âm thanh | ai33 + stable-ts | 2 |
| `dung_phim` | Dựng phim (16:9 và 9:16) | Hậu kỳ | Remotion + ffmpeg | 2 |
| `bien_tap_shorts` | Biên tập Shorts | Nội dung | deepseek-chat | 2 |
| `marketing` | Marketing (tiêu đề, thumbnail, mô tả) | Kinh doanh | deepseek-chat + ghép ảnh thư viện | 2 |
| `phan_tich` | Phân tích số liệu kênh | Kinh doanh | deepseek-reasoner | 4 |

Giám đốc (bạn) duyệt ở 3 cổng: ① chọn đề tài · ② xem ảnh lưới các cảnh · ③ duyệt bản cuối.
(Chưa có model đọc ảnh → việc "kiểm định hình ảnh" do Giám đốc làm ở cổng ②.)

## Dây chuyền

```
de_tai → [GĐ ①] → bien_kich ⇄ bien_tap → dao_dien → thu_vien → hoa_si → [GĐ ②]
      → long_tieng → dung_phim(16:9) → bien_tap_shorts → long_tieng → dung_phim(9:16)
      → marketing → [GĐ ③] → đăng → phan_tich → de_tai
```

## Quy tắc bàn giao (bắt buộc)

1. **Mỗi lúc chỉ 1 nhân viên giữ việc** (`state.json → stage`).
2. Nhân viên **chỉ đọc**: hồ sơ của mình + các file trong mục "Nhận vào" + **phiếu bàn giao** của người trước.
3. Làm xong, nhân viên **ghi phiếu bàn giao** vào `state.json` (tối đa 5 dòng):
   ```json
   "handoff": {
     "tu": "bien_kich", "cho": "bien_tap",
     "da_lam": "Viết kịch bản 2.150 chữ, 6 đoạn",
     "file": ["story.md"],
     "luu_y": "Đoạn 4 có chi tiết giá tiền cần kiểm tra",
     "chi_phi_vnd": 640
   }
   ```
4. Không đạt tiêu chí → trả về người trước kèm lý do (tối đa 2 vòng), quá 2 vòng → hỏi Giám đốc.
5. Trưởng phòng cộng chi phí; chạm 80% ngân sách → dừng, hỏi Giám đốc.

## Cấu trúc 1 video (`projects/<mã>/`)

```
state.json        ← bảng trạng thái + phiếu bàn giao (đọc file này là biết video đang ở đâu)
story.md          ← bien_kich
review.json       ← bien_tap
storyboard.json   ← dao_dien
can_ve.json       ← thu_vien
voice/  short/    ← long_tieng
final_16x9.mp4  final_9x16.mp4   ← dung_phim
marketing.md  thumbnail.png      ← marketing
chi_phi.csv       ← tự động
```
Tài sản dùng chung giữa các video: `library/` (nền, nhân vật, biểu cảm, đạo cụ).

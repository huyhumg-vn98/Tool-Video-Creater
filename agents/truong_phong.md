# 🤖 Trưởng phòng sản xuất — `truong_phong`
Phòng: Ban giám đốc · Công cụ: code (không dùng AI) · Báo cáo cho: Giám đốc

## Nhiệm vụ
- Tạo `state.json` khi có video mới, giao việc cho nhân viên theo thứ tự dây chuyền.
- Sau mỗi bước: kiểm tra đầu ra có đúng khuôn, cộng chi phí, chuyển `stage` cho người tiếp theo.
- Lỗi mạng/API → thử lại tối đa 3 lần. Bước bị trả về quá 2 vòng → dừng, hỏi Giám đốc.
- Ước tính chi phí trước mỗi bước tốn tiền; tổng chạm 80% `budget_vnd_per_video` → dừng, hỏi Giám đốc.
- Đến cổng duyệt → đặt `waiting_for` và (GĐ3) nhắn Telegram.
- Chạy lại lệnh → tiếp tục đúng chỗ đã dừng, không làm lại bước đã xong.

## Nhận vào
`state.json`, phiếu bàn giao mới nhất, `config.json`.

## Trả ra
`state.json` cập nhật; dòng tóm tắt in ra màn hình: `V001 | bien_kich ✓ 640đ | → bien_tap | tổng 640/10.000đ`.

## Tiêu chí hoàn thành
Video đi hết dây chuyền, `state.json → stage = "xong"`, tổng chi phí ≤ ngân sách.

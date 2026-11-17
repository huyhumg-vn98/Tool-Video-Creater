# 🤖 Lồng tiếng — `long_tieng`
Phòng: Âm thanh · Công cụ: ai33 TTS + **stable-ts** (căn thời gian từng từ, chạy trên máy) · Báo cáo cho: `dung_phim`

## Nhiệm vụ
Đọc `loi_ke` từng cảnh thành file giọng; căn mốc thời gian từng từ cho phụ đề; tự kiểm tra lỗi.

## Nhận vào
`storyboard.json` (bản dài) hoặc `short.json` (bản Shorts); `config.json → voice_id, voice_speed / short_voice_speed`.

## Trả ra
- `voice/<id cảnh>.mp3` (bản dài) hoặc `short/voice/<id>.mp3`
- `timing.json`: `{ "<id cảnh>": {"dur": giây, "words": [{"w": "chữ", "s": giây, "e": giây}]} }`
  (stable-ts căn **văn bản có sẵn** vào giọng đọc — không cần nhận dạng giọng nói)

## Tự kiểm tra
Tốc độ đọc = số ký tự / số giây. Ngoài khoảng 9–22 ký tự/giây → đọc lại 1 lần, vẫn lỗi → ghi `luu_y` phiếu bàn giao.

## Tiêu chí hoàn thành
Đủ file giọng + timing cho mọi cảnh, không cảnh nào lỗi tốc độ.

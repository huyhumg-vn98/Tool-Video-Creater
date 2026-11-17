# 🤖 Quản lý thư viện — `thu_vien`
Phòng: Hình ảnh · Công cụ: code (không dùng AI) · Báo cáo cho: `hoa_si`

## Nhiệm vụ
So `storyboard.json` với `library/index.json`, liệt kê tài sản còn thiếu cần vẽ; ước tính chi phí.

## Nhận vào
`storyboard.json`, `library/index.json`, bảng giá model (`lab/models.json`).

## Trả ra
`can_ve.json`: `{ "nen": [...], "nhan_vat_goc": [...], "bieu_cam": [{"nhan_vat","bieu_cam"}], "dao_cu": [...], "dac_biet": [id cảnh], "uoc_tinh_vnd": 0 }`

## Thư viện `library/`
```
library/index.json
library/nen/<id>.png                 (16:9)
library/nhan_vat/<id>/goc.png        (ảnh gốc, nền trắng)
library/nhan_vat/<id>/<bieu_cam>.png (đã tách nền, PNG trong suốt)
library/dao_cu/<id>.png              (đã tách nền)
```

## Tiêu chí hoàn thành
Mọi tài sản storyboard cần đều có trong thư viện hoặc trong `can_ve.json`.

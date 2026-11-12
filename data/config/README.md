# data/config

Cấu hình tái lập dataset và kịch bản (docs/DATA_MODEL.md mục 3 và 8).

- [x] `areas.json`: tâm Bến Thành, vùng tải nửa cạnh 4,5 km + đệm 0,5 km, vùng demo nửa cạnh 2 km, `network_type="drive"`. **[Đề xuất]**, nhóm xác nhận ở buổi họp.
- [x] `speeds.json`: tốc độ theo loại đường, mặc định 20 km/h, bỏ qua `maxspeed`. **[Giả định]**, số mô phỏng, không phải đo thực tế.
- [ ] `scenarios.json`: hệ số ùn tắc (`alpha >= 1`), seed (T40).

Đổi `areas.json` thì phải chạy lại `python scripts/prepare_data.py download --force`. Đổi `speeds.json` thì phải tính lại `v_max` và mọi kết quả benchmark.

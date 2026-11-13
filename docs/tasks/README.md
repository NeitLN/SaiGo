# Phiếu giao việc

Mỗi phiếu tự đủ: người nhận chỉ cần đọc phiếu (và các file phiếu trỏ tới) là làm được. Phiếu bổ sung cho mô tả gốc trong [TASKS.md](../TASKS.md): ghi rõ ai sở hữu file nào, phải dùng interface nào, và phụ thuộc chặn ở mức nào.

**Trạng thái: Đã duyệt 26/10** ([ROADMAP](../ROADMAP.md) mục 6). TASKS.md đã đồng bộ; người tích hợp (Tiến) cập nhật GitHub bằng `--sync` sau khi PR đồng bộ merge.

| Phiếu | Người | Ngày | Issue | Trạng thái 26/10 |
|---|---|---|---|---|
| [T34 — Release dữ liệu thô](T34-release-data.md) | Minh | 26/10 | tạo khi chạy `--sync` | |
| [T01 — Định dạng đồ thị, fixture, `load_graph`](T01-graph-format.md) | Tiến | 26–27/10 | [#3](https://github.com/NeitLN/SaiGo/issues/3) | ✅ #57; còn kiểm dữ liệu thật (chờ T34) |
| [T10 — Hàm địa lý](T10-geo.md) | Tiến | 26–27/10 | [#6](https://github.com/NeitLN/SaiGo/issues/6) | ✅ #58 |
| [T11 — Dijkstra](T11-dijkstra.md) | Tiến | 27–28/10 | [#7](https://github.com/NeitLN/SaiGo/issues/7) | ✅ #59 |
| [T13 — API skeleton](T13-api-skeleton.md) | Duy Anh (sáng giao Minh, chiều Duy Anh làm) | 26/10 | [#49](https://github.com/NeitLN/SaiGo/issues/49) | ✅ #73 |
| [T14 — Bản đồ skeleton](T14-map-skeleton.md) | Minh | 27–28/10 | [#50](https://github.com/NeitLN/SaiGo/issues/50) | |
| [T15 — Chạy MW trên máy thứ hai](T15-second-machine.md) | Bảo | 29/10 | [#51](https://github.com/NeitLN/SaiGo/issues/51) | |
| [T20 — A*](T20-astar.md) | Tiến | 30–31/10 | [#9](https://github.com/NeitLN/SaiGo/issues/9) | ✅ #62 |
| [T12 — CLI](T12-cli.md) | Bảo (chuyển từ Tiến 26/10) | 30–31/10 | [#8](https://github.com/NeitLN/SaiGo/issues/8) | |
| [T21 — Đối chứng NetworkX](T21-oracle.md) | Duy Anh (làm thay dự phòng của Bảo) | 26/10 | [#10](https://github.com/NeitLN/SaiGo/issues/10) | ✅ #64 |
| [T62 — E3 tăng quy mô](T62-scaling.md) | Tiến (Minh review) | 13/11 | [#27](https://github.com/NeitLN/SaiGo/issues/27) | Đặc tả đã duyệt 13/11 |
| [T63 — E4 ùn tắc, đóng đường](T63-congestion-closure.md) | Tiến (Minh review) | 14/11 | [#28](https://github.com/NeitLN/SaiGo/issues/28) | Đặc tả đã duyệt 13/11 |
| [T74 — E5 tour](T74-tour-benchmark.md) | Tiến (Minh review) | 15/11 | [#36](https://github.com/NeitLN/SaiGo/issues/36) | Đặc tả đã duyệt 13/11 |
| [M9 — Hoàn thiện (G1, T65, T80–T83)](M9-finish.md) | Tiến (Minh review) | 13–22/11 | — | Mini |

Khi xong một phiếu: ghi bằng chứng (lệnh và kết quả) trong PR, sửa dòng PROGRESS của task mình. Không tự sửa ROADMAP hay STATUS; người tích hợp cập nhật sau khi ghép và kiểm chung.

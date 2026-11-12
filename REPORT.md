## 📉 Burndown SaiGo

_Tự động cập nhật 04:12 13/11/2026 (giờ VN) bởi workflow `tracking.yml` từ trạng thái issue/PR thật. Số những ngày đã qua được chốt cuối ngày và không bị sửa lại; số hôm nay là tạm tính. Cách tính ở đầu file `scripts/tracking/burndown.py`._

![Burndown](https://raw.githubusercontent.com/NeitLN/SaiGo/tracking/burndown.png?v=43307852425)

- **Phạm vi hiện tại:** 136 giờ ước lượng, 46 task (đã cắt 3 giờ)
- **Đã đóng:** 100 giờ — có bằng chứng (PR/commit) 100 giờ · **Còn lại:** 36 giờ, 11 task mở
- **Đường lý tưởng hôm nay:** 0 giờ → **chậm** hơn kế hoạch 36.0 giờ
- Mốc: cổng G1 05/11 · final ready 12/11 · thuyết trình 19/11 · nộp 22/11

### Theo tuần

| Tuần | Giờ đến hạn | Giờ hoàn thành | Task xong | Còn lại cuối tuần | PR merge | Lượt review |
|---|---:|---:|---:|---:|---:|---:|
| Tuần 1 · 19–25/10 | 27 | 10 | 3 | 129 | 2 | 3 |
| Tuần 2 · 26/10–01/11 | 30 | 69 | 24 | 57 | 36 | 57 |
| Tuần 3 · 02–08/11 | 62 | 4 | 2 | 53 | 4 | 3 |
| Tuần 4 · 09–15/11 | 17 | 17 | 6 | 36 | 7 | 5 |

### Theo thành viên

| Thành viên | Giờ được giao | Giờ hoàn thành có bằng chứng | Task xong | Đóng tay | Task mở | PR đã merge | PR đã review (có nội dung) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bảo (@dobaovlu) | 18.2 | 11.0 | 5 | 0 | 4 | 5 | 15 |
| Duy Anh (@anh7032) | 34.8 | 30.0 | 10 | 0 | 3 | 19 | 15 |
| Minh (@Jayson135724) | 28.8 | 21.5 | 9 | 0 | 4 | 9 | 31 |
| Tiến (@NeitLN) | 54.2 | 37.5 | 13 | 0 | 8 | 16 | 7 |

### Đóng trong 7 ngày qua

- 13/11 · #78 T34 · Đưa dữ liệu thô lên Release và kiểm hash trên 2 máy (2 h, qua commit)
- 13/11 · #34 T72 · Ma trận chi phí từ đồ thị và `/api/tour` (4 h, qua commit)
- 13/11 · #26 T61 · Cắt lồng nhau cho thí nghiệm tăng quy mô (3 h, qua commit)
- 13/11 · #23 T54 · UI: đóng đoạn đường và báo không có đường (3 h, qua commit)
- 13/11 · #20 T51 · API `/api/route` và `/api/dataset` (3 h, qua PR)
- 13/11 · #8 T12 · CLI tìm đường (2 h, qua PR)

### Ghi chú

- Backlog ban đầu (40 task, ước lượng giờ) do Tiến lập từ `docs/TASKS.md` bằng script ngày 23/10/2026; trạng thái sau đó do từng thành viên cập nhật. Không dựng lại dữ liệu trước ngày này.
- Ước lượng lấy cận trên của khoảng trong TASKS.md (ví dụ "2–3 h" → 3); "nhiều buổi" (essay) được giả định là 10 giờ.
- #1 đóng bằng commit trực tiếp trước khi bật bảo vệ branch `main`; từ đó mọi thay đổi phải qua PR có review.
- Số liệu từng ngày: [`daily.csv`](https://github.com/NeitLN/SaiGo/blob/tracking/daily.csv) trên branch `tracking`.

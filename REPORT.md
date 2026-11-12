## 📉 Burndown SaiGo

_Tự động cập nhật 02:39 13/11/2026 (giờ VN) bởi workflow `tracking.yml` từ trạng thái issue/PR thật. Số những ngày đã qua được chốt cuối ngày và không bị sửa lại; số hôm nay là tạm tính. Cách tính ở đầu file `scripts/tracking/burndown.py`._

![Burndown](https://raw.githubusercontent.com/NeitLN/SaiGo/tracking/burndown.png?v=43292376238)

- **Phạm vi hiện tại:** 136 giờ ước lượng, 46 task (đã cắt 3 giờ)
- **Đã đóng:** 85 giờ — có bằng chứng (PR/commit) 85 giờ · **Còn lại:** 51 giờ, 16 task mở
- **Đường lý tưởng hôm nay:** 0 giờ → **chậm** hơn kế hoạch 51.0 giờ
- Mốc: cổng G1 05/11 · final ready 12/11 · thuyết trình 19/11 · nộp 22/11

### Theo tuần

| Tuần | Giờ đến hạn | Giờ hoàn thành | Task xong | Còn lại cuối tuần | PR merge | Lượt review |
|---|---:|---:|---:|---:|---:|---:|
| Tuần 1 · 19–25/10 | 27 | 10 | 3 | 129 | 2 | 3 |
| Tuần 2 · 26/10–01/11 | 30 | 69 | 24 | 57 | 36 | 58 |
| Tuần 3 · 02–08/11 | 62 | 4 | 2 | 53 | 4 | 3 |
| Tuần 4 · 09–15/11 | 17 | 2 | 1 | 51 | 1 | 0 |

### Theo thành viên

| Thành viên | Giờ được giao | Giờ hoàn thành có bằng chứng | Task xong | Đóng tay | Task mở | PR đã merge | PR đã review (có nội dung) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bảo (@dobaovlu) | 18.2 | 9.0 | 4 | 0 | 5 | 4 | 15 |
| Duy Anh (@anh7032) | 34.8 | 30.0 | 10 | 0 | 3 | 19 | 16 |
| Minh (@Jayson135724) | 28.8 | 17.0 | 7 | 0 | 6 | 7 | 28 |
| Tiến (@NeitLN) | 54.2 | 29.0 | 10 | 0 | 11 | 13 | 5 |

### Đóng trong 7 ngày qua

- 13/11 · #78 T34 · Đưa dữ liệu thô lên Release và kiểm hash trên 2 máy (2 h, qua commit)

### Ghi chú

- Backlog ban đầu (40 task, ước lượng giờ) do Tiến lập từ `docs/TASKS.md` bằng script ngày 23/10/2026; trạng thái sau đó do từng thành viên cập nhật. Không dựng lại dữ liệu trước ngày này.
- Ước lượng lấy cận trên của khoảng trong TASKS.md (ví dụ "2–3 h" → 3); "nhiều buổi" (essay) được giả định là 10 giờ.
- #1 đóng bằng commit trực tiếp trước khi bật bảo vệ branch `main`; từ đó mọi thay đổi phải qua PR có review.
- Số liệu từng ngày: [`daily.csv`](https://github.com/NeitLN/SaiGo/blob/tracking/daily.csv) trên branch `tracking`.

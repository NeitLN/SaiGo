# Thực nghiệm

Cấu hình, bộ truy vấn, môi trường đo và phân tích kết quả. Thiết kế: [TOPIC.md](TOPIC.md) mục 18, [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md).
Mọi số dưới đây truy ngược được bằng `run_id` trong `results/`. Bảng sinh bằng `python scripts/summarize_results.py results/<run_id>` (T65); phần diễn giải được viết tách riêng khỏi số đo.

## E2 — A* vs Dijkstra trên vùng demo (RQ1)

**Nguồn chính thức:** run_id `20261031-1556-demo-054f300` (T60, #92) · dataset `hcm-benthanh-r2000-20261024` (1.889 node, 4.004 cạnh) · 1.000 cặp phân tầng theo δ = khoảng cách thẳng / L (333 ngắn, 334 trung bình, 333 dài), seed 42 · 20 truy vấn warm-up, mỗi cặp lặp 5 lần, lấy median · Python 3.11.9, Windows 11, Intel 16 GB (máy Duy Anh) · git `054f300`, không dirty.

| Thuật toán | Tầng | Median ms | p95 ms | Median expanded | Khớp chi phí |
|---|---|---:|---:|---:|---|
| Dijkstra | ngắn (δ<0,2) | 0,212 | 1,224 | 110 | — |
| Dijkstra | trung bình | 1,003 | 4,870 | 597,5 | — |
| Dijkstra | dài (δ≥0,5) | 2,072 | 8,160 | 1.279 | — |
| Dijkstra | tất cả | 0,929 | 5,505 | 578 | — |
| A* | ngắn (δ<0,2) | 0,242 | 1,097 | 41 | 100,0 % |
| A* | trung bình | 0,779 | 5,227 | 202 | 100,0 % |
| A* | dài (δ≥0,5) | 2,001 | 10,120 | 535 | 100,0 % |
| A* | tất cả | 0,763 | 6,290 | 194 | 100,0 % |

Tỉ số theo **từng cặp** rồi mới lấy median (EXPERIMENT_PLAN mục 3.2): `r` = expanded_A* / expanded_Dijkstra, `s` = thời gian Dijkstra / thời gian A* (s > 1 nghĩa là A* nhanh hơn).

| Tầng | Median r | Median s | Số cặp A* chậm hơn (s < 1) |
|---|---:|---:|---:|
| ngắn | 0,376 | 0,91 | 194 / 333 |
| trung bình | 0,348 | 1,22 | 116 / 334 |
| dài | 0,467 | 0,98 | 170 / 333 |
| tất cả | 0,398 | 1,03 | 480 / 1.000 |

**Tính đúng:** 1.000/1.000 cặp A* và Dijkstra cùng chi phí; `reopened = 0` ở mọi truy vấn A* (heuristic consistent trên dữ liệu thật, khớp T22 và T33).

**Kiểm chéo (yêu cầu của T65):** run_id `20261103-crosscheck-demo-minh` · cùng `queries.csv` của run chính thức (`--queries`), cùng tham số · Python 3.14.4, máy Minh · git `6ce33eb`, không dirty.
- 2.000/2.000 dòng (cặp × thuật toán) **trùng chi phí và trùng expanded** với run chính thức; `r` theo tầng giống hệt.
- Thời gian nhanh hơn khoảng 1,9 lần (median theo cặp) nhưng cùng bậc: median tất cả Dijkstra 0,540 ms, A* 0,410 ms; p95 Dijkstra 1,731 ms, A* 2,087 ms.
- `s` theo tầng: ngắn 0,98 · trung bình 1,26 · dài 1,00 · tất cả 1,07; A* chậm hơn ở 444/1.000 cặp.

### Diễn giải

Các nhận xét dưới đây chỉ dựa trên những gì lặp lại ở **cả hai** run; chỗ hai run khác nhau thì ghi là chưa kết luận.

- **A* mở ít node hơn nhiều:** median chỉ bằng khoảng 40% số node Dijkstra mở (r = 0,398), ổn định ở mọi tầng và giống hệt trên hai máy (expanded là số xác định, không phụ thuộc máy).
- **Nhưng thời gian gần như không giảm:** median s chỉ 1,03–1,07, và ở 44–48% số cặp A* còn chậm hơn Dijkstra. Lợi ích rõ chỉ có ở tầng trung bình (s = 1,22–1,26). Giải thích hợp lý (giả thuyết, chưa đo riêng): mỗi lần đẩy một node vào hàng đợi, A* phải tính haversine (lượng giác), đắt hơn nhiều so với phép cộng của Dijkstra; trên đồ thị 1.889 node, mỗi truy vấn chỉ khoảng 1 ms, nên chi phí này ăn gần hết phần tiết kiệm từ việc mở ít node.
- **Đuôi chậm của A* là thật:** p95 của A* cao hơn Dijkstra ở cả hai run (6,29 so với 5,51 ms; 2,09 so với 1,73 ms), rõ nhất ở tầng dài (10,12 so với 8,16 ms).
- **Chưa kết luận:** median s của tầng ngắn và tầng dài dao động quanh 1 (0,91–1,00) giữa các run. Ở mức khoảng 0,1 ms mỗi truy vấn, sai số đo đủ để đổi chiều, nên không nói A* nhanh hay chậm hơn ở hai tầng này.
- **Trường hợp A* không có lợi:** (1) truy vấn trên vùng nhỏ, nơi chi phí tính heuristic lớn hơn phần tiết kiệm; (2) khi không có đường đi, A* vẫn phải duyệt hết vùng tới được như Dijkstra nên không còn lợi thế (kiểm ở E4 khi có run kịch bản đóng đường, T63).

**Còn thiếu:** E3 (tăng quy mô, chờ T62 chạy trên 4 vùng của T61), E4 (ùn tắc và đóng đường, chờ T63), E5 (tour, T74).

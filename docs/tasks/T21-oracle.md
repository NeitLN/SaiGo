# T21 — Đối chứng NetworkX trên đồ thị ngẫu nhiên

**Trạng thái: ✅ Duy Anh làm xong chiều 26/10 ([#64](https://github.com/NeitLN/SaiGo/pull/64))**; Bảo không cần dùng giờ dự phòng cho task này.

Tuần mục tiêu: 2 **nếu còn dự phòng**, không thì 3 · Giao cho: Bảo (dùng 3 giờ dự phòng) · Nhánh: `t21-oracle` · Issue: [#10](https://github.com/NeitLN/SaiGo/issues/10)
Review: Tiến · Người tích hợp: Tiến
Phụ thuộc: T20 (**bắt đầu**: đã merge) · T15 (**bắt đầu**: MW đã đạt) · Ước lượng: 3 giờ
**Chỉ bắt đầu khi:** MW đã đạt ở mốc 29/10 **và** T20 đã merge. Không thì dời sang tuần 3, giữ 3 giờ dự phòng để sửa lỗi.

## Mục tiêu
Có bằng chứng thực nghiệm rằng Dijkstra và A* đúng trên nhiều đồ thị, không chỉ trên fixture.

## Việc cần làm
1. **`tests/helpers/random_graph.py`:** `make_random_graph(seed, n_nodes, n_edges) -> (Graph, GraphMeta)`.
   - Node rải ngẫu nhiên trong vùng 2 km × 2 km quanh Bến Thành.
   - Cạnh có hướng, `length_m = haversine × hệ số ngẫu nhiên trong [1; 1,5]`, nên luôn ≥ khoảng cách thẳng.
   - Có ít nhất một cặp cạnh song song và một node không tới được.
2. **`tests/test_oracle_networkx.py`:**
   - 20 đồ thị (seed 0–19) × 50 cặp; so `cost_s` của Dijkstra và A* với `nx.dijkstra_path_length` trên `MultiDiGraph` cùng trọng số;
   - `no_path` phải trùng với `nx.NetworkXNoPath`;
   - tuyến hợp lệ: các cạnh nối tiếp nhau, đúng chiều, tổng trọng số bằng `cost_s`.

## Sở hữu (chỉ task này được tạo/sửa)
- `tests/helpers/random_graph.py`
- `tests/test_oracle_networkx.py`

## Tiêu chí chấp nhận
- [ ] 1.000 truy vấn khớp với sai số `1e-9 · max(1, cost)`
- [ ] Chạy dưới 30 giây trong CI
- [ ] `pytest tests/test_oracle_networkx.py -q` → PASS

## Kiến thức cần giải thích được
Vì sao so **chi phí** chứ không so dãy node (có thể có nhiều tuyến cùng chi phí); vì sao test không phải là chứng minh.

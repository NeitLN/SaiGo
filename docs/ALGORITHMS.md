# Thuật toán

Chạy tay Dijkstra và A* trên đồ thị mẫu, rồi tóm tắt từng thuật toán đã cài trong `backend/app/algorithms/`: ý tưởng, điều kiện đúng, độ phức tạp, nơi đo. Gồm cả ba phần mở rộng ngoài proposal (D17): Dijkstra hai chiều, ALT, Or-opt.
Đặc tả gốc: [TOPIC.md](TOPIC.md) mục 9–10; mô hình chi phí và điều kiện heuristic: [DATA_MODEL.md](DATA_MODEL.md) mục 5–6. Số đo: [EXPERIMENTS.md](EXPERIMENTS.md).

## Chạy tay trên đồ thị mẫu

Đồ thị 6 node ở [DATA_MODEL.md](DATA_MODEL.md) mục 7, tính trên mặt phẳng mét. Đáp án ghi ở [`tests/fixtures/mini_expected.json`](../tests/fixtures/mini_expected.json).

Quy ước (theo DATA_MODEL mục 6.3):

- Heap chứa `(priority, counter, node)`; hai entry cùng priority thì entry push trước ra trước. Cột "Heap sau bước" viết `(priority, node)` theo thứ tự pop.
- Giả định cạnh ra của S theo thứ tự S→A, S→B, S→C, S→D (thứ tự trong bảng cạnh ở mục 7). Thứ tự này chỉ quyết định C hay D ra trước; số node mở rộng không đổi.
- Lazy deletion: entry có `g` lớn hơn `g[node]` hiện tại bị bỏ qua trước khi kiểm tra đích.
- Dừng khi **pop** đích. `expanded` = số lần pop entry hợp lệ rồi duyệt cạnh ra, không tính lần pop đích.
- Ùn tắc: cạnh khớp luật khi trung điểm nằm trong vùng (khoảng cách ≤ bán kính); trọng số = thời gian cơ sở × α.

Trong cả 6 tình huống không có entry lỗi thời: không node nào được push hai lần, vì mỗi lần tìm được `g` mới cho một node thì node đó chưa có `g` nào trước đó. Cột "Bỏ qua vì lỗi thời?" vì vậy luôn là "không".

### Dijkstra — 1. Cơ sở, S → T

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0 | (0, S) |
| 1 | (S, 0) | không | S→A, S→B, S→C, S→D | g[A] = 40, g[B] = 50, g[C] = 30, g[D] = 30 | (30, C) (30, D) (40, A) (50, B) |
| 2 | (C, 30) | không | — (ngõ cụt) | — | (30, D) (40, A) (50, B) |
| 3 | (D, 30) | không | — (ngõ cụt) | — | (40, A) (50, B) |
| 4 | (A, 40) | không | A→T | g[T] = 80 | (50, B) (80, T) |
| 5 | (B, 50) | không | B→T: 100 ≥ 80 · B→S: 100 ≥ 0 | — | (80, T) |
| 6 | (T, 80) | không | đích → dừng | — | — |

Kết quả: S→A→T, **80 s**, `expanded` = 5 (S, C, D, A, B). C và D bị pop trước A vì `g` của chúng (30) nhỏ hơn, dù chúng nằm ngược hướng đích: Dijkstra chỉ nhìn `g`.

### Dijkstra — 2. Cơ sở, T → S

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[T] = 0 | (0, T) |
| 1 | (T, 0) | không | T→B | g[B] = 50 | (50, B) |
| 2 | (B, 50) | không | B→T: 100 ≥ 0 · B→S | g[S] = 100 | (100, S) |
| 3 | (S, 100) | không | đích → dừng | — | — |

Kết quả: T→B→S, **100 s**, `expanded` = 2. Không có cạnh T→A (A→T một chiều), nên chiều về phải vòng qua B.

### Dijkstra — 3. Ùn tắc vòng tròn tâm A, r = 220 m, α = 2

Khoảng cách từ trung điểm từng cạnh tới A (400, 0):

| Cạnh | Trung điểm | Khoảng cách tới A (m) | Khớp? | Trọng số (s) |
|---|---|---:|---|---:|
| S→A | (200, 0) | 200 | có | 80 |
| A→T | (600, 0) | 200 | có | 80 |
| S→B, B→S | (200, 150) | 250 | không | 50 |
| B→T, T→B | (600, 150) | 250 | không | 50 |
| S→C | (−150, 0) | 550 | không | 30 |
| S→D | (0, −150) | ≈ 427,2 | không | 30 |

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0 | (0, S) |
| 1 | (S, 0) | không | S→A, S→B, S→C, S→D | g[A] = 80, g[B] = 50, g[C] = 30, g[D] = 30 | (30, C) (30, D) (50, B) (80, A) |
| 2 | (C, 30) | không | — | — | (30, D) (50, B) (80, A) |
| 3 | (D, 30) | không | — | — | (50, B) (80, A) |
| 4 | (B, 50) | không | B→T · B→S: 100 ≥ 0 | g[T] = 100 | (80, A) (100, T) |
| 5 | (A, 80) | không | A→T: 160 ≥ 100 | — | (100, T) |
| 6 | (T, 100) | không | đích → dừng | — | — |

Kết quả: S→B→T, **100 s**, `expanded` = 5 (S, C, D, B, A).

### Dijkstra — 4. Ùn tắc đều α = 2 cho mọi cạnh

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0 | (0, S) |
| 1 | (S, 0) | không | S→A, S→B, S→C, S→D | g[A] = 80, g[B] = 100, g[C] = 60, g[D] = 60 | (60, C) (60, D) (80, A) (100, B) |
| 2 | (C, 60) | không | — | — | (60, D) (80, A) (100, B) |
| 3 | (D, 60) | không | — | — | (80, A) (100, B) |
| 4 | (A, 80) | không | A→T | g[T] = 160 | (100, B) (160, T) |
| 5 | (B, 100) | không | B→T: 200 ≥ 160 · B→S: 200 ≥ 0 | — | (160, T) |
| 6 | (T, 160) | không | đích → dừng | — | — |

Kết quả: S→A→T (không đổi), **160 s** = 2 × 80, `expanded` = 5. Mọi tuyến cùng nhân 2 nên thứ tự giữa các tuyến không đổi.

### Dijkstra — 5. Đóng A→T

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0 | (0, S) |
| 1 | (S, 0) | không | S→A, S→B, S→C, S→D | g[A] = 40, g[B] = 50, g[C] = 30, g[D] = 30 | (30, C) (30, D) (40, A) (50, B) |
| 2 | (C, 30) | không | — | — | (30, D) (40, A) (50, B) |
| 3 | (D, 30) | không | — | — | (40, A) (50, B) |
| 4 | (A, 40) | không | A→T bị đóng, không duyệt | — | (50, B) |
| 5 | (B, 50) | không | B→T · B→S: 100 ≥ 0 | g[T] = 100 | (100, T) |
| 6 | (T, 100) | không | đích → dừng | — | — |

Kết quả: S→B→T, **100 s**, `expanded` = 5.

### Dijkstra — 6. Đóng A→T và B→T

| Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0 | (0, S) |
| 1 | (S, 0) | không | S→A, S→B, S→C, S→D | g[A] = 40, g[B] = 50, g[C] = 30, g[D] = 30 | (30, C) (30, D) (40, A) (50, B) |
| 2 | (C, 30) | không | — | — | (30, D) (40, A) (50, B) |
| 3 | (D, 30) | không | — | — | (40, A) (50, B) |
| 4 | (A, 40) | không | A→T bị đóng | — | (50, B) |
| 5 | (B, 50) | không | B→T bị đóng · B→S: 100 ≥ 0 | — | rỗng |

Heap rỗng mà chưa pop T → **`no_path`**, `expanded` = 5 (mọi node đi tới được từ S).

### A*: giá trị heuristic

`h(n)` = khoảng cách thẳng từ n tới đích / 10 m/s. Với đích T (800, 0):

| Node | Tọa độ | Khoảng cách tới T (m) | h (s) |
|---|---|---:|---:|
| S | (0, 0) | 800 | 80 |
| A | (400, 0) | 400 | 40 |
| B | (400, 300) | 500 | 50 |
| C | (−300, 0) | 1100 | 110 |
| D | (0, −300) | √730000 ≈ 854,4 | 85,44 |
| T | (800, 0) | 0 | 0 |

Với đích S (tình huống T → S): h(T) = 80, h(B) = 50, h(S) = 0.

Ùn tắc và đóng đường không đổi `h`: `h` dùng `v_max` cơ sở (DATA_MODEL mục 5.3).

Fixture `mini.json` dùng lat/lon và haversine nên `h` lệch rất ít so với bảng này. Ở các bước có hai `f` gần nhau, chênh lệch nhỏ nhất là 4,56 s (D 145,44 so với B 150 ở tình huống 4), lớn hơn nhiều so với độ lệch đó, nên thứ tự pop không đổi.

### A* — 1. Cơ sở, S → T

Heap sắp theo `f = g + h`. Cột "Heap sau bước" viết `(f, node)`.

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0, h = 80, f = 80 | (80, S) |
| 1 | (S, 0, 80) | không | S→A, S→B, S→C, S→D | A: 40 + 40 = 80 · B: 50 + 50 = 100 · C: 30 + 110 = 140 · D: 30 + 85,44 = 115,44 | (80, A) (100, B) (115,44, D) (140, C) |
| 2 | (A, 40, 80) | không | A→T | T: 80 + 0 = 80 | (80, T) (100, B) (115,44, D) (140, C) |
| 3 | (T, 80, 80) | không | đích → dừng | — | — |

Kết quả: S→A→T, **80 s**, `expanded` = 2 (S, A). A* không pop C và D vì `f(C) = 140` và `f(D) = 115,44` đều lớn hơn chi phí tối ưu 80; khi T được pop với f = 80 thì thuật toán đã dừng.

### A* — 2. Cơ sở, T → S

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[T] = 0, h = 80, f = 80 | (80, T) |
| 1 | (T, 0, 80) | không | T→B | B: 50 + 50 = 100 | (100, B) |
| 2 | (B, 50, 100) | không | B→T: 100 ≥ 0 · B→S | S: 100 + 0 = 100 | (100, S) |
| 3 | (S, 100, 100) | không | đích → dừng | — | — |

Kết quả: T→B→S, **100 s**, `expanded` = 2.

### A* — 3. Ùn tắc vòng tròn tâm A

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0, f = 80 | (80, S) |
| 1 | (S, 0, 80) | không | S→A, S→B, S→C, S→D | A: 80 + 40 = 120 · B: 50 + 50 = 100 · C: 30 + 110 = 140 · D: 30 + 85,44 = 115,44 | (100, B) (115,44, D) (120, A) (140, C) |
| 2 | (B, 50, 100) | không | B→T · B→S: 100 ≥ 0 | T: 100 + 0 = 100 | (100, T) (115,44, D) (120, A) (140, C) |
| 3 | (T, 100, 100) | không | đích → dừng | — | — |

Kết quả: S→B→T, **100 s**, `expanded` = 2 (S, B).

### A* — 4. Ùn tắc đều α = 2

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0, f = 80 | (80, S) |
| 1 | (S, 0, 80) | không | S→A, S→B, S→C, S→D | A: 80 + 40 = 120 · B: 100 + 50 = 150 · C: 60 + 110 = 170 · D: 60 + 85,44 = 145,44 | (120, A) (145,44, D) (150, B) (170, C) |
| 2 | (A, 80, 120) | không | A→T | T: 160 + 0 = 160 | (145,44, D) (150, B) (160, T) (170, C) |
| 3 | (D, 60, 145,44) | không | — (ngõ cụt) | — | (150, B) (160, T) (170, C) |
| 4 | (B, 100, 150) | không | B→T: 200 ≥ 160 · B→S: 200 ≥ 0 | — | (160, T) (170, C) |
| 5 | (T, 160, 160) | không | đích → dừng | — | — |

Kết quả: S→A→T, **160 s**, `expanded` = 4 (S, A, D, B), so với 2 ở trạng thái cơ sở. Chi phí thật tăng gấp đôi nhưng `h` giữ nguyên, nên cận dưới lỏng hơn và A* phải mở thêm D, B. Đây là ví dụ nhỏ cho giả thuyết ở DATA_MODEL mục 5.3. Bảng ở DATA_MODEL mục 7 để trống ô này.

### A* — 5. Đóng A→T

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0, f = 80 | (80, S) |
| 1 | (S, 0, 80) | không | S→A, S→B, S→C, S→D | A: 80 · B: 100 · C: 140 · D: 115,44 | (80, A) (100, B) (115,44, D) (140, C) |
| 2 | (A, 40, 80) | không | A→T bị đóng | — | (100, B) (115,44, D) (140, C) |
| 3 | (B, 50, 100) | không | B→T · B→S: 100 ≥ 0 | T: 100 + 0 = 100 | (100, T) (115,44, D) (140, C) |
| 4 | (T, 100, 100) | không | đích → dừng | — | — |

Kết quả: S→B→T, **100 s**, `expanded` = 3 (S, A, B).

### A* — 6. Đóng A→T và B→T

| Bước | Pop (node, g, f) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g, h, f | Heap sau bước |
|---|---|---|---|---|---|
| 0 | — | — | — | g[S] = 0, f = 80 | (80, S) |
| 1 | (S, 0, 80) | không | S→A, S→B, S→C, S→D | A: 80 · B: 100 · C: 140 · D: 115,44 | (80, A) (100, B) (115,44, D) (140, C) |
| 2 | (A, 40, 80) | không | A→T bị đóng | — | (100, B) (115,44, D) (140, C) |
| 3 | (B, 50, 100) | không | B→T bị đóng · B→S: 100 ≥ 0 | — | (115,44, D) (140, C) |
| 4 | (D, 30, 115,44) | không | — | — | (140, C) |
| 5 | (C, 30, 140) | không | — | — | rỗng |

Kết quả: **`no_path`**, `expanded` = 5. Khi không có đường, A* cũng phải duyệt hết mọi node đi tới được, giống Dijkstra.

### Tổng hợp

| # | Tình huống | Tuyến | Chi phí | Dijkstra `expanded` | A* `expanded` |
|---|---|---|---:|---:|---:|
| 1 | Cơ sở, S → T | S→A→T | 80 s | 5 | 2 |
| 2 | Cơ sở, T → S | T→B→S | 100 s | 2 | 2 |
| 3 | Ùn tắc tâm A, r = 220 m, α = 2 | S→B→T | 100 s | 5 | 2 |
| 4 | Ùn tắc đều α = 2 | S→A→T | 160 s | 5 | 4 |
| 5 | Đóng A→T | S→B→T | 100 s | 5 | 3 |
| 6 | Đóng A→T và B→T | — | `no_path` | 5 | 5 |

Đối chiếu với DATA_MODEL mục 7: chi phí, tuyến và số node mở rộng khớp ở mọi ô bảng đó đã điền. Bốn ô bảng đó để trống được điền thêm ở đây: tình huống 2 (Dijkstra 2, A* 2) và tình huống 4 (Dijkstra 5, A* 4).

## Thuật toán đã cài

Mọi thuật toán tìm đường chạy trên **snapshot** (trọng số cạnh = thời gian cơ sở × α của kịch bản, cạnh đóng = vô cực) và trả cùng kiểu `SearchResult` với cùng bộ đếm (`expanded`, `pushes`, `relaxations`, `max_frontier`, `trace`), nên so được trực tiếp. Đúng = cùng chi phí với Dijkstra; mọi thuật toán đều được kiểm như vậy trên `mini.json`, đồ thị ngẫu nhiên có cạnh song song, và đồ thị demo dưới mọi kịch bản và khi đóng đường.

### Tìm đường: Dijkstra và A* (lõi của proposal)

| | Dijkstra (`dijkstra.py`) | A* (`astar.py`, `heuristics.py`) |
|---|---|---|
| Thứ tự lấy khỏi heap | `g(n)` | `f(n) = g(n) + h(n)`, `h(n) = c · haversine(n, đích) / v_max` |
| Điều kiện đúng | trọng số không âm | `h` admissible; ở đây còn consistent nhờ hệ số `c = geo_scale` (DATA_MODEL mục 5.1–5.2), nên không node nào phải mở lại (`reopened = 0` ở mọi truy vấn E2) |
| Độ phức tạp (heap nhị phân) | O((V + E) log V) | cùng cận trên; lợi chỉ ở số node mở thực tế |
| Kiểm | NetworkX trên 1.000 truy vấn đồ thị ngẫu nhiên, có cả cạnh đóng (`test_oracle_networkx.py`); 200 cặp đồ thị thật | như Dijkstra; thêm: `h ≡ 0` thì A* mở y hệt Dijkstra |
| Số đo | E2, E3, E4 | E2, E3, E4 |

Ùn tắc chỉ nhân chi phí với α ≥ 1 và đóng đường làm chi phí thành vô cực, nên `h` tính trên `v_max` cơ sở vẫn không vượt chi phí thật: A* đúng trên mọi snapshot. Cái giá là `h` lỏng hơn khi ùn tắc (ví dụ A* — 4 ở trên; E4 đo hiệu ứng này trên đồ thị thật).

### Thứ tự giao: NN, 2-opt có hướng, Held–Karp (`tour.py`)

Ma trận chi phí `D[i][j]` là thời gian đi **có hướng** từ điểm i tới điểm j (mỗi hàng là một lần Dijkstra một-nguồn-nhiều-đích), kho là chỉ số 0 cố định ở đầu và cuối. `D` **bất đối xứng** vì đường một chiều.

- **Nearest Neighbor:** từ vị trí hiện tại, chọn điểm chưa giao có `D` nhỏ nhất; hòa thì chọn chỉ số nhỏ hơn. O(n²).
- **2-opt có hướng:** đảo một đoạn điểm giao, nhận nước đầu tiên làm giảm chi phí hơn `1e-9` s, lặp tới khi không còn nước nào. Đảo đoạn còn đảo chiều các chặng bên trong, nên công thức delta của 2-opt đối xứng **sai** ở đây; code tính lại toàn bộ chi phí tour cho mỗi ứng viên: O(n) mỗi ứng viên, O(n³) mỗi vòng quét. Kết quả là cực trị địa phương, không phải tối ưu.
- **`choose_tour`:** lấy phương án rẻ nhất trong {thứ tự nhập, NN, NN + 2-opt}; hòa thì giữ phương án đứng trước, nên không bao giờ trả thứ tự tệ hơn thứ tự nhập.
- **Held–Karp:** quy hoạch động `dp[S][j]` = chi phí nhỏ nhất đi từ kho, thăm đúng tập S, kết thúc ở j. O(2ⁿ · n²) thời gian, O(2ⁿ · n) bộ nhớ; giới hạn 11 điểm kể cả kho. Chỉ dùng làm đối chứng để đo gap (E5) và khi gọi `/api/tour` với `include_optimal`.
- **Tour sau khi đóng đường (R1):** dựng lại ma trận trên snapshot mới, báo song song "giữ thứ tự cũ" (cùng thứ tự, mỗi chặng tìm đường lại) và "sắp lại" (`choose_tour` lại); nếu có chặng không còn đường thì báo điểm không tới được thay vì vẽ tour thiếu điểm. Số đo: E5b.

Số đo: E5 (gap so với Held–Karp, n = 4–10) và E5b.

### Phần mở rộng (D17)

Ba thuật toán dưới đây không có trong proposal. Chúng được thêm để trả lời câu hỏi "tìm từ hai đầu hoặc dùng heuristic mạnh hơn có giúp không" (E2b) và "có thoát được cực trị địa phương của 2-opt không". Cả ba đều gọi được qua API (`algorithms` của `/api/route` nhận `bidijkstra`, `alt`; `/api/tour` nhận `include_or_opt`), nhưng mặc định của API và giao diện không đổi.

#### Dijkstra hai chiều (`bidijkstra.py`)

- **Ý tưởng:** chạy Dijkstra xuôi từ nguồn trên cạnh ra và ngược từ đích trên cạnh vào (đồ thị có hướng nên phía ngược phải dùng `in_edges`). Mỗi bước mở rộng phía có đỉnh heap nhỏ hơn. Mỗi khi quét một cạnh nối hai phía, cập nhật μ = chi phí tuyến tốt nhất đã gặp (`g_f[u] + w(u,v) + g_b[v]`).
- **Điều kiện dừng:** `top_f + top_b ≥ μ`. Với trọng số không âm, mọi tuyến chưa thấy phải dài ít nhất `top_f + top_b`, nên μ đã tối ưu. Tuyến dựng lại từ predecessor hai phía quanh cạnh nối tốt nhất.
- **Bộ đếm:** `expanded` là tổng số node mở ở hai phía; `trace` ghi đúng thứ tự xen kẽ thực tế. `in_edges` dựng một lần cho mỗi đồ thị (như `out_edges` của Dijkstra một chiều) nên so thời gian công bằng.
- **Không dùng heuristic:** giảm số node nhờ tìm từ hai đầu, không nhờ ước lượng.
- **Kiểm:** `tests/test_bidijkstra.py` (mọi cặp `mini.json`, mọi kịch bản và cạnh đóng trên đồ thị demo, đồ thị ngẫu nhiên có cạnh song song, `no_path`, thứ tự `trace`); API cảnh báo nếu chi phí khác Dijkstra.

#### ALT: A* với landmark và bất đẳng thức tam giác (`alt.py`)

- **Tiền xử lý:** chọn k = 8 landmark kiểu "farthest point" trên thành phần liên thông mạnh lớn nhất (điểm đầu do seed 20261113 chọn, nên cùng đồ thị cho cùng bộ landmark). Với mỗi landmark L, chạy Dijkstra xuôi và ngược trên **chi phí cơ sở** để có d(L, v) và d(v, L) cho mọi v: 2k lần Dijkstra, bộ nhớ 8 byte × |V| × 2k. Làm một lần cho mỗi đồ thị, không tính vào thời gian truy vấn. E2b đo: 29,7 ms và 0,24 MB (vùng 2 km); 365,9 ms và 1,30 MB (vùng 4,5 km).
- **Heuristic:** với đích t,
  `h(v) = max(0, max_L [d(L, t) − d(L, v)], max_L [d(v, L) − d(t, L)])`.
  Cả hai vế là chặn dưới của d(v, t) theo bất đẳng thức tam giác trên đồ thị có hướng, nên `h` admissible và consistent với chi phí cơ sở.
- **Vì sao vẫn đúng khi ùn tắc và đóng đường:** snapshot chỉ làm cạnh đắt lên (α ≥ 1, đóng = vô cực), nên khoảng cách cơ sở vẫn là chặn dưới. Consistency cũng giữ: `h(u) ≤ w₀(u,v) + h(v) ≤ w(u,v) + h(v)`. Nếu một kịch bản làm cạnh nào rẻ hơn cơ sở, `ensure_alt_compatible` từ chối truy vấn thay vì trả kết quả sai.
- **Vòng lặp tìm kiếm:** dùng lại đúng `astar`; ALT chỉ khác hàm `h`. Mỗi lần tính `h` tốn O(k).
- **Kiểm:** `tests/test_alt.py` (cùng chi phí với Dijkstra ở mọi cặp `mini.json` và trên đồ thị demo dưới mọi kịch bản và cạnh đóng; `h` không vượt khoảng cách thật, so với NetworkX trên mẫu đồ thị demo; `h` consistent trên mọi cạnh của snapshot; từ chối snapshot có cạnh rẻ hơn cơ sở).
- **Kết quả (E2b):** mở ít node nhất trong bốn thuật toán ở mọi ô, nhưng ở tầng ngắn **chậm hơn** Dijkstra vì mỗi node tốn O(k) để tính `h`. Lợi lớn nhất ở vùng 4,5 km, chuyến dài.

#### Or-opt xen kẽ 2-opt (`tour.py`, `or_opt`)

- **Ý tưởng:** chuyển một đoạn 1–3 điểm giao liên tiếp sang vị trí khác trong tour, thử cả giữ chiều và đảo chiều đoạn. Như 2-opt, nhận nước đầu tiên làm giảm chi phí hơn `1e-9` s và tính lại toàn bộ chi phí (vì ma trận bất đối xứng). Khi Or-opt hết nước thì chạy 2-opt; lặp lại cho tới khi cả hai cùng không cải thiện được, tức tour là cực trị địa phương của cả hai kiểu nước đi.
- **Vì sao thêm:** ở case demo "Kho + 5 điểm giao", NN + 2-opt kẹt ở tour kém tối ưu 43% (tối ưu là tour NN đi ngược chiều); Or-opt tìm được tối ưu ở case này.
- **Kiểm:** `tests/test_tour_or_opt.py`. Trên 200 ma trận ngẫu nhiên bất đối xứng (n = 4–9), kết quả luôn là tour hợp lệ, không đắt hơn NN + 2-opt và không rẻ hơn Held–Karp. Mặc định của `/api/tour` không đổi khi không bật `include_or_opt`.
- **Giới hạn:** chỉ dùng minh họa. Or-opt không nằm trong các phương án đo ở E5, nên không có số đo tổng quát về gap hay thời gian của nó.

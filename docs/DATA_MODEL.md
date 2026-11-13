# SaiGo — Mô hình dữ liệu

Tài liệu này mô tả cấu trúc đồ thị, trọng số, snapshot, heuristic, đầu vào/đầu ra của thuật toán và cách biến dữ liệu OSM thành đồ thị. Nhãn **[Đã chốt] / [Đề xuất] / [Giả định]** theo quy ước ở [PROJECT_BRIEF.md](PROJECT_BRIEF.md).

## 1. Ba lớp dữ liệu

```text
Đồ thị gốc (Graph)            bất biến, nạp 1 lần khi server khởi động
   │  + Kịch bản (Scenario)   luật ùn tắc theo vùng/loại đường
   │  + Danh sách cạnh đóng   do người dùng chọn
   ▼
Snapshot                      mảng trọng số cho đúng 1 request / 1 lần đo
   ▼
Dijkstra / A*  ──►  SearchResult (tuyến, chi phí, số node mở rộng, trace)
```

Nguyên tắc **[Đã chốt]**: thuật toán không bao giờ sửa đồ thị gốc. Mọi thay đổi (ùn tắc, đóng đường) nằm trong snapshot, nên hai request khác nhau không ảnh hưởng nhau.

## 2. Đồ thị gốc

### 2.1. Định dạng file `saigo-graph/1` (JSON) [Đề xuất]

```json
{
  "format": "saigo-graph/1",
  "dataset_id": "hcm-benthanh-r2000-20261025",
  "crs": "EPSG:4326",
  "nodes": [
    {"id": 0, "osmid": 366372345, "lat": 10.77245, "lon": 106.69802}
  ],
  "edges": [
    {
      "id": 0, "u": 0, "v": 1, "key": 0,
      "way_ids": [23456789],
      "highway": "secondary",
      "oneway": true,
      "length_m": 120.4,
      "speed_kmh": 30,
      "geometry": [[106.69802, 10.77245], [106.69890, 10.77301]]
    }
  ]
}
```

| Trường | Ý nghĩa | Quy ước |
|---|---|---|
| `nodes[i].id` | Chỉ số 0..N−1 | Trùng vị trí trong mảng, để tra cứu O(1) |
| `osmid` | ID gốc của OSM | Chỉ để truy vết, thuật toán không dùng |
| `lat`, `lon` | Tọa độ WGS84 | Tên trường rõ ràng; **không** dùng cặp `[a, b]` không tên |
| `in_scc` (tùy chọn) | Node có thuộc thành phần liên thông mạnh lớn nhất không | Do T31 ghi. Thiếu trường này thì `load_graph` coi là `true` (fixture không cần ghi). Node `false` vẫn được vẽ nhưng không dùng làm điểm snap hay điểm benchmark (mục 8.4) **[chờ chốt Q1 ở buổi họp 26/10]** |
| `name` (tùy chọn) | Tên node | Chỉ dùng trong fixture (`S`, `A`, …) để test và CLI gọi theo tên |
| `edges[j].id` | Chỉ số 0..M−1 | Sắp xếp cạnh theo `(u, v, key)` trước khi đánh số, nên ID ổn định với cùng dữ liệu |
| `u → v` | Cạnh **có hướng** | Đường hai chiều = 2 cạnh; đường một chiều = 1 cạnh |
| `key` | Phân biệt cạnh song song cùng `u → v` | Lấy từ OSMnx `(u, v, key)` |
| `way_ids` | Danh sách ID way OSM | Sau khi simplify, một cạnh có thể gộp nhiều way → luôn lưu dạng list |
| `highway` | Loại đường đã chuẩn hóa thành **một** giá trị | Nếu OSM cho list, lấy loại "cao nhất" theo bảng tốc độ |
| `length_m` | Chiều dài theo hình học, mét | Lấy từ OSMnx (tổng các đoạn nhỏ) |
| `speed_kmh` | Tốc độ mô phỏng đã gán | Từ `data/config/speeds.json`, xem mục 3 |
| `geometry` | Polyline `[lon, lat]` (thứ tự GeoJSON) | Chỉ dùng để vẽ và tính trung điểm; thuật toán không đọc |

Kèm theo mỗi file là `manifest.json`: `dataset_id`, ngày tải, vùng tải, vùng cắt, filter, phiên bản OSMnx, số node/cạnh **đo được**, số cạnh một chiều, số cạnh song song, số self-loop, kích thước thành phần liên thông mạnh, `sha256` của file JSON.

### 2.2. Cấu trúc trong bộ nhớ [Đề xuất]

```python
@dataclass(frozen=True)
class Graph:
    dataset_id: str
    node_lat: list[float]        # độ
    node_lon: list[float]
    edge_u: list[int]
    edge_v: list[int]
    edge_length_m: list[float]
    edge_base_time_s: list[float]
    edge_speed_mps: list[float]
    out_edges: list[list[int]]   # out_edges[u] = các edge id đi ra từ u, sắp theo id
    v_max_mps: float             # tốc độ lớn nhất trong các cạnh
    # geometry, highway, way_ids giữ riêng trong GraphMeta, không nằm trong vòng lặp tìm kiếm
```

Vì sao dùng adjacency list theo **edge id** thay vì `dict[node] -> dict[node] -> weight`?

- Giữ được cạnh song song: hai cạnh `u → v` có hai ID khác nhau.
- Đóng đường chính xác: chặn ID `17` không vô tình chặn cạnh song song `18`.
- Predecessor lưu **cạnh**, nên dựng lại tuyến ra đúng danh sách cạnh và tính lại được tổng chi phí.

### 2.3. Kiểm tra khi nạp (raise lỗi nếu sai)

- `0 ≤ u, v < N`; `length_m ≥ 0` và hữu hạn; `speed_kmh > 0` và hữu hạn.
- `edges[j].id == j`, `nodes[i].id == i`.
- Cạnh sắp tăng nghiêm ngặt theo `(u, v, key)` (không có hai cạnh trùng bộ ba này). Sai thì báo lỗi, không tự sắp lại, vì sắp lại sẽ đổi ID cạnh.
- `out_edges` khớp với `edge_u`.

## 3. Trọng số cạnh

### 3.1. Thời gian cơ sở [Đã chốt]

```text
speed_mps(e)   = speed_kmh(e) / 3.6
base_time_s(e) = length_m(e) / speed_mps(e)
```

Ví dụ: 600 m ở 30 km/h → 30/3,6 = 8,33 m/s → 600 / 8,33 = **72 s**.

### 3.2. Bảng tốc độ theo loại đường [Giả định — số mô phỏng, không phải đo thực tế]

| `highway` | km/h | | `highway` | km/h |
|---|---:|---|---|---:|
| `trunk`, `trunk_link` | 40 | | `unclassified` | 25 |
| `primary`, `primary_link` | 35 | | `residential` | 22 |
| `secondary`, `secondary_link` | 30 | | `living_street`, `service` | 15 |
| `tertiary`, `tertiary_link` | 28 | | loại khác / thiếu | 20 |

Ở bản đầu, bỏ qua thẻ `maxspeed` của OSM vì dữ liệu này thưa ở TP.HCM. Bảng lưu ở `data/config/speeds.json`. Khi bảng đổi, `v_max` và mọi kết quả benchmark phải tính lại.

### 3.3. Trọng số theo snapshot

```text
weight_s(e) = base_time_s(e) × multiplier(e)    nếu e không bị đóng
            = bỏ qua (không mở rộng)            nếu e bị đóng
```

## 4. Snapshot: ùn tắc và đóng đường

### 4.1. Kịch bản ùn tắc [Đề xuất]

Một kịch bản là danh sách luật:

```json
{
  "id": "peak-center",
  "label": "Cao điểm mô phỏng — trung tâm",
  "rules": [
    {"zone": {"type": "circle", "lat": 10.7769, "lon": 106.7009, "radius_m": 600},
     "highway": ["primary", "secondary"], "alpha": 2.0},
    {"zone": {"type": "circle", "lat": 10.7725, "lon": 106.6980, "radius_m": 400},
     "alpha": 1.5}
  ]
}
```

Quy tắc áp luật:

1. Mặc định `multiplier(e) = 1`.
2. Cạnh `e` khớp luật nếu **trung điểm dọc theo hình học** của cạnh (điểm ở 50% chiều dài polyline) nằm trong vùng (khoảng cách ≤ `radius_m`, tính cả biên), và `highway` của cạnh nằm trong danh sách loại đường (nếu luật có danh sách đó).
3. `multiplier(e) = max(alpha)` của các luật khớp. Dùng `max` mà không dùng tích, vì hai luật chồng nhau thường mô tả cùng một chỗ tắc; nhân hai hệ số sẽ phóng đại.
4. Bắt buộc `alpha ≥ 1` và hữu hạn. Ràng buộc này giữ heuristic đúng (mục 5).

Giới hạn cần nói rõ: dùng trung điểm thì cả cạnh được tính là tắc hoặc không tắc. Ùn tắc trên một phần cạnh chỉ được xấp xỉ.

**Vì sao không nhân đều cả bản đồ?** Nếu mọi cạnh cùng nhân α thì mọi tuyến cùng nhân α. Thứ tự giữa các tuyến không đổi, nên tuyến tối ưu không đổi, chỉ con số tăng. Ví dụ ở mục 7 minh họa điều này.

### 4.2. Đóng đường [Đề xuất]

- API nhận `blocked_edge_ids: list[int]`, mỗi phần tử là một cạnh **có hướng**.
- UI có hai lựa chọn khi người dùng bấm vào một đoạn:
  - **Đóng một chiều**: chỉ cạnh được bấm.
  - **Đóng đoạn (hai chiều)**: cạnh được bấm và các "cạnh đối" của nó. Cạnh đối là cạnh `v → u` có cùng tập `way_ids` và hình học đảo ngược. Nhóm cạnh đối được tính một lần lúc server khởi động (`closures.reverse_twins`) và trả về trong `edge_twin_ids` của mỗi tuyến (T51); API không tự thêm cạnh đối vào `blocked_edge_ids`.
- Đường có hai làn tách riêng (dual carriageway) trong OSM có thể không có cạnh đối. UI gọi thao tác này là "đóng đoạn", không gọi là "đóng cả con đường".
- Mọi ID cạnh phải tồn tại trong đúng `dataset_id`; ID không hợp lệ → lỗi 422.

### 4.3. Đối tượng Snapshot

```python
@dataclass(frozen=True)
class Snapshot:
    dataset_id: str
    scenario_id: str
    weights: list[float]      # weights[e]; math.inf nếu cạnh bị đóng
    blocked: frozenset[int]
    snapshot_id: str          # hash(dataset_id, scenario_id, sorted(blocked))
```

Xây snapshot tốn O(M) mỗi request. Bản đầu chấp nhận chi phí này, không cache (quyết định D4).

## 5. Heuristic của A*

### 5.1. Công thức [Đã chốt về hướng; hệ số `c` là đề xuất]

```text
h(n) = c · hav(n, t) / v_max
```

- `hav(n, t)`: khoảng cách great-circle (haversine) từ node `n` tới đích `t`, mét. Dùng bán kính Trái Đất R = 6 371 009 m, cùng giá trị OSMnx dùng để tính `length`.
- `v_max`: tốc độ lớn nhất (m/s) trong **các cạnh đã gán tốc độ**, kể cả giá trị mặc định. Với bảng ở mục 3.2: 40 km/h = 11,11 m/s.
- `c = min(1, min_e length_m(e) / hav(u_e, v_e))` trên mọi cạnh có `hav > 0`. Bình thường `length ≥ hav` (đường cong dài hơn dây cung) nên `c = 1`. Nếu dữ liệu có cạnh ngắn hơn khoảng cách thẳng (do làm tròn, lỗi đơn vị, đảo lat/lon), `c < 1` tự động giữ heuristic đúng.

Quy tắc kiểm tra dữ liệu: nếu `c < 0,999` thì **điều tra** các cạnh vi phạm trước khi tiếp tục (thường là lỗi lat/lon hoặc đơn vị). Ghi `c` và số cạnh vi phạm vào manifest.

### 5.2. Vì sao h là cận dưới và consistent (phác thảo chứng minh)

Gọi `w(e) = α(e) · length(e) / speed(e)` với `α ≥ 1` và `speed(e) ≤ v_max`. Khi đó:

1. **Mỗi cạnh:** `w(u,v) ≥ length(u,v) / v_max ≥ c · hav(u,v) / v_max`.
2. **Consistency:** theo bất đẳng thức tam giác trên mặt cầu, `hav(u,t) ≤ hav(u,v) + hav(v,t)`. Nhân hai vế với `c / v_max` rồi dùng (1):
   `h(u) ≤ c·hav(u,v)/v_max + h(v) ≤ w(u,v) + h(v)`.
3. Consistent và `h(t) = 0` thì `h` là admissible (không vượt chi phí thật còn lại). A* với heuristic consistent trả về chi phí tối ưu, và mỗi node được mở rộng tối đa một lần.

Hệ quả cho snapshot: ùn tắc (`α ≥ 1`) và đóng đường chỉ làm chi phí tăng, nên cùng `h` vẫn đúng. Nếu sau này có kịch bản làm đường **nhanh hơn** (α < 1), phải tính lại `v_max`.

Code vẫn cho phép mở lại node nếu tìm được `g` tốt hơn (an toàn). Với heuristic consistent, trường hợp đó không xảy ra; số lần mở lại được đếm để kiểm chứng điều này trên dữ liệu thật.

### 5.3. Heuristic yếu khi có ùn tắc

`h` dùng `v_max` của trạng thái cơ sở. Khi có ùn tắc, chi phí thật tăng nhưng `h` không tăng, nên cận dưới "lỏng" hơn và A* có thể phải mở rộng nhiều node hơn. Đây là **giả thuyết** để đo trong RQ3, không phải kết luận.

## 6. Đầu vào và đầu ra của thuật toán

### 6.1. Chữ ký hàm [Đề xuất]

```python
def dijkstra(graph: Graph, snap: Snapshot, source: int, target: int,
             *, trace_limit: int = 0) -> SearchResult: ...

def astar(graph: Graph, snap: Snapshot, source: int, target: int,
          heuristic: Callable[[int], float], *, trace_limit: int = 0) -> SearchResult: ...
```

`heuristic` được tạo cho từng đích: `make_geo_heuristic(graph, target)`; hệ số `c` mặc định tự tính bằng `geo_scale(graph)` theo mục 5.1. Truyền `lambda n: 0.0` vào `astar` thì kết quả phải giống hệt Dijkstra (dùng làm test).

### 6.2. `SearchResult`

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `status` | `"ok"` \| `"no_path"` | Không bao giờ trả đường thẳng khi `no_path` |
| `cost_s` | float \| None | Tổng `weights` của các cạnh trên tuyến |
| `edge_ids` | list[int] | Tuyến theo cạnh, đúng chiều đi |
| `node_ids` | list[int] | `[source, …, target]` |
| `distance_m` | float \| None | Tổng `length_m` của tuyến |
| `expanded` | int | Số lần pop một entry **hợp lệ** rồi duyệt cạnh ra của nó; **không** tính lần pop đích |
| `unique_expanded` | int | Số node khác nhau đã mở rộng (bằng `expanded` nếu không có mở lại) |
| `reopened` | int | Số lần mở lại node; kỳ vọng 0 với heuristic consistent |
| `relaxations` | int | Số lần cập nhật `g[v]` thành giá trị tốt hơn |
| `pushes`, `max_frontier` | int | Số lần push vào heap; kích thước heap lớn nhất |
| `trace` | list[int] | K node mở rộng đầu tiên (K = `trace_limit`); rỗng khi benchmark |
| `trace_truncated` | bool | `True` nếu K > 0 và số node mở rộng > K. K = 0 nghĩa là tắt trace (benchmark), luôn `False` |

Thời gian chạy **không** nằm trong `SearchResult`: nơi gọi hàm (benchmark hoặc API) tự đo bằng `time.perf_counter_ns()` quanh lời gọi, để mọi thuật toán được đo cùng một cách.

### 6.3. Quy tắc cài đặt [Đã chốt]

- Heap chứa `(priority, counter, node)`. `counter` tăng dần để phá hòa ổn định.
- Lazy deletion: khi pop, bỏ qua entry có `g` lớn hơn `g[node]` hiện tại, **trước** khi kiểm tra đích.
- Dừng khi pop được đích (không dừng khi mới push đích).
- `source == target` → `ok`, chi phí 0, tuyến rỗng, `expanded = 0`.
- Cạnh có `weights[e] == inf` không được duyệt.

## 7. Ví dụ nhỏ để hiểu (đã chạy kiểm tra)

Mặt phẳng tọa độ mét (dữ liệu thật dùng haversine, ý tưởng không đổi). Mọi cạnh cùng tốc độ 36 km/h = 10 m/s, nên `v_max = 10` và `h(n) = khoảng cách thẳng tới T / 10`.

```text
                    B (400, 300)
                  ↗      ↘
                /          ↘
 C ←──── S ─────→ A ─────→ T
(-300,0) (0,0)    (400,0)   (800,0)
         │
         ↓
         D (0, -300)

Chiều về (không vẽ): T → B → S
```

| Cạnh | Dài (m) | Thời gian (s) | Ghi chú |
|---|---:|---:|---|
| S→A | 400 | 40 | |
| A→T | 400 | 40 | Một chiều: không có T→A |
| S→B | 500 | 50 | |
| B→T | 500 | 50 | |
| T→B | 500 | 50 | Chiều về |
| B→S | 500 | 50 | Chiều về |
| S→C | 300 | 30 | Ngõ cụt, ngược hướng đích |
| S→D | 300 | 30 | Ngõ cụt |

Kết quả (đã chạy bằng code thử, khớp NetworkX):

| Tình huống | Tuyến | Chi phí | Dijkstra mở rộng | A* mở rộng |
|---|---|---:|---|---|
| Cơ sở, S → T | S→A→T | 80 s | 5 (S, C, D, A, B) | 2 (S, A) |
| Cơ sở, **T → S** | T→B→S | 100 s | — | — |
| Ùn tắc: vòng tròn tâm A, r = 220 m, α = 2 | S→B→T | 100 s | 5 | 2 (S, B) |
| Ùn tắc đều α = 2 cho **mọi** cạnh | S→A→T (không đổi) | 160 s | | |
| Đóng A→T | S→B→T | 100 s | 5 | 3 (S, A, B) |
| Đóng A→T và B→T | không có | `no_path` | 5 | 5 |

Bốn điều rút ra:

1. **A* vẫn tối ưu:** cùng chi phí với Dijkstra trong mọi dòng.
2. **A* mở rộng ít hơn:** Dijkstra phí công vào C và D (ngược hướng đích). Với A*, `f(C) = 30 + 110 = 140` và `f(D) = 30 + 85,4 = 115,4`, đều lớn hơn chi phí tối ưu 80, nên A* không bao giờ pop C và D.
3. **Đồ thị có hướng:** S→T tốn 80 s nhưng T→S tốn 100 s.
4. **Khi không có đường, A* không tiết kiệm được gì:** cả hai phải duyệt hết các node đi tới được rồi mới kết luận `no_path`.

Ví dụ này sẽ thành fixture `tests/fixtures/mini.json` (task T01; tọa độ đổi sang lat/lon quanh Bến Thành) và là test hồi quy đầu tiên.

## 8. Nguồn dữ liệu và cách chuyển thành đồ thị

### 8.1. Thật hay mô phỏng

| Dữ liệu | Thật hay mô phỏng | Nguồn |
|---|---|---|
| Hình học đường, giao lộ, chiều đường một chiều, loại đường, ID way | **Thật** (snapshot OSM tại ngày tải) | OpenStreetMap qua OSMnx, © OpenStreetMap contributors, ODbL |
| Chiều dài cạnh | **Thật** (tính từ hình học) | OSMnx |
| Tốc độ từng loại đường | **Mô phỏng** | `data/config/speeds.json` |
| Ùn tắc / cao điểm | **Mô phỏng** | `data/config/scenarios.json` |
| Đóng đường | **Mô phỏng**, do người dùng chọn | Request API |
| Cặp truy vấn benchmark, case demo | **Sinh có seed** | `scripts/run_benchmarks.py`, `data/demo/cases.json` |

Trên giao diện và trong essay luôn gọi là "thời gian di chuyển ước tính theo kịch bản", không gọi là "giao thông thực".

### 8.2. Pipeline `scripts/prepare_data.py` [Đề xuất]

1. Đọc `data/config/areas.json`: tâm (Bến Thành), nửa cạnh vùng tải, đệm.
2. `ox.graph_from_bbox(..., network_type="drive", simplify=True, retain_all=True)`. Bước này chỉ chạy **một lần**; lưu GraphML gốc vào `data/raw/` (đã có trong `.gitignore`).
3. Chuẩn hóa thuộc tính: `osmid`/`highway` dạng list → `way_ids` (list) và một `highway`; gán `speed_kmh` theo bảng.
4. Cắt vùng (cho vùng demo và các kích thước của thí nghiệm tăng quy mô): giữ node nằm trong hình vuông, tính bằng mét trên hệ chiếu; giữ cạnh có **cả hai** đầu bên trong. Hình học của cạnh có thể ló ra ngoài một chút; ghi quy ước này vào báo cáo.
5. Lọc thành phần liên thông mạnh (SCC), xem mục 8.4.
6. Đánh lại ID node 0..N−1 và ID cạnh 0..M−1 (theo `(u, v, key)` gốc), xuất `saigo-graph/1` JSON vào `data/processed/` cùng `manifest.json`.
7. In báo cáo kiểm tra: số node/cạnh, % cạnh một chiều, số cạnh song song, self-loop, kích thước SCC, `c` và số cạnh có `length < hav`.

Ứng dụng demo và benchmark chỉ đọc JSON, không cần OSMnx hay mạng Internet.

**Lưu file ở đâu [Đề xuất]:** không commit JSON lớn vào Git. Commit `manifest.json` (có `sha256`) và đính file JSON vào GitHub Release (hoặc thư mục chung của nhóm); README ghi cách tải và kiểm tra hash. CI chỉ dùng fixture nhỏ trong `tests/fixtures/`.

### 8.3. Đường một chiều

- OSMnx đã xử lý `oneway=yes/-1`: đường một chiều chỉ sinh cạnh theo chiều được đi; đường hai chiều sinh hai cạnh ngược nhau.
- SaiGo **không** chuyển đồ thị sang vô hướng ở bất kỳ bước nào, kể cả trong test.
- Kiểm tra trong T31: chọn 2–3 đường một chiều đã biết ở Quận 1, xác nhận chỉ có cạnh theo đúng chiều. Kết quả ghi vào PROGRESS.md. **[Chưa kiểm chứng]**

### 8.4. Điểm không có kết nối

| Trường hợp | Cách xử lý |
|---|---|
| Node không thuộc SCC lớn nhất (ví dụ đường một chiều cụt ở rìa vùng cắt) | Vẫn giữ trong đồ thị để vẽ, nhưng **không** dùng làm điểm snap hay điểm benchmark. Đếm và ghi vào manifest |
| Người dùng bấm xa mạng đường > 150 m | Từ chối, báo "Điểm quá xa mạng đường" |
| Người dùng bấm ngoài vùng | Từ chối, báo "Ngoài vùng dữ liệu" |
| Sau khi đóng đường, đích không còn tới được | `no_path`; UI báo rõ, không vẽ đường thẳng, giữ tuyến cũ ở dạng mờ với nhãn "kế hoạch trước khi đóng đường" |
| Đóng đường làm tách SCC | Không tính lại SCC theo từng request; đơn giản trả `no_path` cho các cặp bị ảnh hưởng |

OSMnx mặc định chỉ giữ thành phần liên thông **yếu** lớn nhất. Vì vậy pipeline phải tự gọi bước chọn SCC.

Với thí nghiệm tăng quy mô, chọn SCC theo kiểu lồng nhau: lấy SCC lớn nhất của vùng nhỏ nhất, rồi ở mỗi vùng lớn hơn chọn **SCC chứa SCC của vùng nhỏ**. Cách này bảo đảm các cặp "fixed trips" tồn tại ở mọi kích thước.

### 8.5. Ánh xạ điểm (snap) [Đề xuất]

- Snap về **node** gần nhất (haversine) trong SCC. Bản đầu dùng duyệt tuyến tính O(N); nếu chậm thì chia lưới ô 200 m.
- Trả về khoảng cách snap; UI vẽ cả điểm bấm và điểm đã snap khi hai điểm cách nhau > 30 m.
- Snap lên giữa cạnh (tạo node ảo) là mở rộng, chưa làm.

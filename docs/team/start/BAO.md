# Phiếu bắt đầu — Đỗ Quốc Bảo (@dobaovlu)

> **Từ 26/10 phân công đã đổi** (cắt T32; Duy Anh vắng sáng 26/10 rồi quay lại chiều 26/10). Danh sách task dưới đây là của tuần 1; việc hiện tại xem [phiếu giao việc](../../tasks/README.md), [ROADMAP](../../ROADMAP.md) mục 6 và tab Issues.

**Vai trò:** ca kiểm thử tính tay, kịch bản và case demo, kiểm thử thủ công, chạy trên máy thứ hai, biểu đồ, tài liệu.
Làm xong [ONBOARDING.md](../ONBOARDING.md) mục 1–5 trước. Mục 2 (đặt tên git là của bạn) đặc biệt quan trọng.

## Task của bạn theo thứ tự

| Thứ tự | Issue | Task | Dự kiến | Review bởi |
|---|---|---|---|---|
| 1 | [#5](https://github.com/NeitLN/SaiGo/issues/5) | T03 · Bảng kết quả tính tay cho đồ thị mẫu | 23–24/10 | Duy Anh |
| 2 | [#18](https://github.com/NeitLN/SaiGo/issues/18) | T42 · Kịch bản ùn tắc cho demo | 30–31/10 | Tiến |
| 3 | [#24](https://github.com/NeitLN/SaiGo/issues/24) | T55 · Case demo + kiểm thử thủ công | 04/11 | Tiến |
| 4 | [#29](https://github.com/NeitLN/SaiGo/issues/29) | T64 · Vẽ biểu đồ | 04–06/11 | Tiến |
| 5 | [#37](https://github.com/NeitLN/SaiGo/issues/37) | T80 · Đóng băng tính năng + chạy trên máy thứ hai | 10/11 | Tiến |
| 6 | [#39](https://github.com/NeitLN/SaiGo/issues/39) | T82 · Tập demo + video dự phòng (cùng Minh) | 10–12/11 | Tiến |

Thêm: phần của mình trong [#31](https://github.com/NeitLN/SaiGo/issues/31) (T65) và [#40](https://github.com/NeitLN/SaiGo/issues/40) (T83).
Danh sách luôn cập nhật: [issue được giao cho bạn](https://github.com/NeitLN/SaiGo/issues?q=is%3Aopen+assignee%3Adobaovlu).

**Bạn review:** PR đụng `docs/`, `data/demo/`, `tests/fixtures/`, `scripts/plot_results.py` (CODEOWNERS tự gửi yêu cầu). Khi review tài liệu, kiểm tra: lệnh trong tài liệu có chạy được không, link có mở được không, có chỗ nào khó hiểu không.

## Đọc trước

- [DATA_MODEL.md](../../DATA_MODEL.md) mục 7: ví dụ 6 node. Đọc thật kỹ; T03 làm trên chính ví dụ này.
- [TOPIC.md](../../TOPIC.md) mục 9.1: pseudocode Dijkstra.
- [PROJECT_BRIEF.md](../../PROJECT_BRIEF.md) mục 7: kịch bản demo (T42, T55, T82 phục vụ phần này).

## Task đầu tiên: T03 (#5) từng bước

**Mục tiêu:** tự chạy tay Dijkstra và A* trên đồ thị mẫu, ra đáp án độc lập. Code của Duy Anh (T11, T20) phải khớp đáp án này. **Không chép bảng kết quả ở DATA_MODEL mục 7**: tự tính rồi so. Nếu ra khác, báo ngay trong issue #5, vì có thể chính tài liệu sai.

**Branch:** `t03-hand-calc`

1. Với mỗi tình huống, điền một bảng theo mẫu (mỗi dòng là một lần lấy phần tử nhỏ nhất ra khỏi heap):

   | Bước | Pop (node, g) | Bỏ qua vì lỗi thời? | Cạnh được xét | Cập nhật g | Heap sau bước |
   |---|---|---|---|---|---|
   | 0 | — | — | — | g[S] = 0 | (0, S) |
   | 1 | (S, 0) | không | S→A, S→B, S→C, S→D | … | … |

   Với A* thêm cột `h` và `f = g + h`; `h(n)` = khoảng cách thẳng từ n tới T chia 10 (m/s).

2. Sáu tình huống: S→T cơ sở; T→S cơ sở; vùng ùn tắc tâm A bán kính 220 m với α = 2; α = 2 cho mọi cạnh; đóng A→T; đóng A→T và B→T. Với Dijkstra làm cả 6; với A* làm ít nhất tình huống S→T cơ sở.
3. Ghi bảng vào [docs/ALGORITHMS.md](../../ALGORITHMS.md), mục mới "Chạy tay trên đồ thị mẫu".
4. Ghi đáp án vào `tests/fixtures/mini_expected.json` theo khung sau. Thay `?` bằng kết quả bạn tự tính; mỗi tình huống một phần tử trong `cases`.

   ```json
   {
     "graph": "tests/fixtures/mini.json",
     "cases": [
       {
         "name": "co-so-S-T",
         "source": "S", "target": "T",
         "scenario": null,
         "blocked": [],
         "dijkstra": {"status": "ok", "cost_s": "?", "path": ["S", "?", "T"], "expanded": "?"},
         "astar":    {"status": "ok", "cost_s": "?", "path": ["S", "?", "T"], "expanded": "?"}
       }
     ]
   }
   ```

   Quy ước: `expanded` là số node đã pop và duyệt cạnh, **không** tính lần pop đích. Tình huống không có đường thì `"status": "no_path"`, `"cost_s": null`, `"path": []`. Ùn tắc ghi `"scenario": {"circle": {"center": "A", "radius_m": 220}, "alpha": 2}`; α đều ghi `"scenario": {"all": 2}`. Đóng cạnh ghi tên, ví dụ `"blocked": ["A->T"]`.
5. Mở PR `Closes #5`, nhờ Duy Anh review.

**Làm bằng VS Code thay cho lệnh** (xem thêm ONBOARDING mục 6):

1. Góc dưới bên trái bấm tên branch → *Create new branch* → `t03-hand-calc`.
2. Sửa file, lưu. Tab Source Control (Ctrl+Shift+G): bấm **+** cạnh file để stage, gõ message `T03: thêm bảng chạy tay Dijkstra`, bấm **Commit**, rồi **Publish Branch**.
3. Lên GitHub bấm **Compare & pull request**.

## Trong lúc chờ task tiếp theo (25–29/10)

- Đọc trước cho T64: hướng dẫn cơ bản của matplotlib (vẽ line, boxplot, đặt nhãn trục). T64 vẽ từ file CSV kết quả.
- Review các PR tài liệu được giao (đọc kỹ, chạy thử lệnh trong tài liệu).
- Ghi lại mọi chỗ trong ONBOARDING/README làm bạn bị vướng khi cài đặt, rồi mở issue loại *Lỗi*. Đây là bước chuẩn bị cho T80 (chạy trên máy thứ hai).

## Phải giải thích được trước giảng viên

- Từng bước Dijkstra trên ví dụ: vì sao pop C, D trước A; vì sao bỏ qua entry lỗi thời.
- Vì sao A* chỉ cần pop S và A.
- Vì sao S→T tốn 80 s còn T→S tốn 100 s (đường một chiều).
- Mỗi case demo minh họa câu hỏi nghiên cứu nào (PROJECT_BRIEF mục 7).

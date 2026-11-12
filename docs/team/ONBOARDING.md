# Bắt đầu làm việc với SaiGo

Làm lần lượt từ mục 1 đến mục 5 trong buổi đầu tiên (khoảng 1 giờ). Sau đó mở phiếu của mình:

| Người | Phiếu bắt đầu |
|---|---|
| Võ Việt Tiến | [start/TIEN.md](start/TIEN.md) |
| Bùi Duy Anh | [start/DUY_ANH.md](start/DUY_ANH.md) |
| Võ Hoàng Minh | [start/MINH.md](start/MINH.md) |
| Đỗ Quốc Bảo | [start/BAO.md](start/BAO.md) |

## 1. Cài công cụ (một lần)

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Git | mới nhất | https://git-scm.com/download/win |
| Python | **3.11.9**, đúng bản này | [Bộ cài Windows 64-bit](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe). Khi cài, tick "Add python.exe to PATH". Trang python.org để bản mới hơn (3.13–3.15) ở đầu; bản đó vẫn chạy được nhưng không dùng file khóa phiên bản, nên số liệu benchmark phải chạy trên 3.11 |
| Node.js | **20** trở lên (LTS) | https://nodejs.org |
| VS Code | mới nhất | Extension gợi ý: Python, Pylance, GitLens |
| GitHub CLI `gh` | tùy chọn | Mở PR, xem issue bằng lệnh; không bắt buộc |

Kiểm tra trong PowerShell:

```powershell
git --version; python --version; node --version
```

## 2. Đặt tên git là **của chính bạn**

Commit mang tên ai thì GitHub và giảng viên ghi công cho người đó. Email phải là email đã thêm vào tài khoản GitHub của bạn (GitHub → Settings → Emails), nếu không commit sẽ không gắn với tài khoản.

```powershell
git config --global user.name "Họ Tên Của Bạn"
git config --global user.email "email-da-them-vao-github@example.com"
git config --global user.name; git config --global user.email   # kiểm tra lại
```

Không dùng máy hoặc tài khoản của người khác để commit giúp. Nếu phải làm chung một máy, mỗi người đặt lại tên/email trước khi commit.

## 3. Clone repo và dựng môi trường

Nên clone vào thư mục **không dấu, không khoảng trắng**, ví dụ `C:\dev`. Đường dẫn có dấu tiếng Việt làm hỏng `pip install -e` và có thể làm hỏng thư viện địa lý.

```powershell
mkdir C:\dev -Force; cd C:\dev
git clone https://github.com/NeitLN/SaiGGo.git
cd SaiGGo
powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1
```

Script kiểm tra công cụ và tên git, tạo `.venv`, cài thư viện, chạy test, build frontend. Kết thúc đúng là dòng `==> Xong`. Minh thêm `-Data` để cài OSMnx.

Chạy app (2 cửa sổ PowerShell):

```powershell
# Cửa sổ 1 — backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --app-dir backend

# Cửa sổ 2 — frontend
cd frontend; npm run dev
```

Mở http://localhost:5173. Góc phải trên phải hiện "Server sẵn sàng · dataset mini" (backend mặc định nạp `tests/fixtures/mini.json`). Kiểm tra nhanh: bấm gần node S (khoảng 200 m bên trái tâm bản đồ lúc mới mở) rồi gần node T (khoảng 580 m bên phải tâm, gần mép phải bản đồ, cùng hàng ngang), bấm **Tìm đường** → bảng kết quả ghi "Thời gian di chuyển ước tính (theo kịch bản)" 80,0 s cho cả Dijkstra và A*, "Chi phí trùng khớp: có" (hai tuyến trùng nhau nên vẽ thành một nét); bấm **Đảo chiều** → 100,0 s. Nền bản đồ lấy tile từ `tile.openstreetmap.org`, mạng chặn trang này thì nền xám nhưng tuyến vẫn vẽ đúng.

Lỗi thường gặp:

| Lỗi | Cách sửa |
|---|---|
| `running scripts is disabled on this system` khi Activate | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (một lần) |
| `python` mở Microsoft Store | Cài Python từ python.org, tắt "App execution aliases" cho python trong Settings |
| `ModuleNotFoundError: app` khi chạy CLI | Chạy từ thư mục gốc với `$env:PYTHONPATH="backend"` |

## 4. Đọc trước (khoảng 20 phút)

1. [PROJECT_BRIEF.md](../PROJECT_BRIEF.md) mục 1–3: dự án làm gì, phạm vi.
2. [CONTRIBUTING.md](../../CONTRIBUTING.md): quy trình branch → PR → review. **Bắt buộc.**
3. [DATA_MODEL.md](../DATA_MODEL.md) mục 7: ví dụ 6 node. Ai cũng phải hiểu ví dụ này.
4. Phần "Đọc trước" trong phiếu của mình.

## 5. Nhận việc trên GitHub

1. Mở [Project](https://github.com/users/NeitLN/projects/3) → lọc theo tên mình (Assignees).
2. Mở issue task đầu tiên trong phiếu, bình luận ngắn để xác nhận, ví dụ "Mình nhận task này, dự kiến xong tối 24/10". Có câu hỏi về task thì cũng hỏi bằng bình luận.
3. Khi bắt đầu làm: chuyển Status của issue trên Project sang **In Progress**.

## 6. Quy trình một task bằng lệnh

Ví dụ với task T11 (issue #7).

```powershell
git switch main
git pull                                   # luôn bắt đầu từ main mới nhất
git switch -c t11-dijkstra                 # branch: <mã task>-<mô tả ngắn>

# ... sửa code ...
.venv\Scripts\python.exe -m pytest -q      # test phải xanh trước khi push

git add backend/app/algorithms/dijkstra.py tests/test_dijkstra.py
git commit -m "T11: thêm Dijkstra với lazy deletion"
git push -u origin t11-dijkstra            # lần đầu; các lần sau chỉ cần git push
```

Sau khi push, GitHub hiện nút **Compare & pull request**:

1. Bấm nút, kiểm tra *base: main* ← *compare: t11-dijkstra*.
2. Điền template; dòng đầu là `Closes #7`.
3. Bấm **Create pull request**. GitHub tự yêu cầu review; chuyển Status sang **In Review**.
4. Reviewer yêu cầu sửa: sửa trên cùng branch, commit, `git push`. PR tự cập nhật.
5. Có approve và CI xanh: bấm **Squash and merge**, rồi **Delete branch**.
6. Về máy: `git switch main; git pull`.

Dùng VS Code thay cho lệnh: tab **Source Control** (Ctrl+Shift+G) có nút commit/push; góc dưới bên trái để đổi branch.

Lỗi thường gặp:

| Thông báo | Nghĩa | Cách xử lý |
|---|---|---|
| `protected branch hook declined` | Đang push thẳng lên `main` | Tạo branch (`git switch -c ...`) rồi push branch đó |
| PR báo *This branch is out-of-date* hoặc conflict | `main` đã có thay đổi mới | `git switch main; git pull; git switch <branch>; git merge main`, sửa conflict, commit, push |
| CI đỏ | Test hoặc build lỗi | Bấm **Details** xem log, sửa, push lại |
| Nút merge xám | Chưa có approve, hoặc người approve là người push commit cuối | Nhờ một người khác review |

## 7. Review PR của người khác

Khi được yêu cầu review (thông báo GitHub hoặc tab Pull requests → *Review requests*):

1. Tab **Files changed**: đọc từng file; bấm dấu **+** cạnh dòng để bình luận cụ thể.
2. Đối chiếu với mục "Hoàn thành khi" và "Kiểm tra" trong issue liên kết.
3. Nếu chạy nhanh: `git fetch; git switch <branch của PR>; .venv\Scripts\python.exe -m pytest -q`.
4. **Review changes** → *Approve* hoặc *Request changes*, kèm 2–3 nhận xét cụ thể. Không chỉ ghi "LGTM".
5. Trả lời trong 24 giờ; bận thì báo nhóm để đổi người.

## 8. Mỗi ngày làm việc

- Bắt đầu: `git switch main; git pull`, xem Project.
- Có tiến độ hoặc vướng mắc: bình luận vào issue. Bị chặn quá nửa ngày: gắn nhãn `blocked` và nhắc người liên quan.
- Kết thúc task: cập nhật [PROGRESS.md](../PROGRESS.md) trong cùng PR (trạng thái, lệnh đã chạy, kết quả, lỗi còn lại).
- Họp tuần: tạo issue từ template **Biên bản họp**. Buổi đầu theo [KICKOFF.md](KICKOFF.md).

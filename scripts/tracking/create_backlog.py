"""Tạo/cập nhật backlog GitHub (labels, milestones, issues) từ docs/TASKS.md.

Nguồn dữ liệu:
- docs/TASKS.md: nội dung, người phụ trách, ước lượng giờ, phụ thuộc của từng task.
- docs/tracking/schedule.csv: mốc, ngày bắt đầu/hạn, nhóm, loại, ưu tiên.

Cách dùng (cần `gh` đã đăng nhập):
    python scripts/tracking/create_backlog.py --dry-run   # chỉ in kết quả phân tích
    python scripts/tracking/create_backlog.py --create    # chỉ tạo task còn thiếu; không sửa issue đã có
    python scripts/tracking/create_backlog.py --sync      # cập nhật mọi issue theo TASKS.md

Issue được nhận diện qua mục "Mã task" trong nội dung, không qua tiêu đề hay nhãn.
--sync giữ checkbox đã tick và các nhãn không do script quản lý (blocked, bug, …),
đồng thời thêm/bỏ quan hệ "blocked by" cho khớp TASKS.md.
Script không đổi trạng thái mở/đóng của issue.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "NeitLN/SaiGGo"
TASKS_URL = f"https://github.com/{REPO}/blob/main/docs/TASKS.md"

PEOPLE = {
    "Tiến": "NeitLN",
    "Duy Anh": "anh7032",
    "Minh": "Jayson135724",
    "Bảo": "dobaovlu",
}

# Tiêu đề là khóa để tìm milestone đã có (ensure_milestones): đổi tiêu đề sẽ tạo milestone mới.
# Mô tả và hạn cập nhật theo kế hoạch đã duyệt 26/10 (docs/proposals/2026-10-26-pham-vi.md).
MILESTONES = {
    "M0": ("M0 — Nền móng", "2026-10-24",
           "Khung chạy trên Windows; fixture mini.json nạp được; OSMnx tải được vùng nhỏ. "
           "Chứng minh: pytest -q xanh; python scripts/prepare_data.py --smoke"),
    "M1": ("M1 — Dijkstra trên đồ thị mẫu", "2026-10-31",
           "Dijkstra khớp bảng tính tay trên mini.json; CLI chạy được cả Dijkstra và A* (T12). "
           "Chứng minh: python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo both"),
    "MW": ("MW — Walking skeleton", "2026-10-29",
           "Bấm 2 điểm trên bản đồ → /api/route → Dijkstra trên mini.json → vẽ tuyến; chạy được trên máy thứ hai. "
           "Chứng minh: pytest tests/test_api_route.py; thao tác ✅ của T14 và T15"),
    "M2": ("M2 — A* và đối chứng", "2026-11-03",
           "A* cùng chi phí, ít node hơn; test ngẫu nhiên khớp NetworkX; kiểm heuristic trên dữ liệu thật (T22). "
           "Chứng minh: pytest tests/test_astar.py tests/test_oracle_networkx.py"),
    "M3": ("M3 — Dữ liệu thật trên bản đồ", "2026-10-28",
           "Từ 26/10: dữ liệu thô đóng băng dùng chung qua Release (T34), JSON vùng demo + manifest (T31). "
           "Không vẽ toàn mạng đường (T32 đã cắt). Chứng minh: hai máy ra cùng sha256; pytest -m realdata"),
    "M4": ("M4 — Tìm đường trên dữ liệu thật", "2026-11-03",
           "Dijkstra/A* trên đồ thị thật; 200 cặp khớp NetworkX. Chứng minh: pytest -m realdata"),
    "M5": ("M5 — Ùn tắc và đóng đường", "2026-11-04",
           "Snapshot với vùng ùn tắc và cạnh đóng; tuyến đổi, no_path khi cần. "
           "Chứng minh: pytest tests/test_scenario.py tests/test_closures.py"),
    "M6": ("M6 — Bản đồ tương tác", "2026-11-07",
           "Bản rút gọn (26/10): bấm 2 điểm → tuyến + bảng Dijkstra/A*; chọn kịch bản, vẽ vùng ùn tắc; "
           "bấm đoạn trên tuyến để đóng, mở lại; báo no_path. Không có lớp chấm node mở rộng. "
           "Chứng minh: checklist UI trong docs/PROGRESS.md"),
    "M7": ("M7 — Benchmark và tăng quy mô", "2026-11-08",
           "CSV đo thật + biểu đồ: 1.000 cặp, 4 kích thước (chỉ fixed trips), ùn tắc/đóng đường; "
           "điểm kiểm bằng chứng 05/11 (G1); MVP tích hợp 08/11. Chứng minh: python scripts/run_benchmarks.py --suite all"),
    "M8": ("M8 — Tour (mở rộng E1)", "2026-11-08",
           "NN, 2-opt có hướng, Held–Karp (T70, T71 xong 26/10); ma trận chi phí từ đồ thị + /api/tour, UI tour, benchmark tour "
           "(T72–T74) trước MVP 08/11. Chứng minh: pytest tests/test_tour.py; bước 9 của demo"),
    "M9": ("M9 — Hoàn thiện", "2026-11-12",
           "09–12/11 không thêm tính năng: chạy lại trên máy thứ hai, sửa lỗi, video demo; essay bắt đầu từ tuần 3. "
           "Final ready 12/11."),
}

LABELS = {
    "task": ("5319e7", "Hạng mục trong backlog, được tính vào burndown"),
    "P0": ("b60205", "Bắt buộc cho bản tối thiểu"),
    "P1": ("d93f0b", "Nên có; cắt được khi trễ"),
    "P2": ("fbca04", "Làm sau phần lõi; cắt được khi trễ"),
    "area:algorithms": ("1d76db", "Dijkstra, A*, heuristic"),
    "area:graph": ("0e8a16", "Mô hình đồ thị, snapshot, snap, đóng đường"),
    "area:data": ("006b75", "Dữ liệu OSM, cấu hình, kịch bản"),
    "area:api": ("0052cc", "FastAPI, CLI, service"),
    "area:frontend": ("c5def5", "Bản đồ Leaflet, giao diện"),
    "area:benchmark": ("5319e7", "Thực nghiệm, benchmark, biểu đồ"),
    "area:tour": ("bfd4f2", "Tour nhiều điểm: NN, 2-opt, Held–Karp"),
    "area:docs": ("0075ca", "Tài liệu, essay, demo"),
    "area:infra": ("7f8c8d", "Môi trường, CI, chạy trên Windows"),
    "type:feature": ("a2eeef", "Chức năng mới"),
    "type:test": ("bfdadc", "Kiểm thử"),
    "type:data": ("c2e0c6", "Chuẩn bị dữ liệu"),
    "type:experiment": ("d4c5f9", "Thực nghiệm"),
    "type:docs": ("0075ca", "Tài liệu"),
    "type:chore": ("ededed", "Việc hỗ trợ"),
    "blocked": ("000000", "Đang bị chặn bởi task khác"),
    "meeting": ("f9d0c4", "Biên bản họp nhóm"),
    "tracking": ("fef2c0", "Issue theo dõi tiến độ tự động"),
}

DOD = """- [ ] Làm trên branch riêng, mở PR có `Closes #<số issue này>`
- [ ] Ít nhất 1 thành viên khác review và approve
- [ ] CI xanh; lệnh kiểm tra trong mô tả chạy đạt
- [ ] Cập nhật `docs/PROGRESS.md` (trạng thái, bằng chứng, lỗi còn lại)
- [ ] Người phụ trách giải thích được phần 🧠 cho nhóm"""


def gh(args: list[str], payload: dict | None = None) -> object:
    cmd = ["gh", "api", *args]
    data = None
    if payload is not None:
        cmd += ["--input", "-"]
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    res = subprocess.run(cmd, input=data, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {res.stderr.decode('utf-8', 'replace').strip()}")
    out = res.stdout.decode("utf-8")
    return json.loads(out) if out.strip() else None


def gh_paged(path: str) -> list:
    items, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = gh([f"{path}{sep}per_page=100&page={page}"])
        items += batch
        if len(batch) < 100:
            return items
        page += 1


# ---------- phân tích TASKS.md ----------

HEADER = re.compile(r"^### (T\d\d|T-PLAN|G1) — (.+)$")
META = re.compile(r"^- 👤 (?P<owner>.+?) · ⏱ (?P<hours>.+?) · ⛓ (?P<deps>.+)$")


def parse_hours(text: str) -> float:
    m = re.match(r"(\d+)(?:–(\d+))?\s*h", text)
    if m:
        return float(m.group(2) or m.group(1))
    if "nhiều buổi" in text:
        return 10.0
    raise ValueError(f"không đọc được ước lượng giờ: {text!r}")


def parse_people(owner: str) -> tuple[list[str], list[str]]:
    """Trả (người phụ trách, người review) từ dòng 👤."""
    main = re.sub(r"\(.*?\)", "", owner).strip()
    if "cả nhóm" in main.lower():
        owners = list(PEOPLE)
    else:
        owners = [p.strip() for p in main.split("+") if p.strip()]
    reviewers = []
    m = re.search(r"\((\w[\w ]*?) review\)", owner)
    if m:
        reviewers = [m.group(1).strip()]
    for name in owners:
        if name not in PEOPLE:
            raise ValueError(f"tên không có trong PEOPLE: {name!r}")
    return owners, reviewers


def parse_tasks() -> list[dict]:
    lines = (ROOT / "docs" / "TASKS.md").read_text(encoding="utf-8").splitlines()
    tasks, cur = [], None
    for line in lines:
        h = HEADER.match(line)
        if h:
            cur = {"id": h.group(1), "title": h.group(2).strip(), "body": []}
            tasks.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("## ") or line.startswith("---"):
            cur = None
            continue
        m = META.match(line)
        if m and "owner" not in cur:
            cur["owner_text"] = m.group("owner")
            cur["owners"], cur["reviewers"] = parse_people(m.group("owner"))
            cur["hours"] = parse_hours(m.group("hours"))
            cur["deps"] = re.findall(r"\b(T-PLAN|T\d\d|G1)\b", m.group("deps"))
            continue
        cur["body"].append(line)
    for t in tasks:
        t["body"] = "\n".join(t["body"]).strip()
    return tasks


def load_schedule() -> dict[str, dict]:
    with open(ROOT / "docs" / "tracking" / "schedule.csv", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


AWAY: set[str] = set()   # người đang vắng: không tự giao review (Duy Anh vắng sáng 26/10, quay lại chiều 26/10)


def default_reviewer(task: dict, area: str) -> list[str]:
    """Người review luôn khác người phụ trách; rỗng nghĩa là cả nhóm review chéo."""
    preferred = ["Minh", "Duy Anh"] if area in ("frontend", "data") else ["Duy Anh", "Minh"]
    for name in [*task["reviewers"], "Tiến", *preferred, "Bảo"]:
        if name not in task["owners"] and name not in AWAY:
            return [name]
    return []


def fmt_people(names: list[str]) -> str:
    if not names:
        return "Cả nhóm review chéo phần của nhau"
    return ", ".join(f"@{PEOPLE[n]} ({n})" for n in names)


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def issue_title(t: dict) -> str:
    return f"{t['id']} · {t['title']}"


def issue_body(t: dict, sched: dict, numbers: dict[str, int]) -> str:
    if t["deps"]:
        deps = "\n".join(
            f"- [ ] #{numbers[d]}" if d in numbers else f"- [ ] {d}" for d in t["deps"]
        )
    else:
        deps = "Không có"
    reviewers = default_reviewer(t, sched["area"])
    return f"""> Task trong [docs/TASKS.md]({TASKS_URL}). Muốn sửa nội dung thì sửa file đó rồi chạy `python scripts/tracking/create_backlog.py --sync`.

### Mã task

{t['id']}

### Ước lượng (giờ)

{t['hours']:g}

### Người phụ trách

{fmt_people(t['owners'])}

### Người review đề xuất

{fmt_people(reviewers)}

### Thời gian dự kiến

{fmt_date(sched['start'])} → {fmt_date(sched['due'])}

### Phụ thuộc

{deps}

### Mô tả

{t['body']}

### Definition of Done

{DOD}
"""


def labels_for(sched: dict) -> list[str]:
    return ["task", sched["priority"], f"area:{sched['area']}", f"type:{sched['type']}"]


# Nhãn do script quản lý; các nhãn khác (blocked, bug, …) do người dùng gắn và được giữ nguyên.
def is_managed_label(name: str) -> bool:
    """Nhãn do script quản lý, nhận theo mẫu tên (kể cả nhãn area:/type: cũ đã bỏ khỏi LABELS)."""
    return name in ("task", "P0", "P1", "P2") or name.startswith(("area:", "type:"))


def merge_labels(managed: list[str], current: list[dict]) -> list[str]:
    return managed + [l["name"] for l in current if not is_managed_label(l["name"])]


def keep_checked(new_body: str, old_body: str) -> str:
    """Giữ các checkbox người dùng đã tick trong nội dung cũ (bỏ qua thụt lề và khoảng trắng cuối dòng)."""
    checked = {line.strip()[6:].strip() for line in (old_body or "").splitlines()
               if line.strip().lower().startswith("- [x] ")}
    out = []
    for line in new_body.splitlines():
        indent = line[:len(line) - len(line.lstrip())]
        item = line.strip()
        if item.startswith("- [ ] ") and item[6:].strip() in checked:
            line = f"{indent}- [x] {item[6:]}"
        out.append(line)
    return "\n".join(out) + ("\n" if new_body.endswith("\n") else "")


# ---------- GitHub ----------

def ensure_labels() -> None:
    existing = {l["name"] for l in gh_paged(f"repos/{REPO}/labels")}
    for name, (color, desc) in LABELS.items():
        payload = {"name": name, "color": color, "description": desc}
        if name in existing:
            gh(["-X", "PATCH", f"repos/{REPO}/labels/{name.replace(':', '%3A')}"], payload)
        else:
            gh(["-X", "POST", f"repos/{REPO}/labels"], payload)
            print(f"label + {name}")


def ensure_milestones() -> dict[str, int]:
    existing = {m["title"]: m["number"] for m in gh_paged(f"repos/{REPO}/milestones?state=all")}
    out = {}
    for key, (title, due, desc) in MILESTONES.items():
        payload = {"title": title, "due_on": f"{due}T12:00:00Z", "description": desc}
        if title in existing:
            gh(["-X", "PATCH", f"repos/{REPO}/milestones/{existing[title]}"], payload)
            out[key] = existing[title]
        else:
            out[key] = gh(["-X", "POST", f"repos/{REPO}/milestones"], payload)["number"]
            print(f"milestone + {title}")
    return out


def task_id_of(issue: dict) -> str | None:
    """Mã task lấy từ mục "Mã task" trong nội dung; tiêu đề chỉ là phương án dự phòng."""
    m = re.search(r"###[^\S\n]*Mã task[^\S\n]*\n\s*(T-PLAN|T\d\d|G1)\s*(?:\n|$)", issue.get("body") or "")
    if m:
        return m.group(1)
    head = issue["title"].split(" · ", 1)[0]
    return head if HEADER.match(f"### {head} — x") else None


def existing_task_issues() -> dict[str, dict]:
    """Tìm trên mọi issue (kể cả đã bỏ nhãn `task`) để không tạo trùng."""
    found: dict[str, dict] = {}
    for issue in gh_paged(f"repos/{REPO}/issues?state=all"):
        if "pull_request" in issue:
            continue
        tid = task_id_of(issue)
        if not tid:
            continue
        if tid in found:
            print(f"CẢNH BÁO: {tid} có nhiều issue (#{found[tid]['number']}, #{issue['number']}); dùng issue cũ hơn")
            if issue["number"] > found[tid]["number"]:
                continue
        found[tid] = issue
    return found


def assignable() -> set[str]:
    return {c["login"] for c in gh_paged(f"repos/{REPO}/collaborators")}


def sync_native_dependencies(tasks: list[dict], issues: dict[str, dict], remove_extra: bool) -> None:
    """Quan hệ 'blocked by' của GitHub khớp với ⛓ trong TASKS.md; bỏ qua nếu API không hỗ trợ."""
    by_number = {i["number"]: i for i in issues.values()}
    for t in tasks:
        num = issues[t["id"]]["number"]
        try:
            current = {d["number"]: d for d in gh_paged(f"repos/{REPO}/issues/{num}/dependencies/blocked_by")}
        except RuntimeError as e:
            print(f"bỏ qua dependency API: {e}")
            return
        wanted = {issues[d]["number"] for d in t["deps"] if d in issues}
        for n in wanted - set(current):
            gh(["-X", "POST", f"repos/{REPO}/issues/{num}/dependencies/blocked_by"], {"issue_id": by_number[n]["id"]})
        if remove_extra:
            for n in set(current) - wanted:
                gh(["-X", "DELETE", f"repos/{REPO}/issues/{num}/dependencies/blocked_by/{current[n]['id']}"])
                print(f"#{num}: bỏ phụ thuộc cũ #{n}")


def run(mode: str) -> None:
    tasks = parse_tasks()
    sched = load_schedule()
    missing = [t["id"] for t in tasks if t["id"] not in sched]
    extra = [k for k in sched if k not in {t["id"] for t in tasks}]
    if missing or extra:
        sys.exit(f"TASKS.md và schedule.csv lệch nhau: thiếu lịch {missing}, thừa lịch {extra}")

    if mode == "dry-run":
        total = 0.0
        for t in tasks:
            s = sched[t["id"]]
            total += t["hours"]
            print(f"{t['id']:7} {s['milestone']} {s['start']}→{s['due']} {t['hours']:>4g}h "
                  f"{'+'.join(t['owners']):24} rv={','.join(default_reviewer(t, s['area'])):8} "
                  f"deps={','.join(t['deps']) or '-':22} {labels_for(s)}")
        print(f"{len(tasks)} task, tổng {total:g} giờ ước lượng")
        return

    ensure_labels()
    ms = ensure_milestones()
    can_assign = assignable()
    issues = existing_task_issues()

    created = []
    for t in tasks:
        s = sched[t["id"]]
        if t["id"] in issues:
            continue
        payload = {
            "title": issue_title(t),
            "labels": labels_for(s),
            "milestone": ms[s["milestone"]],
            "assignees": [PEOPLE[n] for n in t["owners"] if PEOPLE[n] in can_assign],
            "body": issue_body(t, s, {}),
        }
        issues[t["id"]] = gh(["-X", "POST", f"repos/{REPO}/issues"], payload)
        created.append(t["id"])
        print(f"issue + #{issues[t['id']]['number']} {payload['title']}")
        time.sleep(1)  # tránh giới hạn tốc độ tạo nội dung của GitHub

    # --create chỉ hoàn thiện issue mới tạo; --sync cập nhật mọi issue nhưng giữ checkbox và nhãn người dùng gắn.
    numbers = {tid: i["number"] for tid, i in issues.items()}
    targets = tasks if mode == "sync" else [t for t in tasks if t["id"] in created]
    for t in targets:
        s = sched[t["id"]]
        old = issues[t["id"]]
        payload = {
            "title": issue_title(t),
            "body": keep_checked(issue_body(t, s, numbers), old.get("body", "")),
            "labels": merge_labels(labels_for(s), old.get("labels", [])),
            "milestone": ms[s["milestone"]],
            "assignees": [PEOPLE[n] for n in t["owners"] if PEOPLE[n] in can_assign],
        }
        gh(["-X", "PATCH", f"repos/{REPO}/issues/{numbers[t['id']]}"], payload)

    sync_native_dependencies(targets, issues, remove_extra=(mode == "sync"))
    print(f"xong: {len(created)} issue mới, {len(targets)} issue được cập nhật")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--create", action="store_true")
    g.add_argument("--sync", action="store_true")
    a = ap.parse_args()
    run("dry-run" if a.dry_run else "create" if a.create else "sync")

"""Burndown và báo cáo tiến độ SaiGo, tính từ dữ liệu thật trên GitHub.

Nguồn: issue có nhãn `task` (ước lượng giờ nằm trong mục "Ước lượng (giờ)" của issue),
pull request và review của repo. Không có số nào nhập tay.

Cách tính:
- Còn lại ngày d = tổng giờ của task đã tạo, chưa đóng và chưa bị cắt tại cuối ngày d (giờ VN).
- Phạm vi ngày d = tổng giờ task đã tạo trừ phần đã cắt (đóng với lý do "not planned").
- Đường lý tưởng: từ phạm vi ngày bắt đầu giảm đều về 0 vào ngày final ready.
- Số của các ngày đã qua được chốt vào `daily.csv` (chỉ ghi thêm, không sửa): mở lại issue hôm nay
  làm tăng số hôm nay, không sửa số những ngày trước. Điểm của hôm nay là tạm tính.
- Task được coi là "hoàn thành có bằng chứng" khi issue được đóng bởi PR đã merge hoặc commit.
  Issue đóng tay vẫn giảm phần còn lại nhưng được liệt kê riêng và không tính vào giờ hoàn thành của thành viên.
- Giờ của task nhiều người phụ trách được chia đều. Người phụ trách = assignee; nếu chưa có assignee
  thì lấy tên trong mục "Người phụ trách" và đánh dấu "(chưa nhận)".
- Review = số PR khác nhau mà một người đã review (không tính PR của chính mình, không tính review bị dismiss).

    python scripts/tracking/burndown.py --out build/tracking [--history path/daily.csv]
    python scripts/tracking/burndown.py --publish build/tracking     # đăng REPORT.md + tổng kết tuần đã tính

Token: biến môi trường GITHUB_TOKEN, nếu không có thì dùng `gh auth token`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "NeitLN/SaiGo")
VN = timezone(timedelta(hours=7))  # Việt Nam không có giờ mùa hè
START = date(2026, 10, 23)          # ngày lập backlog
END = date(2026, 11, 12)            # final ready (Project_Intructions_261.pdf)
G1 = date(2026, 11, 5)
WEEKS = [
    ("Tuần 1 · 19–25/10", date(2026, 10, 19), date(2026, 10, 25)),
    ("Tuần 2 · 26/10–01/11", date(2026, 10, 26), date(2026, 11, 1)),
    ("Tuần 3 · 02–08/11", date(2026, 11, 2), date(2026, 11, 8)),
    ("Tuần 4 · 09–15/11", date(2026, 11, 9), date(2026, 11, 15)),
    ("Tuần 5 · 16–22/11", date(2026, 11, 16), date(2026, 11, 22)),
]
NAMES = {"NeitLN": "Tiến", "anh7032": "Duy Anh", "Jayson135724": "Minh", "dobaovlu": "Bảo"}
IMAGE_URL = f"https://raw.githubusercontent.com/{REPO}/tracking/burndown.png"
DAILY_FIELDS = ["date", "scope_h", "remaining_h", "done_h", "cut_h", "recorded_at"]
WEEK_MARK = "<!-- saigo-week:{} -->"


# ---------- GitHub API ----------

@lru_cache(maxsize=1)
def token() -> str:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def _request(url: str, method: str, payload: dict | None):
    req = urllib.request.Request(
        url, method=method, data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req) as res:
                body = res.read()
            return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            retryable = (403, 429) if method == "POST" and "graphql" not in url else (403, 429, 500, 502, 503)
            if e.code not in retryable or attempt == 4:
                raise  # không retry POST tạo nội dung khi lỗi 5xx: GitHub có thể đã tạo rồi
            wait = int(e.headers.get("Retry-After") or 2 ** (attempt + 1))
            time.sleep(min(wait, 60))


def api(path: str, method: str = "GET", payload: dict | None = None):
    return _request(f"https://api.github.com/{path}", method, payload)


def graphql(query: str, **variables) -> dict:
    out = _request("https://api.github.com/graphql", "POST", {"query": query, "variables": variables})
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


def paged(path: str) -> list:
    out, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = api(f"{path}{sep}per_page=100&page={page}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def vn_date(ts: str | None) -> date | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(VN).date()


# ---------- dữ liệu ----------

def section(body: str, heading: str) -> str:
    m = re.search(rf"###\s*{re.escape(heading)}\s*\n(.*?)(?=\n###\s|\Z)", body or "", re.S)
    return m.group(1).strip() if m else ""


def parse_estimate(text: str) -> float | None:
    try:
        value = float(text.replace(",", ".").split()[0])
    except (ValueError, IndexError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def close_events(numbers: list[int]) -> dict[int, list[dict]]:
    """Các lần đóng/mở lại của issue theo thời gian, kèm lý do đóng và ai đóng.

    kind: 'closed' | 'reopened'; closer: 'pr' (PR đã merge), 'commit', 'manual'; cut: đóng với lý do not planned.
    """
    owner, name = REPO.split("/")
    out = {}
    for i in range(0, len(numbers), 20):
        chunk = numbers[i:i + 20]
        fields = "\n".join(
            f"""i{n}: issue(number:{n}){{ timelineItems(itemTypes:[CLOSED_EVENT, REOPENED_EVENT], first:100){{ nodes{{
                __typename
                ... on ClosedEvent {{ createdAt stateReason closer {{ __typename ... on PullRequest {{ merged }} }} }}
                ... on ReopenedEvent {{ createdAt }} }} }} }}"""
            for n in chunk)
        data = graphql(f"query($o:String!,$n:String!){{ repository(owner:$o,name:$n){{ {fields} }} }}", o=owner, n=name)
        for n in chunk:
            events = []
            for node in data["repository"][f"i{n}"]["timelineItems"]["nodes"]:
                if node["__typename"] == "ReopenedEvent":
                    events.append({"date": vn_date(node["createdAt"]), "kind": "reopened"})
                    continue
                closer = node.get("closer") or {}
                kind = closer.get("__typename")
                events.append({
                    "date": vn_date(node["createdAt"]), "kind": "closed",
                    "cut": node.get("stateReason") in ("NOT_PLANNED", "DUPLICATE"),
                    "closer": "pr" if kind == "PullRequest" and closer.get("merged") else "commit" if kind == "Commit" else "manual",
                })
            out[n] = events
    return out


def state_at(t: dict, d: date) -> dict | None:
    """Sự kiện đóng đang có hiệu lực vào cuối ngày d, hoặc None nếu issue đang mở."""
    current = None
    for e in t["events"]:
        if e["date"] > d:
            break
        current = e if e["kind"] == "closed" else None
    return current


def load_tasks() -> tuple[list[dict], list[str]]:
    tasks, problems = [], []
    raw = [i for i in paged(f"repos/{REPO}/issues?state=all&labels=task") if "pull_request" not in i]
    events = close_events([i["number"] for i in raw if i["state"] == "closed" or i.get("state_reason") == "reopened"])
    for i in raw:
        hours = parse_estimate(section(i["body"], "Ước lượng (giờ)"))
        if hours is None:
            problems.append(f"#{i['number']} thiếu hoặc sai mục \"Ước lượng (giờ)\" (cần một số ≥ 0); tạm tính 0 giờ")
            hours = 0.0
        assignees = [a["login"] for a in i["assignees"]]
        proposed = re.findall(r"@([A-Za-z0-9-]+)", section(i["body"], "Người phụ trách"))
        t = {
            "number": i["number"], "title": i["title"], "hours": hours,
            "owners": assignees or proposed, "accepted": bool(assignees),
            "created": vn_date(i["created_at"]), "events": events.get(i["number"], []),
            "due": section(i["body"], "Thời gian dự kiến").split("→")[-1].strip(),
        }
        if i["state"] == "closed" and not t["events"]:  # phòng khi timeline chưa trả về sự kiện
            t["events"] = [{"date": vn_date(i["closed_at"]), "kind": "closed", "closer": "manual",
                            "cut": i.get("state_reason") in ("not_planned", "duplicate")}]
        last = state_at(t, date.max)
        t["closed"] = last["date"] if last else None
        t["cut"] = bool(last and last["cut"])
        t["closed_by"] = ("cut" if t["cut"] else last["closer"]) if last else None
        tasks.append(t)
    return tasks, problems


def load_prs() -> list[dict]:
    prs = []
    for p in paged(f"repos/{REPO}/pulls?state=all"):
        reviewers = {}
        with_inline = {c["pull_request_review_id"] for c in paged(f"repos/{REPO}/pulls/{p['number']}/comments")}
        for r in paged(f"repos/{REPO}/pulls/{p['number']}/reviews"):
            login = (r["user"] or {}).get("login")
            if not login or login == p["user"]["login"] or r["state"] in ("DISMISSED", "PENDING"):
                continue
            if r["state"] == "COMMENTED" and not (r.get("body") or "").strip() and r["id"] not in with_inline:
                continue  # review "chỉ bình luận" nhưng không có nội dung
            d = vn_date(r["submitted_at"])
            reviewers[login] = min(reviewers.get(login, d), d)  # lần review đầu tiên của người đó trên PR này
        prs.append({"number": p["number"], "author": p["user"]["login"],
                    "merged": vn_date(p["merged_at"]), "reviewers": reviewers})
    return prs


# ---------- tính toán ----------

def measure(tasks: list[dict], d: date) -> dict:
    """Trạng thái cuối ngày d, dựng lại từ sự kiện đóng/mở lại (không dùng trạng thái hiện tại)."""
    created = [t for t in tasks if t["created"] <= d]
    remaining = done = cut = 0.0
    for t in created:
        e = state_at(t, d)
        if e is None:
            remaining += t["hours"]
        elif e["cut"]:
            cut += t["hours"]
        else:
            done += t["hours"]
    return {"date": d.isoformat(), "scope_h": remaining + done, "remaining_h": remaining,
            "done_h": done, "cut_h": cut}


def load_history(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def update_history(history: dict[str, dict], tasks: list[dict], today: date, now: datetime) -> dict[str, dict]:
    """Chốt các ngày đã qua còn thiếu; không bao giờ sửa dòng đã có."""
    d = START
    while d < today:
        key = d.isoformat()
        if key not in history:
            history[key] = {**measure(tasks, d), "recorded_at": now.isoformat(timespec="minutes")}
        d += timedelta(days=1)
    return history


def series(history: dict[str, dict], tasks: list[dict], today: date) -> list[dict]:
    scope0 = float(history[START.isoformat()]["scope_h"]) if START.isoformat() in history else measure(tasks, START)["scope_h"]
    span = (END - START).days
    rows, d = [], START
    while d <= max(END, today):
        ideal = max(0.0, scope0 * (1 - (d - START).days / span)) if d <= END else 0.0
        if d < today and d.isoformat() in history:
            h = history[d.isoformat()]
            row = {k: float(h[k]) for k in ("scope_h", "remaining_h", "done_h", "cut_h")}
            row["provisional"] = False
        elif d == today:
            row = {k: v for k, v in measure(tasks, d).items() if k != "date"}
            row["provisional"] = True
        else:
            row = {"scope_h": None, "remaining_h": None, "done_h": None, "cut_h": None, "provisional": False}
        rows.append({"date": d.isoformat(), **row, "ideal_h": round(ideal, 2)})
        d += timedelta(days=1)
    return rows


def week_stats(tasks: list[dict], prs: list[dict], rows: list[dict], today: date) -> list[dict]:
    by_date = {r["date"]: r for r in rows}
    out = []
    for name, ws, we in WEEKS:
        if ws > max(today, END) or we < START:
            continue
        planned = 0.0
        for t in tasks:
            try:
                due = datetime.strptime(t["due"], "%d/%m/%Y").date()
            except ValueError:
                continue
            if ws <= due <= we and not t["cut"]:
                planned += t["hours"]
        done = [t for t in tasks if t["closed"] and ws <= t["closed"] <= we and not t["cut"]]
        end_row = by_date.get(min(we, today).isoformat(), {})
        out.append({
            "week": name, "start": ws.isoformat(), "end": we.isoformat(), "finished": we < today,
            "planned_h": planned, "done_h": sum(t["hours"] for t in done), "done_n": len(done),
            "manual_n": sum(1 for t in done if t["closed_by"] == "manual"),
            "cut_h": sum(t["hours"] for t in tasks if t["cut"] and ws <= t["closed"] <= we),
            "remaining_h": end_row.get("remaining_h") if ws <= today else None,
            "prs_merged": sum(1 for p in prs if p["merged"] and ws <= p["merged"] <= we),
            "reviews": sum(1 for p in prs for d in p["reviewers"].values() if d and ws <= d <= we),
        })
    return out


def member_stats(tasks: list[dict], prs: list[dict]) -> list[dict]:
    agg = defaultdict(lambda: {"assigned_h": 0.0, "done_h": 0.0, "done_n": 0, "manual_n": 0, "open_n": 0,
                               "prs": 0, "reviews": 0, "accepted": True})
    for t in tasks:
        if t["cut"] or not t["owners"]:
            continue
        share = t["hours"] / len(t["owners"])
        for o in t["owners"]:
            a = agg[o]
            a["assigned_h"] += share
            a["accepted"] &= t["accepted"]
            if not t["closed"]:
                a["open_n"] += 1
            elif t["closed_by"] == "manual":
                a["manual_n"] += 1
            else:
                a["done_h"] += share
                a["done_n"] += 1
    for p in prs:
        if p["merged"]:
            agg[p["author"]]["prs"] += 1
        for reviewer in p["reviewers"]:
            agg[reviewer]["reviews"] += 1
    return [{"login": k, "name": NAMES.get(k, k), **v} for k, v in sorted(agg.items(), key=lambda kv: NAMES.get(kv[0], kv[0]))]


# ---------- xuất ----------

def plot(rows: list[dict], path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.dates import DateFormatter, DayLocator
    except ImportError:
        return False
    xs = [date.fromisoformat(r["date"]) for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=120)
    ax.plot(xs, [r["ideal_h"] for r in rows], "--", color="#888", label="Lý tưởng")
    scope = [(x, r["scope_h"]) for x, r in zip(xs, rows) if r["scope_h"] is not None]
    ax.step(*zip(*scope), where="post", color="#c8a", alpha=0.6, label="Phạm vi (tổng giờ)")
    actual = [(x, r["remaining_h"]) for x, r in zip(xs, rows) if r["remaining_h"] is not None and not r["provisional"]]
    if actual:
        ax.plot(*zip(*actual), marker="o", color="#d9480f", label="Còn lại (đã chốt cuối ngày)")
    today = [(x, r["remaining_h"]) for x, r in zip(xs, rows) if r["provisional"]]
    if today:
        ax.plot(*zip(*today), marker="o", mfc="white", color="#d9480f", ls="", label="Hôm nay (tạm tính)")
    for _, ws, _ in WEEKS:
        if xs[0] <= ws <= xs[-1]:
            ax.axvline(ws, color="#ddd", lw=0.8, zorder=0)
    ax.axvline(G1, color="#1c7ed6", lw=1, ls=":", label="Cổng G1 (05/11)")
    ax.set_title("SaiGo — Burndown theo giờ ước lượng")
    ax.set_ylabel("Giờ còn lại")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8)
    ax.xaxis.set_major_locator(DayLocator(interval=2))
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return True


def fmt(h) -> str:
    return "—" if h is None else f"{h:g}"


CLOSE_LABEL = {"pr": "qua PR", "commit": "qua commit", "manual": "**đóng tay, chưa có PR**"}


def report(rows, weeks, members, tasks, problems, today: date, now: datetime, image_version: str) -> str:
    cur = next(r for r in rows if r["provisional"]) if START <= today else rows[0]
    gap = cur["remaining_h"] - cur["ideal_h"]
    open_n = sum(1 for t in tasks if not t["closed"])
    verified_h = sum(t["hours"] for t in tasks if t["closed_by"] in ("pr", "commit"))
    manual_h = sum(t["hours"] for t in tasks if t["closed_by"] == "manual")
    cut_note = f" (trong đó {cur['cut_h']:g} giờ là do cắt phạm vi, không phải do làm xong)" if cur["cut_h"] and gap < 0 else ""
    recent = sorted((t for t in tasks if t["closed"] and (today - t["closed"]).days < 7),
                    key=lambda t: (t["closed"], t["number"]), reverse=True)
    lines = [
        "## 📉 Burndown SaiGo",
        "",
        f"_Tự động cập nhật {now:%H:%M %d/%m/%Y} (giờ VN) bởi workflow `tracking.yml` từ trạng thái issue/PR thật. "
        "Số những ngày đã qua được chốt cuối ngày và không bị sửa lại; số hôm nay là tạm tính. "
        "Cách tính ở đầu file `scripts/tracking/burndown.py`._",
        "",
        f"![Burndown]({IMAGE_URL}?v={image_version})",
        "",
        f"- **Phạm vi hiện tại:** {cur['scope_h']:g} giờ ước lượng, {sum(1 for t in tasks if not t['cut'])} task"
        + (f" (đã cắt {cur['cut_h']:g} giờ)" if cur["cut_h"] else ""),
        f"- **Đã đóng:** {cur['done_h']:g} giờ — có bằng chứng (PR/commit) {verified_h:g} giờ"
        + (f", **đóng tay chưa có PR {manual_h:g} giờ**" if manual_h else "")
        + f" · **Còn lại:** {cur['remaining_h']:g} giờ, {open_n} task mở",
        f"- **Đường lý tưởng hôm nay:** {cur['ideal_h']:g} giờ → "
        + ("đúng kế hoạch" if abs(gap) < 0.5
           else f"**chậm** hơn kế hoạch {gap:.1f} giờ" if gap > 0
           else f"nhanh hơn kế hoạch {-gap:.1f} giờ{cut_note}"),
        f"- Mốc: cổng G1 {G1:%d/%m} · final ready {END:%d/%m} · thuyết trình 19/11 · nộp 22/11",
    ]
    if problems:
        lines += ["", "> ⚠️ **Dữ liệu cần sửa:**"] + [f"> - {p}" for p in problems]
    lines += [
        "",
        "### Theo tuần",
        "",
        "| Tuần | Giờ đến hạn | Giờ hoàn thành | Task xong | Còn lại cuối tuần | PR merge | Lượt review |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for w in weeks:
        lines.append(f"| {w['week']} | {w['planned_h']:g} | {w['done_h']:g} | {w['done_n']} | {fmt(w['remaining_h'])} | {w['prs_merged']} | {w['reviews']} |")
    lines += [
        "",
        "### Theo thành viên",
        "",
        "| Thành viên | Giờ được giao | Giờ hoàn thành có bằng chứng | Task xong | Đóng tay | Task mở | PR đã merge | PR đã review (có nội dung) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in members:
        note = "" if m["accepted"] else " (chưa nhận)"
        lines.append(f"| {m['name']} (@{m['login']}){note} | {m['assigned_h']:.1f} | {m['done_h']:.1f} | {m['done_n']} | {m['manual_n']} | {m['open_n']} | {m['prs']} | {m['reviews']} |")
    lines += ["", "### Đóng trong 7 ngày qua", ""]
    for t in recent:
        how = "đã cắt khỏi phạm vi" if t["cut"] else CLOSE_LABEL.get(t["closed_by"], "")
        lines.append(f"- {t['closed']:%d/%m} · #{t['number']} {t['title']} ({t['hours']:g} h, {how})")
    if not recent:
        lines.append("- Chưa có")
    lines += [
        "",
        "### Ghi chú",
        "",
        "- Backlog ban đầu (40 task, ước lượng giờ) do Tiến lập từ `docs/TASKS.md` bằng script ngày 23/10/2026; "
        "trạng thái sau đó do từng thành viên cập nhật. Không dựng lại dữ liệu trước ngày này.",
        "- Ước lượng lấy cận trên của khoảng trong TASKS.md (ví dụ \"2–3 h\" → 3); \"nhiều buổi\" (essay) được giả định là 10 giờ.",
        "- #1 đóng bằng commit trực tiếp trước khi bật bảo vệ branch `main`; từ đó mọi thay đổi phải qua PR có review.",
        f"- Số liệu từng ngày: [`daily.csv`](https://github.com/{REPO}/blob/tracking/daily.csv) trên branch `tracking`.",
    ]
    return "\n".join(lines) + "\n"


def weekly_comments(weeks: list[dict]) -> list[dict]:
    out = []
    for w in weeks:
        if not w["finished"]:
            continue
        body = (f"{WEEK_MARK.format(w['start'])}\n### Tổng kết {w['week']}\n\n"
                f"- Giờ đến hạn trong tuần: {w['planned_h']:g} · giờ hoàn thành: {w['done_h']:g} ({w['done_n']} task"
                + (f", trong đó {w['manual_n']} task đóng tay" if w["manual_n"] else "") + ")\n"
                + (f"- Cắt khỏi phạm vi: {w['cut_h']:g} giờ\n" if w["cut_h"] else "")
                + f"- Còn lại cuối tuần: {fmt(w['remaining_h'])} giờ\n"
                f"- PR đã merge: {w['prs_merged']} · lượt review: {w['reviews']}\n\n"
                "_Tạo tự động bởi workflow `tracking.yml`; mỗi tuần chỉ đăng một lần._\n")
        out.append({"start": w["start"], "body": body})
    return out


def tracking_issue() -> int:
    if os.environ.get("TRACKING_ISSUE"):
        return int(os.environ["TRACKING_ISSUE"])
    issues = paged(f"repos/{REPO}/issues?state=open&labels=tracking")
    if not issues:
        raise SystemExit("không tìm thấy issue mở có nhãn `tracking`")
    return min(i["number"] for i in issues)


def publish(out: Path) -> None:
    num = tracking_issue()
    api(f"repos/{REPO}/issues/{num}", "PATCH", {"body": (out / "REPORT.md").read_text(encoding="utf-8")})
    print(f"đã cập nhật issue #{num}")
    posted = {m.group(1) for c in paged(f"repos/{REPO}/issues/{num}/comments")
              for m in [re.search(r"<!-- saigo-week:(\S+) -->", c["body"] or "")] if m}
    for c in json.loads((out / "weekly.json").read_text(encoding="utf-8")):
        if c["start"] not in posted:
            api(f"repos/{REPO}/issues/{num}/comments", "POST", {"body": c["body"]})
            print(f"đã đăng tổng kết tuần bắt đầu {c['start']}")


def compute(out: Path, history_path: Path | None, image_version: str | None) -> None:
    now = datetime.now(VN)
    today = now.date()
    tasks, problems = load_tasks()
    prs = load_prs()
    history = update_history(load_history(history_path), tasks, today, now)
    rows = series(history, tasks, today)
    weeks = week_stats(tasks, prs, rows, today)
    members = member_stats(tasks, prs)

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DAILY_FIELDS)
        w.writeheader()
        w.writerows(history[k] for k in sorted(history))
    with open(out / "burndown.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    has_png = plot(rows, out / "burndown.png")
    md = report(rows, weeks, members, tasks, problems, today, now, image_version or now.strftime("%Y%m%d%H%M"))
    (out / "REPORT.md").write_text(md, encoding="utf-8")
    (out / "weekly.json").write_text(json.dumps(weekly_comments(weeks), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(tasks)} task, {len(prs)} PR, {len(history)} ngày đã chốt → {out} (png: {has_png})")
    for p in problems:
        print(f"CẢNH BÁO: {p}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("build/tracking"))
    ap.add_argument("--history", type=Path, help="daily.csv đã chốt từ branch tracking")
    ap.add_argument("--image-version", help="tham số chống cache ảnh (mặc định: thời điểm chạy)")
    ap.add_argument("--publish", type=Path, metavar="DIR", help="đăng REPORT.md và weekly.json đã tính trong DIR")
    a = ap.parse_args()
    if a.publish:
        publish(a.publish)
    else:
        # Chạy tại máy không truyền --history thì giữ các ngày đã chốt ở lần chạy trước trong cùng thư mục.
        compute(a.out, a.history or a.out / "daily.csv", a.image_version)


if __name__ == "__main__":
    main()

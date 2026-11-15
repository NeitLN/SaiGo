"""Dựng bảng tên đường (mã đường OSM → tên) từ GraphML thô đã đóng băng.

File đồ thị `saigo-graph/1` chỉ giữ `way_ids` của mỗi cạnh, không giữ tên đường. Bảng này là **file phụ**, không
sửa file đồ thị, nên sha256 của đồ thị và mọi số đo thí nghiệm giữ nguyên. Backend nạp bảng (nếu có) để ghi tên
đường cho từng đoạn khi người dùng chọn đoạn cần đóng (đánh giá dùng thử 16/11).

OSMnx gộp các đoạn liền nhau thành một cạnh: khi đó `osmid` và `name` có thể là danh sách (`[a, b]`,
`['A', 'B']`) mà thứ tự hai danh sách không chắc khớp nhau. Vì vậy chỉ gán tên khi không mơ hồ:
- một mã đường, một tên → gán;
- nhiều mã đường, một tên → gán tên đó cho mọi mã;
- nhiều tên → bỏ qua cạnh này (mã đường thường còn xuất hiện ở cạnh khác, không gộp).
Một mã đường gặp nhiều tên khác nhau thì giữ tên gặp nhiều nhất (hòa thì tên đứng trước theo thứ tự chữ).

Cách chạy (cần `data/raw/outer.graphml` từ Release `data-raw-20261024`)::

    python scripts/build_street_names.py --graphml data/raw/outer.graphml \\
        --out data/processed/street-names-20261024.json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

FORMAT = "saigo-street-names/1"
NS = "{http://graphml.graphdrawing.org/xmlns}"


def parse_list(raw: str) -> list[str]:
    """`"123"` → `["123"]`; `"[1, 2]"` → `["1", "2"]`; `"['A', 'B']"` → `["A", "B"]` (định dạng OSMnx ghi GraphML)."""
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            value = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return [text]
        return [str(v).strip() for v in value if str(v).strip()]
    return [text] if text else []


def collect_names(graphml: Path) -> dict[int, str]:
    """Đọc GraphML, trả `{mã đường OSM: tên}` theo các quy tắc ở đầu file."""
    keys: dict[str, str] = {}
    seen: dict[int, Counter[str]] = defaultdict(Counter)
    for _event, elem in ET.iterparse(graphml, events=("end",)):
        tag = elem.tag.removeprefix(NS)
        if tag == "key" and elem.get("for") == "edge":
            keys[elem.get("id", "")] = elem.get("attr.name", "")
        elif tag == "edge":
            data = {keys.get(d.get("key", ""), ""): (d.text or "") for d in elem.findall(f"{NS}data")}
            names = parse_list(data.get("name", ""))
            ids = parse_list(data.get("osmid", ""))
            if len(names) == 1 and ids:
                for way in ids:
                    if way.isdigit():
                        seen[int(way)][names[0]] += 1
            elem.clear()
        elif tag == "node":
            elem.clear()
    return {way: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for way, c in seen.items()}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graphml", type=Path, default=Path("data/raw/outer.graphml"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/street-names-20261024.json"))
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console Windows mặc định cp1252
    if not args.graphml.is_file():
        print(f"Không thấy {args.graphml}; tải Release data-raw-20261024 trước (ONBOARDING mục 3).", file=sys.stderr)
        return 1
    names = collect_names(args.graphml)
    doc = {
        "format": FORMAT,
        "source": args.graphml.as_posix(),
        "source_sha256": sha256(args.graphml),
        "n_ways": len(names),
        "names": {str(k): names[k] for k in sorted(names)},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(names)} mã đường có tên → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

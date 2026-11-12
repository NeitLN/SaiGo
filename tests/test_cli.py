"""T12: CLI tìm đường (docs/tasks/T12-cli.md)."""

import re

import pytest

from app.cli import main
from mini_cases import MINI, expected_cases

BASELINE = [c for c in expected_cases() if c["scenario"] is None and not c["blocked"]]


def run(capsys, *args):
    code = main(["route", "--graph", str(MINI), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def section(out, label):
    """Phần in ra của một thuật toán, từ dòng [label] tới dòng [..] kế tiếp."""
    m = re.search(rf"^\[{re.escape(label)}\]\n((?:  .*\n)+)", out, re.M)
    assert m, out
    return m.group(1)


@pytest.mark.parametrize("case", BASELINE, ids=lambda c: c["name"])
def test_both_matches_expected(capsys, case):
    code, out, _ = run(capsys, "--from", case["source"], "--to", case["target"], "--algo", "both")
    assert code == 0
    for algo, label in (("dijkstra", "Dijkstra"), ("astar", "A*")):
        want = case[algo]
        part = section(out, label)
        assert "Tuyến: " + " → ".join(want["path"]) in part
        assert f"Chi phí: {want['cost_s']:.1f} s" in part
        assert f"expanded: {want['expanded']}\n" in part
        assert re.search(r"Thời gian chạy: \d+\.\d{3} ms", part)
    assert "Chi phí trùng khớp: có" in out


@pytest.mark.parametrize("algo,label,other", [("dijkstra", "Dijkstra", "[A*]"), ("astar", "A*", "[Dijkstra]")])
def test_single_algo(capsys, algo, label, other):
    code, out, _ = run(capsys, "--from", "S", "--to", "T", "--algo", algo)
    assert code == 0
    assert "Chi phí: 80.0 s" in section(out, label)
    assert other not in out
    assert "trùng khớp" not in out


def test_latlon_snaps_to_nearest_node(capsys):
    # Lệch vài mét so với S (10.7725, 106.698) và T (10.7725, 106.7053154)
    code, out, _ = run(capsys, "--from-latlon", "10.77252,106.69801", "--to-latlon", "10.77248,106.70530")
    assert code == 0
    assert "→ node 0 (snap" in out
    assert "Tuyến: S → A → T" in section(out, "A*")
    assert "Chi phí trùng khớp: có" in out


def test_unknown_name_is_error(capsys):
    code, out, err = run(capsys, "--from", "X", "--to", "T")
    assert code == 2
    assert "không có node tên 'X'" in err


def test_latlon_too_far_is_error(capsys):
    code, _, err = run(capsys, "--from-latlon", "10.80,106.70", "--to", "T")
    assert code == 2
    assert err.startswith("Lỗi:")


def test_bad_latlon_format(capsys):
    with pytest.raises(SystemExit):
        run(capsys, "--from-latlon", "10.77", "--to", "T")


def test_missing_graph_is_error(capsys, tmp_path):
    code = main(["route", "--graph", str(tmp_path / "khong-co.json"), "--from", "S", "--to", "T"])
    err = capsys.readouterr().err
    assert code == 2
    assert err.startswith("Lỗi: không nạp được đồ thị")

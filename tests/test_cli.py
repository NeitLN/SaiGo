"""T12: CLI tìm đường (docs/tasks/T12-cli.md)."""

import re

import pytest

from app.cli import main
from mini_cases import FIXTURES, MINI, edge_id, expected_cases, load_mini

BASELINE = [c for c in expected_cases() if c["scenario"] is None and not c["blocked"]]
MINI_BAD = FIXTURES / "mini_bad.json"
SCENARIOS_MINI = FIXTURES / "scenarios_mini.json"


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


# --- T22: check-heuristic trên fixture ---

def run_check(capsys, graph):
    code = main(["check-heuristic", "--graph", str(graph)])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_check_heuristic_mini_is_clean(capsys):
    code, out, _ = run_check(capsys, MINI)
    assert code == 0
    assert "Đồ thị: mini (6 node, 8 cạnh)" in out
    assert "v_max: 10.000000 m/s (36.0 km/h)" in out
    assert "c: 1.0000000000" in out
    assert "Số cạnh vi phạm (length < haversine − 1 mm): 0" in out
    assert "Cạnh tệ nhất" not in out
    assert "Cảnh báo" not in out


def test_check_heuristic_bad_flags_one_violation_and_warning(capsys):
    code, out, _ = run_check(capsys, MINI_BAD)
    assert code == 0
    assert "c: 0." in out
    assert float(re.search(r"^c: ([0-9.]+)$", out, re.M).group(1)) < 1.0
    assert "Số cạnh vi phạm (length < haversine − 1 mm): 1" in out
    assert "Cạnh tệ nhất (tối đa 5, tỉ lệ length/haversine nhỏ nhất):" in out
    assert "cạnh 0: length 200.000 m · haversine 399." in out
    assert "Cảnh báo: c = 0." in out and "< 0.999" in out


def test_check_heuristic_missing_graph_is_error(capsys, tmp_path):
    code, _, err = run_check(capsys, tmp_path / "khong-co.json")
    assert code == 2
    assert err.startswith("Lỗi: không nạp được đồ thị")


# --- T40: route --scenario / --block trên fixture ---

def test_scenario_congestion_changes_route(capsys):
    code, out, _ = run(capsys, "--scenario", "un-tac-tam-a", "--scenario-file", str(SCENARIOS_MINI),
                       "--from", "S", "--to", "T")
    assert code == 0
    assert "Kịch bản: un-tac-tam-a · đóng: không" in out
    part = section(out, "A*")
    assert "Tuyến: S → B → T" in part
    assert "Chi phí: 100.0 s" in part
    assert "Chi phí trùng khớp: có" in out


def test_block_edge_reroutes_and_reports_blocked(capsys):
    graph, meta = load_mini()
    a_to_t = edge_id(graph, meta, "A->T")
    code, out, _ = run(capsys, "--block", str(a_to_t), "--from", "S", "--to", "T")
    assert code == 0
    assert f"Kịch bản: baseline · đóng: {a_to_t}" in out
    assert "Tuyến: S → B → T" in section(out, "A*")
    assert "Chi phí: 100.0 s" in section(out, "A*")


def test_block_both_exits_is_no_path(capsys):
    graph, meta = load_mini()
    a_to_t = edge_id(graph, meta, "A->T")
    b_to_t = edge_id(graph, meta, "B->T")
    code, out, _ = run(capsys, "--block", str(a_to_t), str(b_to_t), "--from", "S", "--to", "T")
    assert code == 0
    assert f"Kịch bản: baseline · đóng: {a_to_t}, {b_to_t}" in out
    assert "Tuyến: không có đường đi" in section(out, "Dijkstra")
    assert "Tuyến: không có đường đi" in section(out, "A*")
    assert "Chi phí trùng khớp: có" in out


def test_unknown_scenario_is_error(capsys):
    code, _, err = run(capsys, "--scenario", "khong-co", "--from", "S", "--to", "T")
    assert code == 2
    assert "không có kịch bản 'khong-co'" in err


def test_bad_blocked_edge_is_error(capsys):
    code, _, err = run(capsys, "--block", "999", "--from", "S", "--to", "T")
    assert code == 2
    assert err.startswith("Lỗi:") and "999" in err


def test_missing_scenario_file_is_error(capsys, tmp_path):
    code = main(["route", "--graph", str(MINI), "--scenario-file",
                 str(tmp_path / "khong-co.json"), "--from", "S", "--to", "T"])
    err = capsys.readouterr().err
    assert code == 2
    assert err.startswith("Lỗi: không nạp được file kịch bản")

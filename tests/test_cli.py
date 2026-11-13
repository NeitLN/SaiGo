"""T12, A18: CLI tìm đường và lập tour (docs/tasks/T12-cli.md, PLAN mục 17 A18)."""

import json
from pathlib import Path
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


# --- A18: route --algo alt, bidijkstra, all ---

def test_route_algo_all_matches_costs(capsys):
    code, out, _ = run(capsys, "--from", "S", "--to", "T", "--algo", "all")
    assert code == 0
    for label in ("Dijkstra", "A*", "ALT", "Dijkstra hai chiều"):
        part = section(out, label)
        assert "Chi phí: 80.0 s" in part
        assert "Quãng đường: 800.0 m" in part
        assert "Tuyến: S → A → T" in part
    assert "Chi phí trùng khớp: có" in out
    assert "Chi phí ALT khớp Dijkstra: có" in out
    assert "Chi phí hai chiều khớp Dijkstra: có" in out


@pytest.mark.parametrize("algo,label", [("alt", "ALT"), ("bidijkstra", "Dijkstra hai chiều")])
def test_route_single_new_algos(capsys, algo, label):
    code, out, _ = run(capsys, "--from", "S", "--to", "T", "--algo", algo)
    assert code == 0
    assert "Chi phí: 80.0 s" in section(out, label)
    assert "[Dijkstra]" not in out
    assert "[A*]" not in out
    assert "trùng khớp" not in out


# --- A18: tour trên fixture và đối chứng ---

def test_tour_mini_manual_stops(capsys):
    # S = depot (10.77251, 106.69801), stops: B, A, T
    code = main([
        "tour",
        "--graph", str(MINI),
        "--depot", "10.77251,106.69801",
        "--stop", "10.77519,106.7016577", "10.77251,106.7016577", "10.77251,106.70532",
        "--scenario-file", str(SCENARIOS_MINI),
        "--optimal",
        "--or-opt",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "Đồ thị: mini (6 node, 8 cạnh)" in out
    assert "Số điểm giao: 3" in out
    for method in ("Thứ tự nhập", "Nearest Neighbor", "NN + 2-opt", "NN + 2-opt + Or-opt", "Held–Karp (tối ưu)"):
        assert method in out
    assert "280.0 s" in out
    assert "180.0 s" in out
    assert "* Phương án được chọn: Nearest Neighbor" in out
    assert "Thời gian tính ma trận:" in out
    assert "Sắp thứ tự:" in out


@pytest.mark.realdata
def test_tour_demo_case_kho_5_diem(capsys):
    root = Path(__file__).resolve().parents[1]
    manifest_p = root / "data" / "processed" / "manifest.json"
    if not manifest_p.exists():
        pytest.skip("Chưa có data/processed/manifest.json")
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    graph_p = root / manifest["file"]
    if not graph_p.exists():
        pytest.skip(f"Chưa có {manifest['file']}")

    code = main([
        "tour",
        "--graph", str(graph_p),
        "--case", "kho-5-diem",
        "--optimal",
        "--or-opt",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "Kho: Chợ Bến Thành" in out
    assert "Số điểm giao: 5" in out
    assert "Nhà thờ Đức Bà" in out
    assert "Công viên Tao Đàn" in out
    assert "1066.0 s" in out
    assert "627.8 s" in out
    assert "* Phương án được chọn: NN + 2-opt" in out
    assert "Thời gian tính ma trận:" in out
    assert "Sắp thứ tự:" in out


# --- A18: Lỗi rõ cho lệnh tour ---

def test_tour_case_not_found(capsys):
    code = main(["tour", "--case", "khong-ton-tai"])
    err = capsys.readouterr().err
    assert code == 2
    assert "không tìm thấy case demo 'khong-ton-tai'" in err


def test_tour_case_not_tour_mode(capsys):
    code = main(["tour", "--case", "hai-diem-qua-trung-tam"])
    err = capsys.readouterr().err
    assert code == 2
    assert "có mode 'route', không phải tour" in err


def test_tour_missing_depot(capsys):
    code = main(["tour", "--graph", str(MINI), "--stop", "10.1,106.1"])
    err = capsys.readouterr().err
    assert code == 2
    assert "cần truyền --case <id> hoặc tọa độ kho qua --depot lat,lon" in err


def test_tour_missing_stops(capsys):
    code = main(["tour", "--graph", str(MINI), "--depot", "10.1,106.1"])
    err = capsys.readouterr().err
    assert code == 2
    assert "cần ít nhất một điểm giao qua --stop lat,lon" in err


def test_tour_missing_graph_when_no_case(capsys):
    code = main(["tour", "--depot", "10.1,106.1", "--stop", "10.2,106.2"])
    err = capsys.readouterr().err
    assert code == 2
    assert "cần truyền file đồ thị qua --graph" in err


# --- A18: Trợ giúp tiếng Việt kèm ví dụ ---

@pytest.mark.parametrize("subcmd,kw", [
    (None, "Ví dụ sử dụng:"),
    ("route", "Ví dụ sử dụng lệnh route:"),
    ("check-heuristic", "Ví dụ sử dụng lệnh check-heuristic:"),
    ("tour", "Ví dụ sử dụng lệnh tour:"),
])
def test_cli_help_includes_vietnamese_examples(capsys, subcmd, kw):
    args = [subcmd, "--help"] if subcmd else ["--help"]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert kw in out

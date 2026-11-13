"""R2: tour sau khi đóng đường, giữ thứ tự cũ so với sắp lại (scripts/run_tour_closure.py)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "scripts", Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.graph.closures import reverse_twins  # noqa: E402
from app.graph.model import node_by_name  # noqa: E402
from helpers.random_graph import random_graph_dict  # noqa: E402
from mini_cases import edge_id, load_mini  # noqa: E402
from run_tour_closure import CLOSURE_COLUMNS, check_invariants, close_and_replan, main  # noqa: E402


def test_mini_closing_mid_edge_makes_tour_infeasible():
    """mini.json, kho S, điểm A, T, B: tour cũ = thứ tự nhập S→A→T→B→S 180 s (NN hòa nên giữ thứ tự nhập).
    Tuyến có 4 cạnh S→A, A→T, T→B, B→S; cạnh giữa ⌊4/2⌋ = T→B, đóng kèm cạnh đối B→T → T không còn cạnh ra."""
    graph, meta = load_mini()
    nodes = [node_by_name(meta, x) for x in ("S", "A", "T", "B")]
    r = close_and_replan(graph, meta, reverse_twins(graph, meta), nodes)
    assert r["old_method"] == "input" and r["old_cost"] == 180.0
    assert sorted(r["blocked"]) == sorted([edge_id(graph, meta, "T->B"), edge_id(graph, meta, "B->T")])
    assert r["feasible_after"] is False


def test_check_invariants_flags_cheaper_kept_order_and_blocked_edge():
    good = {"feasible_after": True, "old_cost": 100.0, "kept_cost": 120.0, "blocked": [7],
            "kept_edges": [1, 2], "reordered_edges": [3]}
    assert check_invariants([good]) == []
    cheaper = {**good, "kept_cost": 90.0}
    through = {**good, "reordered_edges": [7]}
    reasons = [b["reason"] for b in check_invariants([cheaper, through])]
    assert reasons == ["giữ thứ tự cũ rẻ hơn tour cũ", "tuyến đi qua cạnh đóng"]


def test_run_end_to_end_on_random_graph(tmp_path):
    g = random_graph_dict(seed=11, n_nodes=120, n_edges=480)
    path = tmp_path / "rand.json"
    path.write_text(json.dumps(g), encoding="utf-8")
    out = tmp_path / "results"
    assert main(["--graph", str(path), "--sizes", "4", "--sets", "6", "--seed", "42", "--min-sep", "150",
                 "--out", str(out), "--run-id", "r2"]) == 0
    run = out / "r2"
    with (run / "tour_closure.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and list(rows[0].keys()) == list(CLOSURE_COLUMNS)
    for r in rows:
        assert r["blocked_edges"]
        if r["feasible_after"] == "true":
            assert float(r["kept_cost_s"]) >= float(r["old_cost_s"]) - 1e-6
            assert r["order_changed"] in ("true", "false")
        else:
            assert r["kept_cost_s"] == "" and r["reordered_cost_s"] == ""
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    assert cfg["sizes"] == [4] and cfg["seed"] == 42
    assert not (run / "violations.json").exists()
    # Cùng seed → cùng bộ điểm và cùng kết quả
    assert main(["--graph", str(path), "--sizes", "4", "--sets", "6", "--seed", "42", "--min-sep", "150",
                 "--out", str(out), "--run-id", "r2b"]) == 0
    with (out / "r2b" / "tour_closure.csv").open(encoding="utf-8") as f:
        again = list(csv.DictReader(f))
    strip = lambda rs: [{k: v for k, v in r.items() if k != "run_id"} for r in rs]  # noqa: E731
    assert strip(again) == strip(rows)

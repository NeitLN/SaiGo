"""Tên đường cho từng cạnh (đánh giá dùng thử 16/11): bảng phụ từ GraphML thô, endpoint `/api/edge-names`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.graph.street_names import FORMAT, edge_names, load_street_names
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_street_names as bsn  # noqa: E402


def test_edge_names_first_named_way_wins():
    names = {10: "Lê Lợi", 20: "Hẻm 5"}
    assert edge_names([[10], [30, 20], [30], []], names) == ["Lê Lợi", "Hẻm 5", None, None]


def test_load_street_names_missing_or_bad_file_is_empty(tmp_path):
    assert load_street_names(tmp_path / "khong-co.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": "khac", "names": {"1": "A"}}', encoding="utf-8")
    assert load_street_names(bad) == {}
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"format": FORMAT, "names": {"1": "Đồng Khởi", "x": "B", "2": " "}}), encoding="utf-8")
    assert load_street_names(good) == {1: "Đồng Khởi"}


def test_parse_list_handles_osmnx_values():
    assert bsn.parse_list("123") == ["123"]
    assert bsn.parse_list("[1, 2]") == ["1", "2"]
    assert bsn.parse_list("['Nguyễn Tất Thành', 'Cầu Tân Thuận 2']") == ["Nguyễn Tất Thành", "Cầu Tân Thuận 2"]
    assert bsn.parse_list("") == []


GRAPHML = """<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="d11" for="edge" attr.name="osmid" attr.type="string" />
  <key id="d15" for="edge" attr.name="name" attr.type="string" />
  <graph edgedefault="directed">
    <node id="1" /><node id="2" />
    <edge source="1" target="2"><data key="d11">100</data><data key="d15">Lê Lợi</data></edge>
    <edge source="2" target="1"><data key="d11">100</data><data key="d15">Lê Lợi</data></edge>
    <edge source="1" target="2"><data key="d11">[200, 201]</data><data key="d15">Pasteur</data></edge>
    <edge source="1" target="2"><data key="d11">[300, 301]</data><data key="d15">['A', 'B']</data></edge>
    <edge source="1" target="2"><data key="d11">400</data></edge>
  </graph>
</graphml>
"""


def test_collect_names_only_unambiguous(tmp_path):
    f = tmp_path / "g.graphml"
    f.write_text(GRAPHML, encoding="utf-8")
    # 300/301 có hai tên không rõ thứ tự nên bỏ; 400 không có tên.
    assert bsn.collect_names(f) == {100: "Lê Lợi", 200: "Pasteur", 201: "Pasteur"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    monkeypatch.setenv("SAIGO_STREET_NAMES", str(tmp_path / "khong-co.json"))
    with TestClient(app) as c:
        yield c


def test_edge_names_endpoint_one_entry_per_edge(client):
    body = client.get("/api/edge-names").json()
    assert body["dataset_id"]
    assert len(body["names"]) == 8          # mini.json có 8 cạnh, không có way_ids nên không có tên
    assert all(n is None for n in body["names"])


@pytest.mark.realdata
def test_street_names_file_covers_demo_graph():
    names = load_street_names(ROOT / "data/processed/street-names-20261024.json")
    graph_file = ROOT / "data/processed/hcm-benthanh-r2000-20261024.json"
    if not names or not graph_file.is_file():
        pytest.skip("cần bảng tên đường và đồ thị demo")
    edges = json.loads(graph_file.read_text(encoding="utf-8"))["edges"]
    named = sum(1 for e in edges if any(w in names for w in e.get("way_ids", [])))
    assert named / len(edges) > 0.75

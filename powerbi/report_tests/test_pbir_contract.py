from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT.parent / "ApexIndustrialIoT.Report"
DEFINITION = REPORT / "definition"
PAGE_RE = re.compile(r"^[0-9a-f]{20}$")
VISUAL_RE = re.compile(r"^[0-9a-f]{20}$")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pbip_and_report_binding_exist() -> None:
    pbip = read_json(ROOT.parent / "ApexIndustrialIoT.pbip")
    pbir = read_json(REPORT / "definition.pbir")
    assert pbip["artifacts"][0]["report"]["path"] == "ApexIndustrialIoT.Report"
    assert pbir["version"] == "4.0"
    assert pbir["datasetReference"]["byPath"]["path"] == "../ApexIndustrialIoT.SemanticModel"


def test_pbir_metadata_files_exist() -> None:
    assert (DEFINITION / "report.json").is_file()
    assert (DEFINITION / "version.json").is_file()
    assert (DEFINITION / "pages" / "pages.json").is_file()
    assert (REPORT / ".platform").is_file()


def test_page_registry_and_page_files_are_consistent() -> None:
    pages = read_json(DEFINITION / "pages" / "pages.json")
    order = pages["pageOrder"]
    assert len(order) == 7
    assert pages["activePageName"] == order[0]
    for page_id in order:
        assert PAGE_RE.fullmatch(page_id)
        page = read_json(DEFINITION / "pages" / page_id / "page.json")
        assert page["name"] == page_id
        assert 0 < page["width"] <= 1280
        assert 0 < page["height"] <= 720


def test_visual_ids_are_20_hex_and_positions_fit_canvas() -> None:
    for page_id in read_json(DEFINITION / "pages" / "pages.json")["pageOrder"]:
        page_dir = DEFINITION / "pages" / page_id
        page = read_json(page_dir / "page.json")
        for visual_file in page_dir.glob("visuals/*/visual.json"):
            visual_id = visual_file.parent.name
            assert VISUAL_RE.fullmatch(visual_id)
            visual = read_json(visual_file)
            position = visual["position"]
            assert position["x"] >= 0
            assert position["y"] >= 0
            assert position["x"] + position["width"] <= page["width"]
            assert position["y"] + position["height"] <= page["height"]


def test_visual_types_and_business_annotations_are_present() -> None:
    allowed = {"cardVisual", "barChart", "lineChart", "slicer"}
    count = 0
    for visual_file in DEFINITION.glob("pages/*/visuals/*/visual.json"):
        visual = read_json(visual_file)
        assert visual["visual"]["visualType"] in allowed
        assert visual["annotations"]
        count += 1
    assert count >= 20


def test_machine_detail_is_real_drillthrough_page() -> None:
    page_id = "6fc2b4d9e7a3c365d850"
    page = read_json(DEFINITION / "pages" / page_id / "page.json")
    assert page["visibility"] == "HiddenInViewMode"
    assert page["pageBinding"]["type"] == "Drillthrough"
    assert page["filterConfig"]["filters"][0]["howCreated"] == "Drillthrough"
    assert page["filterConfig"]["filters"][0]["field"]["Column"]["Property"] == "machine_id"


def test_machine_tooltip_page_exists() -> None:
    page = read_json(DEFINITION / "pages/7ad3c5e7f90123456789/page.json")
    assert page["visibility"] == "HiddenInViewMode"
    assert page["pageBinding"]["type"] == "Tooltip"


def test_interaction_contract_covers_navigation_drillthrough_and_rls() -> None:
    interaction = (ROOT / "report_interactions.yaml").read_text(encoding="utf-8")
    assert "drillthrough:" in interaction
    assert "tooltips:" in interaction
    assert "bookmarks:" in interaction
    assert "preserve_rls_filters: true" in interaction


def test_report_blueprint_and_deployment_contract_exist() -> None:
    blueprint = (ROOT / "report_blueprint.yaml").read_text(encoding="utf-8")
    deployment = (ROOT / "deployment/semantic_model_deployment.yaml").read_text(encoding="utf-8")
    assert "Executive Overview" in blueprint
    assert "Machine Health" in blueprint
    assert "ApexIndustrialIoT" in deployment
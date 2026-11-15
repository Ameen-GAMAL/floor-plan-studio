"""Acceptance checks exercise real solves and independently corrupted exports."""
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.generator import generate
from app.main import app
from app.models import Brief, Layout, brief_hash
from app.presets import preset
from app.validator import validate

EXAMPLES=Path(__file__).resolve().parents[1]/"examples"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def baseline():
    brief=preset()
    result=generate(brief)
    assert result["search_status"]=="feasible",result
    return brief,result["layout"]


def statuses(report):
    return {c.id:c.status for c in report.checks}


@pytest.mark.parametrize("name,room_count",[("baseline",5),("changed",5),("alternative",6)])
def test_real_input_scenarios(client,name,room_count):
    brief=Brief.model_validate_json((EXAMPLES/f"{name}.json").read_text(encoding="utf-8"))
    response=client.post("/api/generate",json=brief.model_dump(mode="json"))
    assert response.status_code==200
    result=response.json()
    assert result["search_status"]=="feasible",result
    assert result["validation_status"]=="passed",result
    assert len(result["layout"]["rooms"])==room_count
    assert all(c["status"]=="pass" for c in result["report"]["checks"] if c["classification"]=="hard")
    ledger=result["report"]["area_ledger_m2"]
    assert ledger["uncovered"]==ledger["outside"]==ledger["duplicated"]==0
    assert ledger["partition_total"]==ledger["gross"]
    assert result["brief_hash"]==brief_hash(brief)
    assert result["elapsed_seconds"]<30
    assert result["regulatory_status"]=="unverified"
    assert any(c["status"]=="unverified" and c["implementation_status"]=="not_implemented" for c in result["report"]["checks"])
    if name=="changed":
        schedule={r["id"]:r for r in result["report"]["room_schedule"]}
        assert schedule["meeting"]["area_m2"]>=24
        assert schedule["office_a"]["area_m2"]>=16
        assert schedule["office_b"]["area_m2"]>=16
    if name=="alternative":
        assert "office_c" in {r["id"] for r in result["layout"]["rooms"]}


def test_necessary_area_conflict(client):
    result=client.post("/api/generate",json=preset("impossible").model_dump(mode="json")).json()
    assert result["search_status"]=="infeasible"
    assert result["layout"] is None and result["validation_status"]=="not_run"
    assert result["explanation"]["kind"]=="necessary_condition"
    assert result["explanation"]["required_m2"]==172
    assert result["explanation"]["available_m2"]==149.76
    assert result["brief"]["rooms"][-1]["min_area_m2"]==100
    assert result["brief"]["rooms"][-1]["max_area_m2"] is None


def test_solver_conflict_is_scoped_and_traceable(client):
    brief=preset()
    brief.rooms[-1].min_area_m2=28
    brief.rooms[-1].target_area_m2=28
    result=client.post("/api/generate",json=brief.model_dump(mode="json")).json()
    assert result["search_status"]=="infeasible",result
    assert result["explanation"]["kind"]=="solver_proof"
    assert result["explanation"]["requirement_ids"]
    assert "two" in result["explanation"]["scope"]
    assert result["layout"] is None


@pytest.mark.parametrize("mutation,expected",[
    ("narrow_door","R-APERTURE"),("remove_door","R-CONNECT"),
    ("overlap","R-NO-OVERLAP"),("move_core","R-FIXED"),
    ("remove_desk","R-FURN"),("false_edge","R-CONNECT"),
    ("uncovered_wall","R-ACCOUNT"),
])
def test_independent_validator_rejects_damaged_exports(baseline,mutation,expected):
    brief,original=baseline
    layout=original.model_copy(deep=True)
    if mutation=="narrow_door":
        door=next(d for d in layout.doors if d.id=="door_meeting")
        x1,y1=door.polygon[0]
        y2=door.polygon[2][1]
        door.polygon=[(x1,y1),(x1+800,y1),(x1+800,y2),(x1,y2),(x1,y1)]
    elif mutation=="remove_door":
        layout.doors=[d for d in layout.doors if d.id!="door_meeting"]
    elif mutation=="overlap":
        layout.rooms[1].polygon=deepcopy(layout.rooms[0].polygon)
    elif mutation=="move_core":
        layout.core.polygon=[(x-100,y) for x,y in layout.core.polygon]
    elif mutation=="remove_desk":
        index=next(i for i,f in enumerate(layout.furniture) if f.kind=="desk")
        layout.furniture.pop(index)
    elif mutation=="false_edge":
        layout.doors[0].connects=("meeting","outside")
    elif mutation=="uncovered_wall":
        layout.walls.pop()
    layout.metadata.update(all_constraints_satisfied=True,area_total=160,validator_passed=True)
    report=validate(brief,layout)
    assert report.validation_status=="failed"
    assert statuses(report)[expected]=="fail"


def test_changed_brief_rejects_old_geometry_and_export(client,baseline):
    brief,layout=baseline
    revised=brief.model_copy(deep=True)
    revised.revision+=1
    revised.rooms[-1].min_area_m2=24
    payload=dict(brief=revised.model_dump(mode="json"),layout=layout.model_dump(mode="json"))
    report=client.post("/api/validate",json=payload).json()
    assert report["validation_status"]=="failed"
    assert {c["id"]:c["status"] for c in report["checks"]}["R-REV"]=="fail"
    assert client.post("/api/export/svg",json=payload).status_code==422


def test_unknown_is_not_infeasible(client):
    brief=preset()
    brief.solver.time_limit_seconds=0
    result=client.post("/api/generate",json=brief.model_dump(mode="json")).json()
    assert result["search_status"]=="unknown"
    assert result["explanation"]["kind"]=="unresolved_search"
    assert result["layout"] is None
    assert result["brief"]["rooms"]==brief.model_dump(mode="json")["rooms"]


@pytest.mark.parametrize("change",[{"units":None},{"width":-1},{"contradictory":True}])
def test_specific_input_errors(client,change):
    data=preset().model_dump(mode="json")
    if "units" in change:
        del data["units"]
    if "width" in change:
        data["floor"]["width_mm"]=change["width"]
    if "contradictory" in change:
        data["rooms"][-1]["min_area_m2"]=30
        data["rooms"][-1]["max_area_m2"]=28
    response=client.post("/api/generate",json=data)
    assert response.status_code==422
    result=response.json()
    assert result["search_status"]=="invalid_input"
    assert result["errors"] and all(e["field"] and e["message"] for e in result["errors"])
    if "contradictory" in change:
        assert "minimum area exceeds maximum" in result["errors"][0]["message"]


@pytest.mark.parametrize("kind",["obstruction","corridor","raw_grid"])
def test_unsupported_is_not_infeasible(client,kind):
    brief=preset()
    if kind=="obstruction":
        from app.models import Rect
        brief.fixed.other_obstructions=[Rect(x1=2000,y1=2000,x2=2500,y2=2500)]
    elif kind=="corridor":
        brief.fixed.corridor.x1=300
    else:
        brief.fixed.core.x1=12525
    result=client.post("/api/generate",json=brief.model_dump(mode="json")).json()
    assert result["search_status"]=="unsupported"
    assert result["layout"] is None
    assert result["brief"]["fixed"]==brief.model_dump(mode="json")["fixed"]


@pytest.mark.parametrize("kind",["wall_adjacent","door_connected"])
def test_wall_adjacency_is_distinct_from_direct_door(client,kind):
    data=preset().model_dump(mode="json")
    data["relationships"]=[dict(id="pair",a="office_a",b="office_b",kind=kind,mandatory=True)]
    result=client.post("/api/generate",json=data).json()
    assert result["validation_status"]=="passed",result
    relation=next(c for c in result["report"]["checks"] if c["id"]=="R-REL-pair")
    assert relation["status"]=="pass"
    assert relation["measured"]["shared_wall_length_mm"]>0
    assert relation["measured"]["direct_door"]==(kind=="door_connected")
    if kind=="door_connected":
        damaged=Layout.model_validate(result["layout"])
        damaged.doors=[d for d in damaged.doors if d.id!="door_rel_pair"]
        measured=validate(Brief.model_validate(data),damaged)
        assert statuses(measured)["R-REL-pair"]=="fail"


def test_exports_are_current_measured_geometry(client,baseline):
    brief,layout=baseline
    payload=dict(brief=brief.model_dump(mode="json"),layout=layout.model_dump(mode="json"))
    response=client.post("/api/export/svg",json=payload)
    assert response.status_code==200
    import xml.etree.ElementTree as ET
    root=ET.fromstring(response.text)
    namespace={"s":"http://www.w3.org/2000/svg"}
    room_nodes=root.findall(".//s:g[@data-room]",namespace)
    assert {g.attrib["data-room"] for g in room_nodes}=={r.id for r in layout.rooms}
    for room in layout.rooms:
        group=next(g for g in room_nodes if g.attrib["data-room"]==room.id)
        points=group.find("s:polygon",namespace).attrib["points"]
        assert points==" ".join(f"{x},{y}" for x,y in room.polygon)
    assert "UNVERIFIED" in response.text
    assert "16.00 m OUTSIDE" in response.text


def test_invalid_polygon_cannot_be_certified(baseline):
    brief,original=baseline
    layout=original.model_copy(deep=True)
    layout.rooms[0].polygon=[(0,0),(1000,1000),(0,1000),(1000,0),(0,0)]
    report=validate(brief,layout)
    assert report.validation_status=="failed"
    assert statuses(report)["R-GEOMETRY"]=="fail"
    assert statuses(report)["R-ACCOUNT"]=="unverified"


def test_fixed_seed_repeated_input_is_valid_and_reproducible(baseline):
    brief,layout=baseline
    again=generate(brief)["layout"]
    assert [r.polygon for r in again.rooms]==[r.polygon for r in layout.rooms]
    assert validate(brief,again).validation_status=="passed"


def test_served_app_has_no_remote_frontend_assets(client):
    response=client.get("/")
    assert response.status_code==200
    assert client.get("/static/app.js").status_code==200
    assert client.get("/static/styles.css").status_code==200
    from html.parser import HTMLParser
    class Assets(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for key,value in attrs:
                if tag in {"script","link","img","iframe"} and key in {"src","href"}:
                    assert not value.startswith(("http:","https:","//"))
    Assets().feed(response.text)


def test_duplicate_relationships_share_a_single_physical_aperture(client):
    data=preset().model_dump(mode="json")
    data["relationships"]=[dict(id=name,a="office_a",b="office_b",kind="door_connected",mandatory=True) for name in ["one","two"]]
    result=client.post("/api/generate",json=data).json()
    assert result["validation_status"]=="passed",result
    direct=[d for d in result["layout"]["doors"] if set(d["connects"])=={"office_a","office_b"}]
    assert len(direct)==1


def test_validator_does_not_ignore_obstructions_in_an_imported_brief(baseline):
    from app.models import Rect
    brief,layout=baseline
    revised=brief.model_copy(deep=True)
    revised.fixed.other_obstructions=[Rect(x1=2000,y1=2000,x2=2500,y2=2500)]
    imported=layout.model_copy(deep=True)
    imported.brief_hash=brief_hash(revised)
    report=validate(revised,imported)
    assert report.validation_status=="failed"
    assert statuses(report)["R-FIXED"]=="fail"


def test_candidate_failing_independent_checks_is_never_released(client,baseline,monkeypatch):
    import app.main as main
    brief,layout=baseline
    damaged=layout.model_copy(deep=True)
    damaged.doors=[d for d in damaged.doors if d.id!="door_meeting"]
    monkeypatch.setattr(main,"generate",lambda _:dict(search_status="feasible",optimality="not_proven",layout=damaged,message="Candidate"))
    result=client.post("/api/generate",json=brief.model_dump(mode="json")).json()
    assert result["search_status"]=="feasible"
    assert result["validation_status"]=="failed"
    assert result["layout"] is None and result["svg"] is None
    assert result["report"]["validation_status"]=="failed"

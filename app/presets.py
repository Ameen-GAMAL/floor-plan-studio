"""Saved inputs, never saved solver outputs."""
from copy import deepcopy

from .models import Brief


def preset(name: str = "baseline") -> Brief:
    rooms = [
        dict(id="reception", name="Reception", kind="reception", capacity=1, min_area_m2=16, target_area_m2=19, max_area_m2=22),
        dict(id="workroom", name="Shared workroom", kind="workroom", capacity=4, min_area_m2=24, target_area_m2=27, max_area_m2=32),
        dict(id="office_a", name="Private office A", kind="office", capacity=1, min_area_m2=16, target_area_m2=19, max_area_m2=22),
        dict(id="office_b", name="Private office B", kind="office", capacity=1, min_area_m2=16, target_area_m2=19, max_area_m2=22),
        dict(id="meeting", name="Meeting room", kind="meeting", capacity=6, min_area_m2=18, target_area_m2=21, max_area_m2=28),
    ]
    data = dict(
        schema_version="1.0", revision=1, units="mm", building_use="small_office",
        project_name="Small office study", location=None,
        floor=dict(width_mm=16000, depth_mm=10000),
        fixed=dict(
            corridor=dict(x1=200, y1=4100, x2=15800, y2=5900),
            core=dict(x1=12500, y1=200, x2=15800, y2=4000),
            exterior_openings=[
                dict(id="entry_west", x1=0, y1=4550, x2=200, y2=5450),
                dict(id="opening_east", x1=15800, y1=4550, x2=16000, y2=5450),
            ], other_obstructions=[]),
        rooms=deepcopy(rooms), relationships=[], priority="balanced", rules={}, solver={},
    )
    if name == "changed":
        data["rooms"][-1].update(min_area_m2=24, target_area_m2=24)
        data["project_name"] = "Meeting room expanded"
    elif name == "impossible":
        data["rooms"][-1].update(min_area_m2=100, target_area_m2=100, max_area_m2=None)
        data["project_name"] = "Area conflict demonstration"
    elif name == "alternative":
        # A larger compatible shell and a third office; all fixed coordinates are explicit.
        data["floor"].update(width_mm=21000)
        data["fixed"]["corridor"]["x2"] = 20800
        data["fixed"]["core"].update(x1=17500, x2=20800)
        data["fixed"]["exterior_openings"][1].update(x1=20800, x2=21000)
        data["rooms"].insert(4, dict(id="office_c", name="Private office C", kind="office", capacity=1,
                                      min_area_m2=16, target_area_m2=22, max_area_m2=28))
        for r in data["rooms"]:
            if r["kind"] != "meeting":
                r["max_area_m2"] = 45
        data["project_name"] = "Three-office input sensitivity"
    elif name != "baseline":
        raise KeyError(name)
    return Brief.model_validate(data)

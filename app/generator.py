"""CP-SAT strip-family generation. The validator does not import this module."""
from __future__ import annotations

import importlib.metadata
import json
import math
import time
from pathlib import Path

from ortools.sat.python import cp_model
from shapely.geometry import box
from shapely.ops import unary_union

from .models import Brief, Door, Furniture, Layout, PolygonItem, Space, brief_hash

MODEL_VERSION = "office-strips-1.0"
CATALOGUE = json.loads(Path(__file__).with_name("templates.json").read_text(encoding="utf-8"))["templates"]


def ring(x1, y1, x2, y2):
    return [(int(x1), int(y1)), (int(x2), int(y1)), (int(x2), int(y2)), (int(x1), int(y2)), (int(x1), int(y1))]


def rect_poly(r):
    return ring(r.x1, r.y1, r.x2, r.y2)


def domain(brief: Brief):
    """Return supported banks or an explicit limit. Preserve every fixed coordinate."""
    f, fixed, g = brief.floor, brief.fixed, brief.rules.grid_mm
    t, w, h, it = f.external_wall_mm, f.width_mm, f.depth_mm, f.internal_wall_mm
    c, core = fixed.corridor, fixed.core
    if fixed.other_obstructions:
        return None, "Interior obstructions are outside the supported two-bank family. Their coordinates were retained."
    vals = [w, h, t, it, *c.model_dump().values(), *core.model_dump().values()]
    vals += [v for o in fixed.exterior_openings for k, v in o.model_dump().items() if k != "id"]
    if any(v % g for v in vals) or brief.rules.min_aperture_mm % g:
        return None, f"Fixed coordinates, wall thicknesses and aperture width must align with the declared {g} mm grid; coordinates were not rounded."
    if c.x1 != t or c.x2 != w - t or not t < c.y1 - it < c.y2 + it < h - t:
        return None, "The fixed corridor must span the inside shell and leave a room bank and explicit wall on each side."
    banks = [[t, t, w - t, c.y1 - it], [t, c.y2 + it, w - t, h - t]]
    core_bank = None
    for b, bounds in enumerate(banks):
        left, top, right, bottom = bounds
        if core.y1 == top and core.y2 == bottom:
            if core.x1 == left and core.x2 < right - it:
                bounds[0] = core.x2 + it
                core_bank = b
            elif core.x2 == right and core.x1 > left + it:
                bounds[2] = core.x1 - it
                core_bank = b
    if core_bank is None:
        return None, "The service reserve must occupy one complete bank depth at its left or right end. No fixed element was moved."
    for o in fixed.exterior_openings:
        side = (o.x1 == 0 and o.x2 == t) or (o.x1 == w - t and o.x2 == w)
        if not side or o.y1 < c.y1 or o.y2 > c.y2:
            return None, f"{o.id}: supported exterior openings cross the west/east wall directly into the fixed corridor."
    if any(rel.kind == "near" and rel.mandatory for rel in brief.relationships):
        return None, "Proximity is a ranked preference in this version. Use explicit shared-wall adjacency or direct door connectivity for a mandatory relationship."
    return (banks, core_bank), None


def _template_items(spec, bounds, bank, orientation):
    tpl = CATALOGUE[f"{spec.kind}_{spec.capacity}"]
    tw, td = tpl["width"], tpl["depth"]
    if orientation:
        tw, td = td, tw
    x0 = bounds[0] + (bounds[2] - bounds[0] - tw) // 2
    out = []
    for index, (kind, label, x, y, w, h) in enumerate(tpl["items"]):
        if orientation:
            x, y, w, h = tpl["depth"] - y - h, x, h, w
        fy = bounds[1] + 200 + y if bank == 0 else bounds[3] - 200 - y - h
        out.append(Furniture(id=f"f_{spec.id}_{index}", room_id=spec.id, kind=kind, label=label,
                             polygon=ring(x0 + x, fy, x0 + x + w, fy + h)))
    return out


def generate(brief: Brief):
    started = time.perf_counter()
    scope = f"{brief.rules.grid_mm} mm grid; rectangular rooms; two fully tiled banks; fixed corridor/core"
    geometry, limit = domain(brief)
    if limit:
        return dict(search_status="unsupported", message=limit, explanation={"scope": scope, "requirement_ids": ["R-FIXED", "R-GRID"]})
    banks, core_bank = geometry
    f, rules = brief.floor, brief.rules
    inner = (f.width_mm - 2 * f.external_wall_mm) * (f.depth_mm - 2 * f.external_wall_mm) / 1e6
    minimum = sum(r.min_area_m2 for r in brief.rooms)
    if minimum > inner:
        return dict(search_status="infeasible", message=f"Room minimums require {minimum:.2f} m², but the entire inside shell has only {inner:.2f} m².",
                    explanation=dict(kind="necessary_condition", scope="Inside-shell area, even before reserving circulation, services and partitions",
                                     required_m2=minimum, available_m2=inner, deficit_m2=minimum-inner,
                                     requirement_ids=[f"R-AREA-{r.id}" for r in brief.rooms], suggestions=["Reduce explicitly selected room minimums or increase the measured footprint. Mandatory bounds were retained."]))
    for o in brief.fixed.exterior_openings:
        if o.y2 - o.y1 < rules.min_aperture_mm:
            return dict(search_status="infeasible", message=f"{o.id} is fixed at {o.y2-o.y1} mm clear; the brief requires at least {rules.min_aperture_mm} mm.", explanation={"kind": "necessary_condition", "scope": "Fixed aperture versus requested width", "requirement_ids": ["R-APERTURE", "R-OPENINGS"]})
    if brief.fixed.corridor.y2 - brief.fixed.corridor.y1 < rules.min_corridor_mm:
        return dict(search_status="infeasible", message="The fixed corridor is narrower than the approved corridor-width requirement.", explanation={"kind": "necessary_condition", "requirement_ids": ["R-CORRIDOR", "R-FIXED"]})

    model = cp_model.CpModel()
    grid, wall = rules.grid_mm, f.internal_wall_mm // rules.grid_mm
    maxunits = f.width_mm // grid
    records, intervals, packed = {}, [[], []], [[], []]
    assumptions = {}

    def assumption(identifier):
        lit = model.new_bool_var(identifier)
        model.add_assumption(lit)
        assumptions[lit.index] = identifier
        return lit

    area_cost, secondary = [], []
    for i, spec in enumerate(brief.rooms):
        bank = model.new_bool_var(f"bank_{spec.id}")
        width = model.new_int_var(1, maxunits, f"width_{spec.id}")
        x = model.new_int_var(0, maxunits, f"x_{spec.id}")
        end = model.new_int_var(0, maxunits + wall, f"end_{spec.id}")
        size = model.new_int_var(1 + wall, maxunits + wall, f"interval_{spec.id}")
        area = model.new_int_var(0, f.width_mm * f.depth_mm, f"area_{spec.id}")
        orientation = model.new_bool_var(f"template_rotation_{spec.id}")
        tpl = CATALOGUE[f"{spec.kind}_{spec.capacity}"]
        allowed = []
        for b, bounds in enumerate(banks):
            depth = bounds[3] - bounds[1]
            for wu in range(1, (bounds[2] - bounds[0]) // grid + 1):
                ww = wu * grid
                if min(ww, depth) < rules.min_short_side_mm or max(ww, depth) > rules.max_aspect_ratio * min(ww, depth):
                    continue
                for orient in [0, 1]:
                    tw, td = (tpl["depth"], tpl["width"]) if orient else (tpl["width"], tpl["depth"])
                    if ww >= tw + 300 and depth >= td + 200 + rules.min_aperture_mm:
                        allowed.append([b, wu, ww * depth, orient])
        if not allowed:
            return dict(search_status="infeasible", message=f"{spec.name}: no room dimensions in either fixed bank fit the requested dimensional rules and indicative furniture template.", explanation={"kind": "exhaustive_room_domain", "scope": scope, "requirement_ids": [f"R-DIM-{spec.id}", "R-FURN", "R-FIXED"]})
        model.add_allowed_assignments([bank, width, area, orientation], allowed)
        area_lit = assumption(f"R-AREA-{spec.id}")
        model.add(area >= math.ceil(spec.min_area_m2 * 1e6 - 1e-6)).only_enforce_if(area_lit)
        if spec.max_area_m2 is not None:
            model.add(area <= math.floor(spec.max_area_m2 * 1e6 + 1e-6)).only_enforce_if(area_lit)
        model.add(size == width + wall)
        model.add(end == x + size)
        presence = [bank.Not(), bank]
        for b, bounds in enumerate(banks):
            model.add(x >= bounds[0] // grid).only_enforce_if(presence[b])
            model.add(x + width <= bounds[2] // grid).only_enforce_if(presence[b])
            intervals[b].append(model.new_optional_interval_var(x, size, end, presence[b], f"slot_{spec.id}_{b}"))
            used = model.new_int_var(0, maxunits + wall, f"used_{spec.id}_{b}")
            model.add(used == size).only_enforce_if(presence[b])
            model.add(used == 0).only_enforce_if(presence[b].Not())
            packed[b].append(used)
        deviation = model.new_int_var(0, f.width_mm * f.depth_mm + math.ceil(spec.target_area_m2*1e6), f"deviation_{spec.id}")
        model.add_abs_equality(deviation, area - round(spec.target_area_m2 * 1e6))
        area_cost.append(deviation)
        desired = 0 if spec.kind in {"reception", "workroom"} else 1
        if brief.priority == "privacy" and spec.kind == "meeting":
            desired = 0
        zoning_cost = 100000 if brief.priority != "area" else 100
        secondary.append((bank if desired == 0 else 1 - bank) * zoning_cost)
        secondary.append(x * (len(brief.rooms) - i))
        offset = model.new_int_var(1, 3, f"door_offset_{spec.id}")
        model.add(offset + rules.min_aperture_mm // grid <= width - 1)
        secondary.append(offset)
        records[spec.id] = dict(spec=spec, bank=bank, width=width, x=x, area=area, orientation=orientation, offset=offset)

    for b, bounds in enumerate(banks):
        model.add_no_overlap(intervals[b])
        # Interval includes the following partition. Equality makes each bank a complete tiling.
        model.add(sum(packed[b]) == (bounds[2] - bounds[0]) // grid + wall)
        model.add(sum(r["bank"] if b else 1-r["bank"] for r in records.values()) >= 1)

    for rel in brief.relationships:
        a, b = records[rel.a], records[rel.b]
        if rel.kind in {"wall_adjacent", "door_connected"}:
            matched = assumption(f"R-REL-{rel.id}") if rel.mandatory else model.new_bool_var(f"prefer_{rel.id}")
            order = model.new_bool_var(f"order_{rel.id}")
            model.add(a["bank"] == b["bank"]).only_enforce_if(matched)
            model.add(a["x"] + a["width"] + wall == b["x"]).only_enforce_if([matched, order])
            model.add(b["x"] + b["width"] + wall == a["x"]).only_enforce_if([matched, order.Not()])
            if not rel.mandatory:
                secondary.append((1-matched) * 500000)
        else:
            dx = model.new_int_var(0, 2*maxunits, f"near_x_{rel.id}")
            model.add_abs_equality(dx, 2*a["x"]+a["width"]-2*b["x"]-b["width"])
            different = model.new_bool_var(f"near_bank_{rel.id}")
            model.add(a["bank"] != b["bank"]).only_enforce_if(different)
            model.add(a["bank"] == b["bank"]).only_enforce_if(different.Not())
            secondary.extend([dx*10, different*10000])

    model.minimize(sum(area_cost)*100000 + sum(secondary))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = brief.solver.time_limit_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = brief.solver.seed
    status = solver.solve(model)
    if status == cp_model.INFEASIBLE:
        identifiers = [assumptions.get(i, str(i)) for i in solver.sufficient_assumptions_for_infeasibility()]
        return dict(search_status="infeasible", message="No layout satisfies all mandatory requirements in the declared grid and two-bank model.",
                    explanation=dict(kind="solver_proof", scope=scope, requirement_ids=identifiers,
                                     note="This sufficient conflict set is not guaranteed minimal. It does not prove infeasibility for unrestricted architecture.",
                                     suggestions=["Review listed area bounds and relationships, or revise fixed geometry. No mandatory requirement was relaxed."]))
    if status == cp_model.UNKNOWN:
        return dict(search_status="unknown", message="Search ended without a feasible candidate or proof of infeasibility. Your requirements were retained.", explanation={"kind": "unresolved_search", "scope": scope, "time_limit_seconds": brief.solver.time_limit_seconds})
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return dict(search_status="error", message="The solver could not process the encoded model. See the local application log.", explanation={"kind": "solver_model_error", "status": solver.status_name(status), "detail": model.validate()})

    rooms, furniture, doors, bank_contents = [], [], [], [[], []]
    coords = {}
    c, core = brief.fixed.corridor, brief.fixed.core
    for rec in records.values():
        spec = rec["spec"]
        b = solver.value(rec["bank"])
        x1 = solver.value(rec["x"]) * grid
        bounds = [x1, banks[b][1], x1+solver.value(rec["width"])*grid, banks[b][3]]
        coords[spec.id] = (bounds, b)
        rooms.append(Space(id=spec.id, name=spec.name, kind=spec.kind, capacity=spec.capacity, polygon=ring(*bounds)))
        bank_contents[b].append(bounds)
        furniture.extend(_template_items(spec, bounds, b, solver.value(rec["orientation"])))
        dx = x1 + solver.value(rec["offset"]) * grid
        yy = (c.y1 - f.internal_wall_mm, c.y1) if b == 0 else (c.y2, c.y2 + f.internal_wall_mm)
        doors.append(Door(id=f"door_{spec.id}", connects=(spec.id, "corridor"), polygon=ring(dx, yy[0], dx+rules.min_aperture_mm, yy[1])))
    bank_contents[core_bank].append([core.x1, core.y1, core.x2, core.y2])
    yy = (c.y1 - f.internal_wall_mm, c.y1) if core_bank == 0 else (c.y2, c.y2 + f.internal_wall_mm)
    if core.x2 - core.x1 < rules.min_aperture_mm + 2*grid:
        return dict(search_status="infeasible", message="The fixed core frontage cannot contain the declared aperture and modeled jambs.", explanation={"kind": "necessary_condition", "requirement_ids": ["R-FIXED", "R-APERTURE"]})
    doors.append(Door(id="door_core", connects=("core", "corridor"), polygon=ring(core.x1+grid, yy[0], core.x1+grid+rules.min_aperture_mm, yy[1])))
    direct_pairs = set()
    for rel in brief.relationships:
        if rel.kind != "door_connected":
            continue
        pair = tuple(sorted((rel.a, rel.b)))
        if pair in direct_pairs:
            continue
        direct_pairs.add(pair)
        aa, abank = coords[rel.a]
        bb, bbank = coords[rel.b]
        left, right = sorted([aa, bb], key=lambda z:z[0])
        if abank == bbank and right[0] - left[2] == f.internal_wall_mm:
            dy = left[1] + grid
            doors.append(Door(id=f"door_rel_{rel.id}", connects=(rel.a, rel.b), polygon=ring(left[2], dy, right[0], dy+rules.min_aperture_mm)))
    doors.extend(Door(id=o.id, connects=("corridor", "outside"), polygon=rect_poly(o)) for o in brief.fixed.exterior_openings)

    t, w, h, it = f.external_wall_mm, f.width_mm, f.depth_mm, f.internal_wall_mm
    wall_boxes = [box(0,0,w,t), box(0,h-t,w,h), box(0,t,t,h-t), box(w-t,t,w,h-t),
                  box(t,c.y1-it,w-t,c.y1), box(t,c.y2,w-t,c.y2+it)]
    for contents in bank_contents:
        ordered = sorted(contents, key=lambda z:z[0])
        for left, right in zip(ordered, ordered[1:]):
            wall_boxes.append(box(left[2],left[1],right[0],left[3]))
    apertures = unary_union([box(*[min(x for x,y in d.polygon), min(y for x,y in d.polygon), max(x for x,y in d.polygon), max(y for x,y in d.polygon)]) for d in doors])
    walls = []
    for band in wall_boxes:
        remaining = band.difference(apertures)
        parts = list(remaining.geoms) if remaining.geom_type == "MultiPolygon" else [remaining]
        for piece in parts:
            if not piece.is_empty:
                walls.append(PolygonItem(id=f"wall_{len(walls)+1}", polygon=[(round(x),round(y)) for x,y in piece.exterior.coords]))
    layout = Layout(brief_revision=brief.revision, brief_hash=brief_hash(brief), grid_mm=grid, model_version=MODEL_VERSION,
                    rooms=rooms, corridor=Space(id="corridor", name="Circulation", kind="corridor", polygon=rect_poly(c)),
                    core=Space(id="core", name="Service reserve", kind="core", polygon=rect_poly(core)),
                    walls=walls, doors=doors, furniture=furniture,
                    metadata=dict(solver_status=solver.status_name(status), seed=brief.solver.seed, workers=1,
                                  time_limit_seconds=brief.solver.time_limit_seconds, solve_seconds=round(solver.wall_time,6),
                                  generator_seconds=round(time.perf_counter()-started,6), objective_value=solver.objective_value,
                                  objective_scope="Absolute target-area deviation first, then declared zoning/proximity preferences and stable ordering",
                                  scope=scope, dependencies={n:importlib.metadata.version(n) for n in ["ortools","shapely","networkx","pydantic"]}))
    return dict(search_status="feasible", optimality="proven" if status == cp_model.OPTIMAL else "not_proven",
                message="A candidate was generated. Independent checks determine whether it can be released.", layout=layout)

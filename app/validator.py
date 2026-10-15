"""Independent exported-geometry checks. No generator/solver imports or scores."""
from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

import networkx as nx
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from .models import Brief, Check, Layout, Report, brief_hash
from .requirements import REGISTER

VERSION = "geometry-validator-1.0"
EPS = 0.00001  # mm²/line length numeric noise, not a design allowance.


def validate(brief: Brief, layout: Layout) -> Report:
    checks = []
    ledger, schedule, graph = {}, [], nx.Graph()

    def check(identifier, passed, expected, measured, *, units=None, tolerance=0, ids=None, description=None, source=None, provenance=None, procedure=None, classification="hard"):
        definition = REGISTER.get(identifier, (description, source, provenance, units, procedure))
        checks.append(Check(id=identifier, description=description or definition[0], source=source or definition[1],
                            provenance=provenance or definition[2], classification=classification,
                            units=units or definition[3], expected=expected, measured=measured, tolerance=tolerance,
                            status="pass" if passed else "fail", validation_procedure=procedure or definition[4], geometry_ids=ids or []))

    def finish():
        reviews = [
            ("R-SURVEY", "Survey accuracy and existing conditions", "Source geometry has not been independently surveyed by this application."),
            ("R-OPERATING", "Furniture use, door swings and operational clearances", "Only indicative footprints, counts and collisions are checked; full usable clearances and swing envelopes are not implemented."),
            ("R-EGRESS", "Finite-width evacuation and exit suitability", "Door topology is checked. Travel distance, fire strategy, legal exits and finite-width route simulation are not implemented."),
            ("R-ACCESS", "Accessible use and routes", "Turning spaces, accessible facilities and jurisdiction-specific accessibility checks are not implemented."),
            ("R-REGULATORY", "Applicable official requirements", "No jurisdiction-specific official requirement set is selected or implemented."),
            ("R-SERVICES", "Service reserve contents and building systems", "The core is a gross reserve; internal usable area, plumbing, ventilation and structural coordination are not verified."),
            ("R-ARCHITECT", "Architectural usefulness", "A qualified architect must review function, daylight, privacy, acoustics and the appropriateness of the design assumptions."),
        ]
        for identifier, title, reason in reviews:
            checks.append(Check(id=identifier, description=title, source="PLAN.md sections 7–8 and 13", provenance="not_selected" if identifier == "R-REGULATORY" else "design_assumption",
                                classification="review", units="review", expected="Qualified review or implemented requirement set", measured=None,
                                status="unverified", implementation_status="not_implemented", validation_procedure=reason,
                                scope="Outside the implemented geometry-check scope"))
        failed = any(c.status == "fail" and c.classification == "hard" for c in checks)
        return Report(validator_version=VERSION, brief_revision=brief.revision, brief_hash=brief_hash(brief),
                      validation_status="failed" if failed else "passed", scope="Implemented 2D geometry, indicative furniture footprints and door topology only; not architectural or regulatory approval",
                      checks=checks, area_ledger_m2=ledger, room_schedule=schedule,
                      connectivity_edges=sorted(tuple(sorted(e)) for e in graph.edges))

    check("R-INPUT", brief.units == "mm" and layout.units == "mm", "Explicit mm units and declared source status",
          dict(brief_units=brief.units, geometry_units=layout.units, source_status=brief.floor.source_status, source_note=brief.floor.source_note))
    check("R-REV", layout.brief_hash == brief_hash(brief) and layout.brief_revision == brief.revision,
          dict(hash=brief_hash(brief), revision=brief.revision), dict(hash=layout.brief_hash, revision=layout.brief_revision))
    allspaces = [*layout.rooms, layout.corridor, layout.core]
    allitems = [*allspaces, *layout.walls, *layout.doors, *layout.furniture]
    identifiers = [s.id for s in allitems]
    errors, polys = [], {}
    for item in allitems:
        try:
            poly = Polygon(item.polygon)
            if not poly.is_valid or poly.is_empty or poly.area <= 0 or item.polygon[0] != item.polygon[-1]:
                errors.append(item.id)
            elif item in allspaces and (poly.symmetric_difference(box(*poly.bounds)).area > EPS or not poly.equals(poly.envelope)):
                errors.append(item.id)
            else:
                polys[item.id] = poly
        except (ValueError, TypeError):
            errors.append(item.id)
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate_geometry_ids")
    if layout.corridor.id != "corridor" or layout.core.id != "core":
        errors.append("reserved_fixed_space_ids")
    check("R-GEOMETRY", not errors, "Unique IDs, closed valid positive polygons, rectangular axis-aligned spaces", dict(invalid=errors, item_count=len(allitems)), ids=errors)
    if errors:
        for identifier, definition in REGISTER.items():
            if identifier not in {c.id for c in checks}:
                checks.append(Check(id=identifier, description=definition[0], source=definition[1], provenance=definition[2], units=definition[3],
                                    expected="Valid input polygons before this check", status="unverified", measured=None,
                                    validation_procedure="Skipped because invalid exported geometry prevents a reliable measurement."))
        return finish()

    f, fixed = brief.floor, brief.fixed
    t, it = f.external_wall_mm, f.internal_wall_mm
    shell = box(0, 0, f.width_mm, f.depth_mm)
    inside = box(t, t, f.width_mm-t, f.depth_mm-t)
    spaces = {s.id:polys[s.id] for s in allspaces}
    expected_program = {r.id:(r.kind, r.capacity) for r in brief.rooms}
    actual_program = {r.id:(r.kind, r.capacity) for r in layout.rooms}
    check("R-PROGRAM", expected_program == actual_program and len(layout.rooms) == len(brief.rooms), expected_program, actual_program)
    outside_spaces = {s.id:round(polys[s.id].difference(inside).area,6) for s in allspaces if polys[s.id].difference(inside).area > EPS}
    check("R-CONTAIN", not outside_spaces, 0, outside_spaces or 0, ids=list(outside_spaces), tolerance=EPS)
    primary = [*allspaces, *layout.walls, *layout.doors]
    intersections = []
    for a, b in itertools.combinations(primary,2):
        area = polys[a.id].intersection(polys[b.id]).area
        if area > EPS:
            intersections.append(dict(a=a.id,b=b.id,overlap_mm2=round(area,6)))
    check("R-NO-OVERLAP", not intersections, 0, intersections or 0, tolerance=EPS)
    fixed_errors = {name:polys[name].symmetric_difference(box(r.x1,r.y1,r.x2,r.y2)).area
                    for name,r in [("core",fixed.core),("corridor",fixed.corridor)]}
    preserved = all(v <= EPS for v in fixed_errors.values())
    fixed_errors["unsupported_additional_obstructions"] = [r.model_dump() for r in fixed.other_obstructions]
    check("R-FIXED", preserved and not fixed.other_obstructions, {"core":0,"corridor":0,"additional_obstructions":"Outside implemented family; cannot certify"}, fixed_errors, ids=["core","corridor"], tolerance=EPS)
    offgrid = [(item.id,x,y) for item in [*allspaces,*layout.walls,*layout.doors] for x,y in item.polygon
               if x % brief.rules.grid_mm or y % brief.rules.grid_mm]
    check("R-GRID", not offgrid and layout.grid_mm == brief.rules.grid_mm, brief.rules.grid_mm, dict(declared_grid_mm=layout.grid_mm, off_grid_vertices=offgrid), tolerance=0)
    cb = polys["corridor"].bounds
    corridor_width = min(cb[2]-cb[0], cb[3]-cb[1])
    check("R-CORRIDOR", corridor_width >= brief.rules.min_corridor_mm, {"minimum":brief.rules.min_corridor_mm}, corridor_width, ids=["corridor"])
    fixed_opening_errors = {}
    for o in fixed.exterior_openings:
        actual = polys.get(o.id)
        fixed_opening_errors[o.id] = actual.symmetric_difference(box(o.x1,o.y1,o.x2,o.y2)).area if actual is not None else "missing"
    check("R-OPENINGS", all(isinstance(v,(float,int)) and v <= EPS for v in fixed_opening_errors.values()), "Exact fixed apertures", fixed_opening_errors, ids=list(fixed_opening_errors), tolerance=EPS)

    for spec in brief.rooms:
        if spec.id not in spaces:
            check(f"R-AREA-{spec.id}",False, {"minimum":spec.min_area_m2,"maximum":spec.max_area_m2}, "missing room",
                  description=f"{spec.name}: clear area",source="User-approved room area bounds",provenance="user",units="m²",procedure="Measure the exported clear room polygon.",ids=[spec.id])
            continue
        poly = spaces[spec.id]
        x1,y1,x2,y2 = poly.bounds
        w,h = x2-x1,y2-y1
        area = poly.area / 1e6
        ratio = max(w,h)/min(w,h)
        check(f"R-AREA-{spec.id}", area+1e-9 >= spec.min_area_m2 and (spec.max_area_m2 is None or area <= spec.max_area_m2+1e-9),
              dict(minimum=spec.min_area_m2,maximum=spec.max_area_m2,target=spec.target_area_m2), round(area,6),
              description=f"{spec.name}: clear area",source="User-approved room area bounds",provenance="user",units="m²",procedure="Measure the exported clear room polygon; target is a preference.",ids=[spec.id], tolerance=1e-9)
        check(f"R-DIM-{spec.id}", min(w,h) >= brief.rules.min_short_side_mm and ratio <= brief.rules.max_aspect_ratio+1e-9,
              dict(minimum_short_side_mm=brief.rules.min_short_side_mm,maximum_aspect_ratio=brief.rules.max_aspect_ratio),
              dict(width_mm=w,depth_mm=h,short_side_mm=min(w,h),aspect_ratio=round(ratio,6)),description=f"{spec.name}: dimensions",
              source="PLAN.md section 7; prototype design assumptions",provenance="design_assumption",units="mm/ratio",procedure="Measure axis-aligned clear room bounds.",ids=[spec.id])
        schedule.append(dict(id=spec.id,name=spec.name,kind=spec.kind,capacity=spec.capacity,width_mm=w,depth_mm=h,
                             area_m2=round(area,6),minimum_m2=spec.min_area_m2,target_m2=spec.target_area_m2,maximum_m2=spec.max_area_m2))

    graph.add_nodes_from([*spaces,"outside"])
    door_measurements, bad_doors, declared_mismatches = [], [], []
    for door in layout.doors:
        dp = polys[door.id]
        x1,y1,x2,y2 = dp.bounds
        w,h = x2-x1,y2-y1
        vertical = h > w
        if vertical:
            faces = [LineString([(x1,y1),(x1,y2)]),LineString([(x2,y1),(x2,y2)])]
            clear,thickness = h,w
        else:
            faces = [LineString([(x1,y1),(x2,y1)]),LineString([(x1,y2),(x2,y2)])]
            clear,thickness = w,h
        contacts = []
        for face in faces:
            matched = [name for name,sp in spaces.items() if sp.boundary.intersection(face).length >= clear-EPS]
            if shell.boundary.intersection(face).length >= clear-EPS:
                matched.append("outside")
            contacts.append(matched)
        pair = [v[0] for v in contacts] if all(len(v)==1 for v in contacts) else []
        exterior = "outside" in pair
        shape_ok = dp.symmetric_difference(box(*dp.bounds)).area <= EPS
        valid = shape_ok and clear >= brief.rules.min_aperture_mm and len(pair)==2 and pair[0]!=pair[1] and thickness == (t if exterior else it)
        door_measurements.append(dict(id=door.id,clear_mm=clear,wall_thickness_mm=thickness,contacts=contacts))
        if valid:
            graph.add_edge(*pair)
            if set(pair) != set(door.connects):
                declared_mismatches.append(door.id)
        else:
            bad_doors.append(door.id)
    check("R-APERTURE", not bad_doors, dict(minimum_clear_mm=brief.rules.min_aperture_mm,opposite_face_contacts=2), door_measurements,ids=bad_doors)
    disconnected = [name for name in spaces if name != "corridor" and (not graph.has_edge(name,"corridor") or not nx.has_path(graph,name,"outside"))]
    if not nx.has_path(graph,"corridor","outside"):
        disconnected.append("corridor")
    check("R-CONNECT", not disconnected and not bad_doors and not declared_mismatches,
          "Every room and core has an aperture to the corridor and a topological path to an exterior opening; declarations match measurements",
          dict(disconnected=disconnected,invalid_interfaces=bad_doors,declared_connection_mismatches=declared_mismatches,edges=sorted(tuple(sorted(e)) for e in graph.edges)),
          ids=disconnected+declared_mismatches)

    # Rebuild expected physical walls from the brief and actual room boundaries.
    corridor = fixed.corridor
    expected_wall_parts = [shell.difference(inside),box(t,corridor.y1-it,f.width_mm-t,corridor.y1),box(t,corridor.y2,f.width_mm-t,corridor.y2+it)]
    groups = [[],[]]
    family_errors = []
    for item in allspaces:
        if item.id == "corridor":
            continue
        bounds = polys[item.id].bounds
        if bounds[1] == t and bounds[3] == corridor.y1-it:
            groups[0].append((item.id,bounds))
        elif bounds[1] == corridor.y2+it and bounds[3] == f.depth_mm-t:
            groups[1].append((item.id,bounds))
        else:
            family_errors.append(item.id)
    for group in groups:
        group.sort(key=lambda v:v[1][0])
        if not group or group[0][1][0] != t or group[-1][1][2] != f.width_mm-t:
            family_errors.append("bank_extent")
        for (aid,a),(bid,b) in zip(group,group[1:]):
            if b[0]-a[2] != it:
                family_errors.append(f"{aid}/{bid}")
            elif a[1]==b[1] and a[3]==b[3]:
                expected_wall_parts.append(box(a[2],a[1],b[0],a[3]))
    apertures = unary_union([polys[d.id] for d in layout.doors])
    expected_wall_union = unary_union(expected_wall_parts).difference(apertures)
    actual_wall_union = unary_union([polys[w.id] for w in layout.walls])
    wall_error = expected_wall_union.symmetric_difference(actual_wall_union).area
    check("R-WALLS", wall_error <= EPS and not family_errors, "Declared thicknesses and completely tiled banks", dict(symmetric_difference_mm2=round(wall_error,6),family_errors=family_errors),tolerance=EPS)

    catalogue = json.loads(Path(__file__).with_name("templates.json").read_text(encoding="utf-8"))["templates"]
    furniture_errors, furniture_summary = [], {}
    for spec in brief.rooms:
        items = [v for v in layout.furniture if v.room_id == spec.id]
        expected = catalogue[f"{spec.kind}_{spec.capacity}"]["items"]
        signature = lambda kind,w,h:(kind,min(w,h),max(w,h))
        needed = Counter(signature(v[0],v[4],v[5]) for v in expected)
        actual = Counter()
        for item in items:
            p = polys[item.id]
            x1,y1,x2,y2 = p.bounds
            actual[signature(item.kind,x2-x1,y2-y1)] += 1
            if spec.id not in spaces or p.difference(spaces[spec.id]).area > EPS or p.symmetric_difference(box(*p.bounds)).area > EPS:
                furniture_errors.append(item.id)
        if needed != actual:
            furniture_errors.append(f"{spec.id}: footprint/count mismatch")
        furniture_summary[spec.id] = dict(expected_items=len(expected),actual_items=len(items),expected_kind_counts=dict(Counter(v[0] for v in expected)),actual_kind_counts=dict(Counter(v.kind for v in items)))
    for item in layout.furniture:
        if item.room_id not in expected_program:
            furniture_errors.append(item.id)
    for a,b in itertools.combinations(layout.furniture,2):
        if polys[a.id].intersection(polys[b.id]).area > EPS:
            furniture_errors.append(f"{a.id}/{b.id}: collision")
    check("R-FURN", not furniture_errors, "Declared template counts and dimensions, contained non-overlapping footprints", dict(rooms=furniture_summary,errors=furniture_errors),ids=furniture_errors,tolerance=EPS)

    for rel in brief.relationships:
        a,b = spaces.get(rel.a),spaces.get(rel.b)
        shared_wall = 0
        distance = None
        if a is not None and b is not None:
            aa,bb = a.bounds,b.bounds
            if abs(aa[2]-bb[0]) == it or abs(bb[2]-aa[0]) == it:
                shared_wall = max(0,min(aa[3],bb[3])-max(aa[1],bb[1]))
            distance = a.centroid.distance(b.centroid)
        measured = dict(shared_wall_length_mm=shared_wall,direct_door=graph.has_edge(rel.a,rel.b),centroid_distance_mm=round(distance,3) if distance is not None else None)
        satisfied = shared_wall > 0 if rel.kind == "wall_adjacent" else graph.has_edge(rel.a,rel.b) if rel.kind == "door_connected" else distance is not None
        check(f"R-REL-{rel.id}", satisfied, rel.kind, measured, description=f"{rel.a} / {rel.b}: {rel.kind}",source="User-approved relationship",provenance="user",units="mm/boolean",
              procedure="Measure separating-wall contact or a reconstructed direct aperture edge. Proximity is a measured preference without a pass threshold.",classification="hard" if rel.mandatory else "soft",ids=[rel.a,rel.b])

    union = unary_union([polys[item.id] for item in primary])
    total = sum(polys[item.id].area for item in primary)
    uncovered, excess = shell.difference(union).area,union.difference(shell).area
    ledger.update(program_usable=round(sum(polys[s.id].area for s in layout.rooms)/1e6,6),
                  core_gross_reserve=round(polys["core"].area/1e6,6),circulation_clear=round(polys["corridor"].area/1e6,6),
                  thresholds=round(sum(polys[d.id].area for d in layout.doors)/1e6,6),walls=round(sum(polys[w.id].area for w in layout.walls)/1e6,6),
                  gross=round(shell.area/1e6,6),partition_total=round(total/1e6,6),uncovered=round(uncovered/1e6,9),outside=round(excess/1e6,9),
                  duplicated=round((total-union.area)/1e6,9))
    check("R-ACCOUNT", uncovered <= EPS and excess <= EPS and abs(total-shell.area)/1e6 <= 0.01,
          "No uncovered/outside area; ledger discrepancy at most 0.01 m²", ledger,
          tolerance={"ledger_m2":0.01,"uncovered_mm2":EPS,"outside_mm2":EPS})
    return finish()

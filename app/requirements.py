"""Requirement provenance, not constraint-building code."""
REGISTER = {
    "R-INPUT": ("Input provenance and units", "User-approved brief; PLAN.md sections 5–6", "user", "fields", "Read explicit units, source confidence and versioned schema."),
    "R-REV": ("Geometry belongs to the approved brief", "Brief revision and SHA-256 digest", "derived", "revision/hash", "Recompute the digest of the complete approved brief."),
    "R-GEOMETRY": ("Valid positive geometry and unique IDs", "PLAN.md section 6", "derived", "items", "Check closed valid polygons, positive areas, axis-aligned rectangular spaces and unique IDs."),
    "R-PROGRAM": ("Requested room program and capacities", "User-approved room program", "user", "rooms/seats", "Compare exported IDs, kinds and capacities with the brief."),
    "R-CONTAIN": ("Spaces remain inside the inside-face boundary", "Measured or assumed floor and wall dimensions", "user", "mm²", "Subtract the independently constructed inside-face shell from each space."),
    "R-NO-OVERLAP": ("Spaces, walls and apertures do not overlap", "PLAN.md section 8", "derived", "mm²", "Measure pairwise positive-area intersections of every primary partition."),
    "R-FIXED": ("Fixed corridor and core remain unchanged", "User-approved fixed coordinates", "user", "mm²", "Compare exported fixed polygons with the brief using symmetric differences."),
    "R-GRID": ("Design grid is respected", "PLAN.md section 7; adjustable design assumption", "design_assumption", "mm", "Check room and wall vertices against the declared design grid."),
    "R-CORRIDOR": ("Modeled corridor clear width", "PLAN.md section 7; not a code threshold", "design_assumption", "mm", "Measure the short side of the exported corridor rectangle."),
    "R-OPENINGS": ("Fixed exterior apertures remain unchanged", "User-approved opening locations", "user", "mm²", "Match fixed aperture polygons and require physical shell/corridor contact."),
    "R-APERTURE": ("Modeled aperture widths and interfaces", "PLAN.md section 7; not a door certification", "design_assumption", "mm", "Measure the clear span and require contacts on opposite aperture edges."),
    "R-CONNECT": ("Usable door topology, distinct from shared-wall adjacency", "User requirement: every room connects to the corridor and an exterior opening", "user", "graph paths", "Reconstruct edges from measured aperture contacts; compare declarations and find paths."),
    "R-FURN": ("Indicative furniture counts, footprints and containment", "app/templates.json; prototype footprint assumptions", "design_assumption", "items/mm²", "Count expected furniture; measure item dimensions, containment and collisions independently."),
    "R-WALLS": ("Explicit wall geometry accounts for wall construction", "Declared external/internal wall thicknesses", "user", "mm²", "Rebuild shell, corridor bands and actual room/core separators; compare their aperture-cut union."),
    "R-ACCOUNT": ("Gross-area accounting without unexplained gaps", "PLAN.md section 7", "derived", "m²", "Union explicit partitions; measure uncovered and outside area separately from the sum ledger."),
}


def register():
    rows = [dict(id=k, description=v[0], source=v[1], provenance=v[2], units=v[3], validation_procedure=v[4],
                 classification="hard", implementation_status="implemented", tolerance=0)
            for k, v in REGISTER.items()]
    rows.extend([
        dict(id="R-AREA-{room_id}", description="Room area minimum/optional maximum and target", source="User-approved room bounds", units="m²", tolerance=0, classification="hard", implementation_status="implemented", validation_procedure="Measure exported clear room polygon area."),
        dict(id="R-DIM-{room_id}", description="Room short side and aspect ratio", source="Prototype design assumptions", units="mm/ratio", tolerance=0, classification="hard", implementation_status="implemented", validation_procedure="Measure the exported room bounding rectangle."),
        dict(id="R-REL-{relationship_id}", description="Explicit adjacency, direct door or proximity", source="User-approved relationship", units="mm/boolean", tolerance=0, classification="hard or soft", implementation_status="implemented", validation_procedure="Measure physical separating wall or reconstructed direct door edge; report proximity separately."),
    ])
    return rows

# Floor Plan Generation — Prototype Implementation Plan

Status: implemented and verified within the agreed prototype scope; milestones M0–M6 complete.
Created: 2026-10-15.
Purpose: build a small, reliable prototype the user can demonstrate to their boss.
Canonical plan: this file in the project root. Update it as work is verified.

## 1. The outcome we are proving

A user answers relevant questions, reviews a structured brief, receives a dimensioned office floor plan with an independent geometry report, changes a requirement, and receives either a newly validated layout or an honest explanation of the conflict.

Success means a repeatable end-to-end demonstration. It does not mean universal architectural design or construction approval.

## 2. Decisions already made

| Decision | Commitment |
| --- | --- |
| Building type | One small office, one ground floor. |
| Delivery | A local browser application on the presentation computer. |
| Cost/dependency model | No required paid API, cloud account, LLM service, or network connection during the demo after dependencies are installed. |
| Interaction | An adaptive questionnaire, editable brief, generation, independent validation, and targeted follow-up. |
| Visual reference | The accepted interactive office output example, including its clear plan, room inspector, area schedule, and pass/unverified distinction. |
| Main demonstration | Change a room requirement live and show a genuine response from the backend. |
| Missing deadline | No presentation date was supplied. Use milestone gates, not invented calendar promises. |

### Existing work and its limits

- [x] An earlier illustrative result screen was created at outputs/floor-plan-demo.html. It is retained locally as historical reference and excluded from the Git repository and distributed source archive.
- [x] Its initial layout, meeting-room resizing, and oversized-request message were exercised in a browser.
- [x] The user accepted the example as the direction for the output.
- [x] The adaptive questionnaire is implemented and exercised in the browser.
- [x] The Python generator and independent exported-geometry validator are implemented and tested.

The earlier illustrative example uses a manually defined arrangement and browser calculations. The implemented application follows its visual language and uses real backend generation and validation. The historical example's 24/30 m² cases are UX references; the repository's outputs/*-result.json and outputs/*-plan.svg files record actual executed solver/validator results.

## 3. MVP scope contract

### Included

- One rectangular outside footprint, entered as width and depth in metres.
- Explicit fixed entrance/opening locations, a straight corridor, and one service-core reserve.
- Axis-aligned rectangular rooms placed in two banks alongside that corridor.
- Reception, one shared workroom, one meeting room, and one to four private offices. Default: two private offices, giving five programmed rooms plus the core.
- A small furnishing-template catalogue: two/four/six shared workstations, four/six meeting seats, one workstation per private office, and a reception desk with waiting seats.
- Minimum and optional maximum clear room areas, soft target areas, and supported room relationships.
- One genuine feasible layout per request, with room labels, clear dimensions, areas, walls, doors, and indicative furniture.
- A separately calculated geometry report and room schedule.
- Editable requirements, regeneration, reset to the demo brief, and local SVG/JSON downloads.
- Three repeatable demonstration scenarios and a small set of failure checks.

### Deliberately deferred

- Malls, residential layouts, multiple floors, arbitrary boundary polygons, free-form corridors, and 3D rendering.
- CAD/PDF/image recognition, BIM authoring, model training, and image-generated floor plans.
- Accounts, collaboration, databases, public hosting, and third-party service integrations.
- Automatic structural, fire, accessibility, or other legal certification.
- General furniture optimization and full operational/accessible-clearance simulation.

An interior obstruction or geometry outside the supported strip family must produce an explicit unsupported-input result. Do not ignore it or claim that no architectural solution exists.

Routine implementation choices within this contract can be resolved and documented. Do not add deferred features without a new user request.

## 4. The demonstration contract

The finished prototype must support this sequence:

1. Open the app locally with the documented launch command.
2. Start the small-office preset and complete the short adaptive questions.
3. Review the resulting editable brief, including assumptions and fixed geometry.
4. Generate a real layout and show independently measured checks.
5. Inspect a room's dimensions and area, and open the area schedule.
6. Increase the meeting-room requirement; regenerate and show the resulting room-size trade-off.
7. Submit a demonstrably impossible request; show a specific explanation and editable requirements.
8. Restore the original brief and repeat successfully.
9. Download the current validated geometry as SVG and the brief/layout/report as JSON.

Saved examples are reproducible inputs. They must go through the actual engine during the demonstration, rather than replacing generation with saved output.

Initial performance target: a supported normal case completes generation and validation within 30 seconds on the presentation computer. Start with a solver budget of 25 seconds, measure the entire request, and record actual results. These are unverified targets until measured.

## 5. Adaptive questionnaire

Use deterministic branching rules for this version. A paid API or language model is unnecessary for the agreed flow.

### Question groups

| Group | Collect | Follow-up behavior |
| --- | --- | --- |
| Floor | Outside width/depth, units, and whether dimensions are measured or assumed | If only total area is known, request dimensions or a declared rectangular proportion; do not infer a unique shape from area. |
| Fixed geometry | Core reserve, corridor and exterior opening locations; presence of other immovable elements | Offer the preset for a synthetic demo. Ask for missing fixed coordinates when using custom geometry. |
| Activities | Private-office count, shared workstation count, meeting capacity, reception/waiting needs | Ask only the capacity questions relevant to selected spaces and templates. |
| Room requirements | Minimum area, target area, optional maximum, and required relationships | Clarify direct door access versus shared-wall adjacency versus proximity. |
| Priorities | Which preferences may change when space is tight | Keep mandatory requirements separate from preferences. |
| Context | Project location, if known, and source confidence | Record it; retain regulatory status as unverified in this prototype. |

### Behavior rules

- Every question maps to a required field, a constraint, or a visible design preference.
- Skip information already established by the selected office use or preset.
- Show why a follow-up is necessary in plain language.
- Do not require users to supply professional code thresholds. Use documented prototype defaults and label them as design assumptions.
- Validate positive dimensions, units, counts, area bounds, and the supported geometry family before solving.
- Reject contradictory minimum/maximum bounds with field-specific messages.
- Show staff/workstation capacity explicitly; do not silently invent desks. Meeting seats can serve the same staff population and are not automatically additional occupants.
- Never silently change a mandatory answer. Offer the user specific editable alternatives after a conflict.
- Mark old results as previous whenever the brief changes. Never show old green checks as evidence for the changed brief.

## 6. Data and geometry contracts

Use typed input/output models, stable identifiers, explicit units, and versioned JSON.

Create stable requirement IDs for input/provenance, room counts, area ranges, room dimensions, containment, overlaps, fixed geometry, walls, corridor width, aperture width, door connectivity, specified adjacency, furniture fit and area accounting. Keep operational clearances and regulatory checks as explicit unverified requirements. Each check must be independently reportable.

### Brief

Include project use, source status, outside boundary, inside-face geometry, fixed zones/openings, room IDs and activities, furnishing templates, hard constraints, ranked preferences, and unresolved items.

Each requirement has: ID, description, source, hard/soft classification, units, bounds/tolerance, implementation status, and validation procedure. Distinguish user answers, derived values, verified references, and assumptions.

### Layout

Export clear room polygons, wall polygons, corridor/service-reserve polygons, aperture polygons, door IDs and the spaces they connect, and indicative furniture footprints. Include the exact brief revision/hash, grid size, model version, solver status, seed/settings, dependency versions, and elapsed time.

Do not export a screenshot as the authoritative plan. The drawing is a view of the dimensioned geometry.

### Report

For each requirement export: ID, expected value, measured value, units, pass/fail/unverified status, scope, and affected geometry IDs. Recalculate totals from exported geometry.

Use separate search and validation states:

| Field | Values / interpretation |
| --- | --- |
| search_status | feasible, infeasible, unknown, invalid_input, unsupported, error |
| optimality | proven or not_proven; applies only to the encoded objective/model |
| validation_status | passed, failed, unverified, or not_run, with a declared check scope |
| regulatory_status | unverified for this MVP |

A failed mandatory geometry check blocks release of the candidate as a valid result. An unimplemented check remains unverified. A geometry pass must never be labeled overall architectural or regulatory approval.

## 7. Prototype design assumptions

These are adjustable project assumptions, not building-code claims:

| Item | Starting value |
| --- | --- |
| Reference outside shell | 16.00 × 10.00 m; gross area 160.00 m² |
| External/internal wall thickness | 200 / 100 mm |
| Fixed corridor clear rectangle | x=200..15800, y=4100..5900 mm |
| Fixed service-core reserve | x=12500..15800, y=200..4000 mm |
| Exterior opening candidates | West/east shell sides, y=4550..5450 mm |
| Design grid | 50 mm; preserve raw coordinates in integer mm |
| Modeled aperture minimum | 900 mm clear |
| Minimum room short side / maximum aspect ratio | 3200 mm / 3 |
| Area accounting discrepancy ceiling | 0.01 m²; never use this to conceal real holes or overlaps |
| Baseline program | Reception; four-desk workroom; two one-desk offices; six-seat meeting room |
| Room area minimum/target/maximum, m² | Reception 16/19/22; workroom 24/27/32; each office 16/19/22; meeting 18/21/28 |

The meeting-room maximum of 28 m² is a prototype default for the live-change demonstration; it does not establish feasibility of that size. Surface bounds in the editable brief.

The core is a gross reserve; its internal usable area and facilities are unknown. Exterior openings are candidates, not confirmed legal exits. Survey accuracy and legal occupancy remain unverified.

Custom input must preserve its own fixed coordinates. Changing a footprint does not silently move a fixed core, corridor or entrance. Validate compatibility with the supported two-bank family and request corrected input or report unsupported geometry.

## 8. Implementation architecture

| Component | Choice / responsibility |
| --- | --- |
| Runtime | Python 3.12 baseline; record the exact tested environment. |
| Local application/API | FastAPI and Uvicorn, bound to 127.0.0.1; serve frontend and API from the same origin. |
| Input/output contracts | Pydantic models and versioned JSON. |
| Frontend | Plain HTML, CSS and JavaScript, using the accepted result screen as the visual reference. No frontend build service is required. |
| Generation | OR-Tools CP-SAT. |
| Geometry checks | Shapely, plus exact integer checks where appropriate. |
| Connectivity | NetworkX, using connections reconstructed from geometry. |
| Persistence/export | Local JSON/SVG; no database for MVP. |
| Verification | Focused pytest checks and browser exercises of the demonstration flow. |

Pin exact dependency versions after a successful compatibility run. Vendor or bundle any presentation assets; the demo must not rely on CDNs, web fonts, remote scripts or external APIs at runtime.

### Generation method

- Derive two rectangular room banks from the supplied shell and fixed corridor. Restrict the core to a compatible end-of-bank reserve for the initial model.
- For each room choose a bank, position, width, doorway offset, and allowed furnishing/template orientation. Bank depth follows the fixed geometry.
- Use integer grid variables, allowed assignments and explicit separation constraints. Account for walls as real occupied area.
- Enforce room bounds, required spaces, fixed elements, minimum dimensions, specified relationships and corridor access.
- Prefer target room areas first, then compatible zoning/proximity. Use only objectives that the model actually represents. Corridor area is fixed and is not an optimization achievement.
- Construct/export explicit walls and apertures. Never label unexplained leftover area as wall merely to force area closure.
- Keep room templates small and traceable. Verify indicative furniture containment/collisions; retain operational and accessible clearances as unverified.
- Do not reuse the current example's coordinate-resizing function as the generation engine.

### Independent validation

The validator receives the brief and exported geometry. It must not import the generator's constraint-building functions or trust solver-provided totals, edges, or satisfaction flags.

Recalculate: schema/units/IDs; valid positive geometry; room count; boundary containment; overlaps and uncovered areas; preservation of fixed elements; clear room areas and dimensions; modeled corridor/aperture widths; required wall adjacency; doorway topology; basic furniture containment/collisions; and the area ledger.

Rebuild connectivity from actual openings and physical contact. Point contact or a shared wall alone is insufficient. Connectivity is topological; it is not a verified finite-width or legal escape route.

Do not use Shapely minimum_clearance as a corridor-width measurement. Do not treat IFC/schema validity, solver feasibility, or a good-looking image as building-code compliance.

### Failure behavior

- Invalid data: explain the affected fields before generation.
- Unsupported input: identify the model limit; do not imply global architectural infeasibility.
- Necessary-condition contradiction: explain the arithmetic and identify requirement IDs.
- CP-SAT INFEASIBLE: state that the encoded grid/layout family was proven infeasible.
- CP-SAT UNKNOWN / timeout without a candidate: say the search is unresolved.
- Feasible incumbent at timeout: independently validate it and report unproven optimality.
- Invalid solver model / unexpected exception: show a clear failure state and keep technical diagnostics in local logs.
- No silent requirement relaxation and no stale result presented as meeting an updated brief.

## 9. Build sequence and gates

Work in this order. Finish one small, verified end-to-end path before broadening within the MVP.

### M0 — Scope and reference

- [x] Record the agreed scope and current state in this plan.
- [x] Preserve the accepted output example as a visual reference.

Gate: the illustrative example is clearly distinguished from the implemented solver application.

### M1 — Runnable skeleton and data contracts

- [x] Create the minimal Python app, local static frontend, typed brief/layout/report models and pinned dependency file.
- [x] Provide a documented local launch command and a saved baseline input.
- [x] Define the requirement register and assumption labels.

Gate: the app opens locally and validates the baseline brief without pretending to generate a plan.

### M2 — Real solver on the baseline case

- [x] Implement the supported two-bank CP-SAT model with real room/door/wall geometry.
- [x] Generate a baseline candidate from input data, with no saved-coordinate shortcut.
- [x] Record solver outcomes and the model/grid scope correctly.

Gate: a genuine feasible candidate exists with all required spaces and fixed geometry preserved. It is still a candidate until M3 passes.

### M3 — Independent validator and meaningful failures

- [x] Implement the independent geometry checks and per-requirement evidence report.
- [x] Validate the baseline and a compatible changed brief.
- [x] Detect deliberately damaged geometry and distinguish infeasible from unknown.

Gate: invalid candidates cannot appear as accepted output, and unverified checks are visible.

### M4 — Adaptive interview and editable brief

- [x] Implement the question groups and relevant follow-up rules.
- [x] Add editable answers, minimum/target/maximum distinctions, source status and conflict messages.
- [x] Make room counts and compatible supported inputs genuine model inputs.

Gate: a first-time user can reach a complete brief without editing JSON or answering irrelevant questions.

### M5 — Result screen, regeneration and exports

- [x] Connect the actual API to the accepted visual style.
- [x] Render the exported geometry with readable dimensions, areas and indicative furniture.
- [x] Add room inspection, schedule, measured checks and explicit unverified items.
- [x] Implement regeneration, reset, waiting/error states and SVG/JSON downloads.
- [x] Associate each result with the current brief revision and prevent stale-success displays.

Gate: the complete demonstration sequence works through the browser.

### M6 — Presentation readiness

- [x] Exercise the three demo scenarios and targeted negative tests below.
- [x] Measure end-to-end timing on the presentation machine.
- [x] Verify an offline run after installation and a fresh relaunch using the documented command.
- [x] Check the intended laptop viewport and keyboard operation of the form.
- [x] Finish README startup/troubleshooting instructions and a short demo script.
- [x] Update this plan with actual test evidence and remaining limitations.

Gate: every required acceptance check is evidenced. Any blocker is explicit; do not call an incomplete mockup the finished prototype.

## 10. Small evaluation and acceptance checklist

Use three saved demonstration inputs:

1. Baseline: the 16 × 10 m office with five rooms and the declared fixed zones.
2. Changed brief: a 24 m² meeting minimum, with a compatible declared maximum, that leaves both private offices at least 16 m².
3. Impossible brief: minimum room areas together exceed even the inside shell area, while every individual minimum/maximum pair is valid. For example, meeting minimum 100 m² with no hard maximum, plus the other baseline minimums, requires 172 m² against 149.76 m² inside the shell. Explain this necessary-condition contradiction without requiring a successful search.

Also use one compatible alternative room-count/footprint fixture to establish that the engine reads inputs rather than replaying the reference. A witness layout establishes expected feasibility; output need not match its exact coordinates.

### Required checks

- [x] Baseline and changed-brief layouts pass every implemented mandatory geometry check.
- [x] The alternative compatible input is generated and validated correctly.
- [x] A narrowed aperture, removed doorway, overlapping room and displaced fixed core are detected.
- [x] Missing units, invalid dimensions and contradictory area bounds receive specific messages.
- [x] Unsupported geometry and an unresolved search cannot be mislabeled proven infeasible.
- [x] The impossible request receives an evidence-based explanation and retains the user's hard requirements.
- [x] Updating the brief immediately invalidates the displayed acceptance state until a new result is validated.
- [x] SVG and JSON downloads match the displayed result and its brief revision.
- [x] An unchanged saved input is reproducible under recorded solver settings; the same valid layout is not required when multiple solutions exist.
- [x] Timings are measured against the 30-second target; misses and unresolved searches are recorded honestly.
- [x] The runtime works without a paid API key or internet connection after setup.
- [x] Restart and reset support a repeatable boss demonstration.
- [x] No UI or export claims overall architectural/regulatory approval.

Keep tests focused on real failure modes. Do not add a broad research benchmark or a large test framework for this prototype.

## 11. Minimal project organization

| Path | Purpose |
| --- | --- |
| PLAN.md | Canonical scope, milestone status, acceptance evidence and decision log. |
| README.md | Installation, local launch, limits and demonstration steps. |
| requirements.txt | Exact tested dependency versions. |
| app/main.py | Local API, static files and request/result orchestration. |
| app/models.py | Brief, layout, requirement and report schemas. |
| app/generator.py | Constraint model and solver outcome handling. |
| app/exporter.py | Explicit geometry serialization and SVG export. |
| app/validator.py | Independent checks of exported geometry. |
| app/templates.json | Small, documented furnishing/dimensional catalogue. |
| app/static/ | Questionnaire, result view, styles and browser interactions. |
| examples/ | Small repeatable input fixtures and witness metadata. |
| tests/ | Geometry, status handling and end-to-end smoke checks. |
| outputs/floor-plan-demo.html | Historical local illustrative reference; excluded from the repository and source distribution. |

These implementation files now exist. Additional scripts/ files reproduce the API measurements, offline check and source packaging; outputs/ contains executed evaluation evidence.

## 12. Rules for staying on this plan

1. Read this file before beginning or resuming implementation.
2. Start from the first unfinished milestone and keep work aligned with its gate.
3. Reuse completed work and update checkboxes only after verification.
4. Keep decisions, actual commands, outcomes and material limitations recorded here or in the referenced test evidence.
5. Resolve ordinary engineering choices within scope; record the reason for meaningful changes.
6. Record a blocker and continue independent in-scope work where possible. Never hide a blocker by reducing a mandatory requirement.
7. Do not expand into deferred features during the prototype. New requested scope must be explicit in this document.
8. Keep measured results separate from targets, examples, assumptions and future work.

### Decision log

- 2026-10-15: User selected a small office, local browser delivery and no required paid API.
- 2026-10-15: User accepted the interactive output example and requested a plan to guide implementation.
- 2026-10-15: Implementation defaults proposed here: FastAPI plus plain browser UI, CP-SAT generation, Shapely/NetworkX validation, bounded office counts and a small template catalogue. These are engineering choices within the agreed scope, not new architectural claims.
- 2026-10-15: At plan creation, no deadline or external codebase was supplied and the backend/interview had not yet been built.

## 13. Sources and evidence boundaries

The scope, numerical defaults and acceptance targets above are project decisions. Tool capabilities and outcome semantics are grounded in the following official documentation, checked 2026-10-15:

- [FastAPI: first steps](https://fastapi.tiangolo.com/tutorial/first-steps/) — local Python web/API foundation.
- [OR-Tools: CP-SAT solver](https://developers.google.com/optimization/cp/cp_solver) — integer modeling and solver status meanings.
- [OR-Tools: Python model API](https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model) — model operations; verify compatibility against the pinned version.
- [Shapely user manual](https://shapely.readthedocs.io/en/stable/manual.html) — planar geometry operations and their limitations.
- [NetworkX: shortest paths](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html) — graph-based paths; the application must supply physically valid connections.

No official building regulation has been selected for an actual project jurisdiction. A qualified architect must review real-world use, source geometry, functional clearances, applicable regulations and building-system coordination before the result is used beyond a prototype demonstration.


## 14. Verified completion record — 2026-10-15

- M1: local FastAPI app, typed/versioned contracts, four saved input fixtures, requirement register and exact tested dependency lock are present.
- M2–M3: real CP-SAT generation and independent Shapely/NetworkX checks are implemented. Candidate exports fail closed when mandatory checks fail.
- M4–M5: adaptive questions, editable brief, live regeneration, room inspection, measured schedule/report, reset and SVG/JSON downloads were exercised in the actual browser.
- M6: 29 automated acceptance checks passed; baseline and changed inputs passed after a fresh launch and in a fresh server with non-loopback TCP connections blocked. Local/data frontend assets were audited. No OS network setting was changed.
- API wall times on this computer: baseline 0.120480 s; changed meeting 0.127023 s; impossible area brief 0.002038 s; alternative footprint/three offices 25.039627 s. All met the 30-second target. The alternative returned a validated feasible incumbent with optimality not proven.
- Browser checks confirmed old acceptance/export state is removed on edits, the 24 m² minimum yields a measured 24.13 m² room, the area conflict is 172 versus 149.76 m², both exports agree with their revision/geometry, and keyboard operation/reset work. Narrow and laptop-size layouts were checked.
- Full commands, measured results, environment and evidence boundaries: [VALIDATION.md](VALIDATION.md). Startup/troubleshooting/demo: [README.md](README.md).

The agreed design scope was retained. No external architect review or jurisdiction-specific regulation validation was performed. Operational/accessibility/fire/egress/building-systems checks remain explicitly unverified; these are review limits, not completed certifications.

# Technical architecture

## Contract

The system accepts one approved small-office brief and returns either a candidate that passes independent implemented geometry checks, or an explicit non-success outcome. A geometry pass leaves architectural, operational and regulatory reviews unverified.

The current design family is intentionally small: one rectangular outside shell, a straight corridor, two rectangular room banks, a fixed service reserve and fixed exterior apertures. It has no remote runtime service or trained model.

## Data flow

1. The browser collects footprint/source confidence, activities, fixed geometry, room bounds, relationships and ranked preferences.
2. Pydantic validates the brief. Mandatory units are millimetres. A canonical digest binds the entire brief and its revision to the result.
3. CP-SAT searches the supported grid/layout family. The request's mandatory constraints remain intact on every outcome.
4. The generator exports explicit room, corridor, core, wall, aperture and furniture polygons.
5. A separate validator recomputes requirements from those polygons and the approved brief.
6. Only a passing candidate reaches the browser as a valid layout. SVG export independently revalidates the payload.

## Modules

| Module | Responsibility |
| --- | --- |
| app/models.py | Strict typed inputs/results, identifiers, units, revision and canonical brief digest |
| app/presets.py and examples/ | Reproducible input briefs |
| app/templates.json | Finite furniture/equipment footprint assumptions |
| app/requirements.py | Requirement identifiers and provenance |
| app/generator.py | Supported-family check, CP-SAT construction/search and explicit geometry export |
| app/validator.py | Exported-geometry checks and physical door graph reconstruction |
| app/exporter.py | Dimensioned SVG from checked geometry |
| app/main.py | Same-origin HTTP application, validation gate, exports and one-request generation limit |
| app/static/ | Questionnaire, editable brief, SVG inspection, report and current-revision export flow |

## Generation formulation

Dimensions and coordinates use integer millimetres. The default discretization is 50 mm. Variables select each room's bank, horizontal start, clear width, door offset and furniture-template orientation. Bank depth follows the fixed corridor/shell geometry.

Allowed assignments enforce room dimensions, clear area bounds and supported template fit. Optional intervals, no-overlap constraints and total-span equalities tile both banks, including explicit wall thickness and the service core. Fixed geometry is preserved.

Mandatory relationships can require a shared wall or a physical direct door. Duplicate direct-door requirements share one aperture. Optional proximity is a preference, with a simplified horizontal-centroid/same-bank search term.

The primary objective minimizes absolute target-area deviation; secondary terms rank declared preferences and stabilize ordering. Corridor area is fixed and is not reported as an optimization improvement.

The default solver uses one worker, seed 20261015 and a 25-second budget. A passing feasible incumbent may be returned without a proven optimum. Area assumptions support sufficient conflict sets; those sets are not promised to be minimal.

## Independent validator

The validator shares the typed contract and declared input data but imports neither the generator nor its solver constraints. It receives exported geometry and reconstructs measurements rather than trusting solver scores or declared connectivity.

Implemented checks cover:

- Schema/units, unique identifiers, polygon validity and clear rectangular room geometry.
- Exact brief revision/digest and supported fixed geometry.
- Inside-face containment, positive-area overlaps and grid alignment.
- Room counts, clear areas/dimensions and supported capacities.
- Corridor and aperture widths; actual opposite-face contacts across door openings.
- A reconstructed NetworkX access graph, including every required room/core path to the exterior.
- Independently reconstructed physical walls and real union-based area accounting.
- Furniture counts/dimensions, containment and footprint collisions.
- Shared-wall adjacency separately from actual direct-door connectivity.

Each report row contains its identifier, source, classification, units, expected and measured values, tolerance, procedure, implementation status and pass/fail/unverified status.

Gross footprint, usable rooms, circulation, gross core reserve, physical walls and aperture thresholds are reported separately. Uncovered, outside and duplicated geometry are measured directly; they are not hidden in a residual wall allowance.

## Outcome and revision guarantees

| Condition | Response |
| --- | --- |
| A candidate passes all implemented hard checks | feasible / passed |
| An area contradiction is established before search | infeasible / necessary_condition |
| CP-SAT proves the encoded model has no solution | infeasible / solver_proof, scoped to this layout family |
| Search ends without a candidate or proof | unknown |
| Input is outside the supported family | unsupported |
| Typed inputs are missing, invalid or internally contradictory | invalid_input and field-specific HTTP 422 |
| A generated candidate fails the validator | failed report; candidate geometry/SVG withheld |
| An implementation exception occurs | error; requirements retained and local log available |

Editing a brief invalidates the browser's old result and disables its exports immediately. A response for an earlier revision cannot certify the current one. The SVG endpoint rejects geometry that fails revalidation for its supplied brief.

## Explicit limits

A grid and a fixed topology can exclude a continuous or differently organized solution. A scoped infeasibility proof is not a universal architectural conclusion. Finite furniture templates restrict the generated alternatives, and footprint collision checks do not establish usable operational clearances.

The seven outstanding review categories are source/survey accuracy, furniture operation and door swings, finite-width egress, accessibility, official regulations, building systems/services and architect functional review. The prototype has not received qualified architect approval.

## Verification

The acceptance suite exercises real solves and intentionally damages exported candidates to test rejection. Saved feasible geometry is a checkable witness, not a substitute for live generation. The deliberately impossible area case, a scoped solver conflict and a zero-budget unresolved case distinguish the outcome semantics.

See [VALIDATION.md](../VALIDATION.md) for executed results and [PLAN.md](../PLAN.md) for the agreed scope.

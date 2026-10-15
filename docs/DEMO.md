# Presenter guide

## Prepare

1. Follow the root [README](../README.md) to install dependencies and start the app.
2. Open http://127.0.0.1:8000.
3. Keep the server process running. The installed app does not require internet access.
4. Optionally build the downloadable source archive with **python scripts/package_project.py**, using the project virtual environment.

Use the baseline first. The larger alternative input can use the entire 25-second solver budget.

## Main demonstration

| Step | Action | Evidence to show |
| --- | --- | --- |
| 1 | Start Small office and complete the three questionnaire steps | Source confidence, activities and fixed coordinates are explicit |
| 2 | Review the editable room-area matrix and structured brief | Minimum/maximum are mandatory; target is a preference |
| 3 | Generate a floor plan | A real search and independent validation run |
| 4 | Select the meeting room and open the schedule/report | Dimensions, usable area, measured values and unverified reviews |
| 5 | Change meeting minimum to 24 m² | The old plan/export acceptance disappears immediately |
| 6 | Regenerate | A new layout satisfies the revised brief; the recorded reference meeting area is 24.13 m² |
| 7 | Download SVG and JSON | Current geometry, brief revision, machine-readable report and digest |
| 8 | Select Area conflict and generate | 172 m² minimum room area exceeds the 149.76 m² inside shell by 22.24 m² |
| 9 | Return to Small office and regenerate | The successful path is repeatable |

The sidebar presets become a selector on narrow screens. Reset returns to the baseline.

The reference values above come from executed pinned-dependency Windows runs. Geometry and optimization timing can vary with dependency versions, solver budget and execution environment; the report measures the candidate actually returned.

## Useful follow-ups

- To show a specific input conflict, set meeting minimum to **30 m²** while retaining maximum **28 m²**. A field-specific error appears; the maximum is not silently raised.
- To show an alternative input, choose **Three private offices**. It supplies a separate 21 x 10 m footprint, six programmed rooms and compatible fixed coordinates.
- If only area is known, the questionnaire asks for a rectangular proportion and explicit adoption of an assumed boundary. An area alone does not determine a floor shape.
- Changing shell dimensions does not move fixed elements. Enter compatible coordinates explicitly.

## Explain the result accurately

The engine uses constraint programming, not a generated image or a language model. The validator checks exported polygons separately. A valid returned plan satisfies the implemented geometry requirements for the selected family.

An infeasible result is scoped to either the stated necessary contradiction or the encoded grid/layout family. An unresolved search does not prove infeasibility. Unsupported geometry is reported explicitly.

The pass result does not certify actual office operation, accessibility, fire compliance, survey accuracy or building-system coordination. Those reviews remain visible as unverified and require a qualified architect.

## Evidence files

- [Executed verification](../VALIDATION.md)
- [Evaluation summary](../outputs/evaluation.json)
- [Baseline input](../examples/baseline.json) and [result](../outputs/baseline-result.json)
- [Revised meeting input](../examples/changed.json) and [result](../outputs/changed-result.json)
- [Impossible input](../examples/impossible.json) and [result](../outputs/impossible-result.json)

Saved results document an executed run. The application generates new results from the input fixtures during the presentation.

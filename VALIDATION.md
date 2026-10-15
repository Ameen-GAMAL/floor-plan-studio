# Executed verification — 2026-10-15

The agreed prototype is implemented. This document records executed checks, not planned experiments. Architectural usefulness and regulatory compliance have not been independently reviewed by an architect.

## Environment

Windows 11 (10.0.26200), 64-bit Python 3.12.0.

| Dependency | Tested version |
| --- | --- |
| FastAPI | 0.143.2 |
| Uvicorn | 0.54.0 |
| Pydantic | 2.14.1 |
| OR-Tools | 9.15.6755 |
| Shapely | 2.2.0 |
| NetworkX | 3.7 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |

The complete installed dependency set is pinned in requirements.txt. A fresh virtual environment was created and the dependencies installed before testing.

## Automated acceptance

Executed command:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
~~~

Result: **29 passed in 27.16 seconds**. One non-blocking test-client deprecation warning recommends httpx2 instead of httpx in a future test setup; the tested dependency set was retained.

The suite includes:

- Actual generation and independent validation for baseline, 24 m² meeting, and alternative footprint/room-count inputs.
- The 172 m² versus 149.76 m² necessary-condition contradiction.
- A solver-proven conflict with requirement IDs, explicitly scoped to the grid/layout family.
- Deliberately narrowed aperture, missing doorway, overlapping room, moved core, removed furniture, forged declared connection and missing wall.
- Missing units, negative dimensions, contradictory area bounds and unsupported fixed geometry.
- A zero-budget search returning unknown rather than infeasible.
- Rejection of stale geometry and SVG exports after a brief revision.
- Shared-wall adjacency versus an actual direct doorway, and duplicate requirements sharing one physical doorway.
- Malformed polygons and imported briefs with unsupported obstructions.
- The API withholding candidate geometry and SVG when independent checks fail.
- Exported SVG room polygons matching the validated layout coordinates.
- Repeated fixed-seed input and local frontend asset references.

## Measured API runs

Executed against the freshly relaunched local server:

~~~powershell
.\.venv\Scripts\python.exe scripts\evaluate.py
~~~

| Input | Search / validation | HTTP wall time | Optimality | Meeting clear area |
| --- | --- | --- | --- | --- |
| Baseline | feasible / passed | 0.120480 s | proven in encoded objective | 20.90 m² |
| Meeting minimum 24 m² | feasible / passed | 0.127023 s | proven in encoded objective | 24.13 m² |
| Impossible area brief | infeasible / not run | 0.002038 s | not applicable | no candidate |
| 21 × 10 m, three private offices | feasible / passed | 25.039627 s | not proven | 27.93 m² |

All four measured requests met the predefined 30-second target on this computer. The alternative case used the 25-second solver budget and returned a feasible incumbent. The application does not claim its objective is optimal.

Full machine/dependency metadata and timings are in outputs/evaluation.json. Exact exported results are in outputs/*-result.json and the three accepted plans in outputs/*-plan.svg. These are generated evidence; the app never substitutes them for a live solve. The report associated with each accepted fixture supplies a geometric feasibility witness. No external architect supplied or reviewed these witnesses.

Baseline gross-area ledger, independently recomputed:

| Partition | Area |
| --- | --- |
| Programmed usable rooms | 104.50 m² |
| Clear circulation | 28.08 m² |
| Gross service reserve | 12.54 m² |
| Physical walls | 13.98 m² |
| Aperture thresholds | 0.90 m² |
| Outside gross total | 160.00 m² |
| Uncovered / outside / duplicated area | 0 / 0 / 0 m² |

## Executed browser checks

The actual local application was exercised through the browser:

1. Completed the three interview steps and generated the baseline.
2. Inspected the room schedule and the report: 25 mandatory geometry checks passed, zero failed, seven reviews unverified.
3. Downloaded baseline JSON, then revised the meeting minimum to 24 m². The previous plan disappeared and both previous exports were disabled immediately.
4. Regenerated: measured meeting area 24.13 m², dimensions 6.35 × 3.80 m, with the other hard bounds retained.
5. Downloaded the changed result as both JSON and independently revalidated SVG.
6. Entered minimum 30 m² against the retained maximum 28 m². A specific field error appeared; the maximum was not changed.
7. Loaded the impossible input through the narrow-window selector and generated its explicit 172.00 / 149.76 / 22.24 m² contradiction.
8. Reset to the small-office brief and successfully generated again.
9. Used Enter to inspect Reception on the SVG. Tab from the meeting-minimum input reached Regenerate.
10. Exercised the area-only question: provided 160 m² and an explicit 1.6 proportion, adopted the assumed 16 × 10 m rectangle, and completed the wizard/generation with keyboard Enter actions.
11. Checked the narrow in-app window (543 CSS px wide) and a laptop-sized view measured at 1360 × 771 CSS px. The plan and inspector fit within the laptop viewport. Temporary viewport overrides were reset.
12. Inspected browser error logs: no application errors captured. The validated baseline is left open.

The browser-downloaded JSON/SVG files were checked against each other: the same brief revision and matching room geometry. The JSON also retains the brief/layout/report digests. Browser evidence/screenshots are kept as local QA materials, outside the distributed source package.

## Runtime without external services and restart

The documented run.py launch was used to start and freshly relaunch the application. Health and generation requests succeeded after relaunch.

Executed:

~~~powershell
.\.venv\Scripts\python.exe scripts\offline_smoke.py
~~~

Result: passed. A new server process on loopback port 8002 prohibited non-loopback TCP connections, explicitly checked that the guard blocked an external connection, generated and validated baseline and changed briefs, and served the HTML/JS/CSS assets. The temporary process was stopped afterward.

The frontend assets are local/data assets; there are no CDN, remote-font or external API dependencies. The computer's network settings were not changed. This check establishes operation with external TCP unavailable to the server plus an audit of local frontend dependencies; it is not a claim of OS-level network isolation. Recorded results are in outputs/offline-check.json.

## Remaining limits

- Only the agreed rectangular, two-bank, single-office-floor family is implemented. Both banks are fully tiled; allowing arbitrary unassigned space would be a different formulation.
- Raw fixed coordinates are preserved. Incompatible geometry is unsupported, rather than moved or rounded silently.
- A grid can make a narrow area interval infeasible even when a continuous or different layout could fit.
- Objective optimality concerns the encoded area/zoning preferences; it is not a claim of best architectural design.
- Furniture footprint dimensions are indicative assumptions. Door swings, operational/accessible clearances, finite-width routes, legal exits, official code requirements, survey accuracy, daylight, acoustics and building-system coordination remain unverified.
- Architect review, other machines/operating systems and public multi-user deployment have not been evaluated.

## Repository publication checks - 2026-10-15

The source was prepared for the private Ameen-GAMAL/floor-plan-studio repository without changing the office-generation scope.

- Re-ran the full acceptance suite: **29 passed, one existing deprecation warning, in 27.38 seconds**.
- Dependency consistency: **pip check passed**.
- Browser JavaScript: **node --check app/static/app.js passed**.
- Extracted a newly built source archive into a clean directory. Its document routes and static assets loaded, and its live baseline solve passed independent validation.
- Ran the offline smoke check from that extracted copy: both baseline and changed briefs passed using a fresh server with non-loopback TCP blocked.
- Reviewed all **42 staged files**: no environment, work directory, log, generated archive or historical mockup was staged. Credential-pattern checks found no matches and local Markdown links resolved.
- Configured Python 3.12 CI on Windows and Ubuntu, with read-only repository permissions and GitHub Actions pinned to verified full commit SHAs. Hosted execution status is available through the repository's Actions page; local results alone do not establish hosted CI success.

The source archive includes the implementation, documentation, workflow, input fixtures and executed evidence. Historical illustrative studies remain local and are excluded from the archive and repository.

# Development guide

This is a local feasibility prototype. Keep changes within the small-office design family and the outcome contract in [PLAN.md](PLAN.md). See [SECURITY.md](SECURITY.md) for private reporting and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the dependency sources.

## Setup and checks

Use Python 3.12 and the pinned requirements. Follow [README.md](README.md) for installation.

~~~powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\offline_smoke.py
.\.venv\Scripts\python.exe scripts\package_project.py
~~~

For macOS/Linux, use **.venv/bin/python**. When Node.js is available, check frontend syntax with **node --check app/static/app.js**. CI runs these checks on Python 3.12.

## Change conventions

- Make a focused branch and describe the concrete problem, resulting behavior and relevant verification in a pull request.
- Keep mandatory requirements separate from ranked preferences. Never silently relax a hard bound.
- Keep the validator independent of generator internals. New supported constraints need exported-geometry evidence and a meaningful damaged-export check.
- Preserve explicit unknown, unsupported, invalid-input and scoped infeasibility outcomes.
- Reject stale geometry after any brief revision.
- Leave unimplemented architectural or regulatory requirements explicitly unverified.
- Update the brief schema, fixtures, requirement register and documentation when their contracts change.

Requirements are pinned to the tested environment. Review dependency changes deliberately and record their executed results; do not replace versions merely to make a badge green.

Use `requirements.in` to record direct dependencies and `requirements.txt` to hold the reviewed transitive versions. Regenerate the wheel hashes with `uv pip compile requirements.in --constraint requirements.txt --universal --python-version 3.12 --only-binary :all: --generate-hashes --output-file requirements.lock.txt`. Verify the locked install with `python -m pip install --require-hashes -r requirements.lock.txt` before running the suite. CI also checks Python syntax/name errors, types in `app/models.py`, runtime Python security patterns and dependency advisories. Its packaged artifact includes a CycloneDX inventory of the lock.

## Evidence and packaging

The **outputs/** JSON/SVG files record actual runs. To regenerate all four through a running local server, use **python scripts/evaluate.py** with the virtual environment. Review changed evidence before committing; solver timings are machine-specific.

Generated ZIP archives, logs, local environments and work files are ignored. Build the distributable with **scripts/package_project.py**. It includes source, documentation, input fixtures and executed evidence, while excluding historical illustrative mockups.

Do not replace the live generator with saved results, or describe a geometry pass as architect/code approval.

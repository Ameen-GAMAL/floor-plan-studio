"""Package only intended source and executed evidence; omit environments and QA."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parent.parent


def main():
    files=[ROOT/n for n in [".gitignore",".gitattributes",".editorconfig","PLAN.md","README.md","VALIDATION.md","CONTRIBUTING.md","requirements.txt","pytest.ini","run.py"]]
    for folder in ["app","examples","tests","scripts","docs",".github"]:
        files.extend(p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    outputs=ROOT/"outputs"
    for pattern in ["*-result.json","*-plan.svg","evaluation.json","offline-check.json"]:
        files.extend(outputs.glob(pattern))
    target=outputs/"floor-plan-studio.zip"
    with ZipFile(target,"w",ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path,"floor-plan-studio/"+path.relative_to(ROOT).as_posix())
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all("/work/" not in p and "/.venv/" not in p and "__pycache__" not in p for p in archive.namelist())
        assert "floor-plan-studio/app/static/app.js" in archive.namelist()
        assert "floor-plan-studio/VALIDATION.md" in archive.namelist()
        assert "floor-plan-studio/.gitignore" in archive.namelist()
        assert "floor-plan-studio/docs/DEMO.md" in archive.namelist()
        assert "floor-plan-studio/outputs/floor-plan-demo.html" not in archive.namelist()
        print(f"Packaged {len(archive.namelist())} files; {target.stat().st_size} bytes; archive integrity passed.")


if __name__=="__main__":
    main()

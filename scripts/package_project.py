"""Package only intended source and executed evidence; omit environments and QA."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parent.parent


def main():
    outputs=ROOT/"outputs"
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=outputs/"floor-plan-studio.zip")
    parser.add_argument("--smoke-report",type=Path,default=outputs/"offline-check.json")
    parser.add_argument("--sbom",type=Path,help="CycloneDX JSON produced by the dependency audit")
    args=parser.parse_args()
    files=[ROOT/name for name in (
        ".gitignore", ".gitattributes", ".editorconfig", "PLAN.md", "README.md", "VALIDATION.md",
        "CONTRIBUTING.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "requirements.txt",
        "requirements.in", "requirements.lock.txt", "pytest.ini", "pyproject.toml", "run.py",
    )]
    for folder in ["app","examples","tests","scripts","docs",".github"]:
        files.extend(p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for pattern in ["*-result.json","*-plan.svg","evaluation.json"]:
        files.extend(outputs.glob(pattern))
    target=args.output
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,"w",ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path,"floor-plan-studio/"+path.relative_to(ROOT).as_posix())
        archive.write(args.smoke_report,"floor-plan-studio/outputs/offline-check.json")
        if args.sbom:
            archive.write(args.sbom,"floor-plan-studio/outputs/sbom.cdx.json")
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert all("/work/" not in p and "/.venv/" not in p and "__pycache__" not in p for p in archive.namelist())
        assert "floor-plan-studio/app/static/app.js" in archive.namelist()
        assert "floor-plan-studio/VALIDATION.md" in archive.namelist()
        assert "floor-plan-studio/.gitignore" in archive.namelist()
        assert "floor-plan-studio/docs/DEMO.md" in archive.namelist()
        assert "floor-plan-studio/outputs/floor-plan-demo.html" not in archive.namelist()
        print(f"Packaged {len(archive.namelist())} files; {target.stat().st_size} bytes; archive integrity passed.")
    with target.open("rb") as stream:
        print(f"SHA-256: {hashlib.file_digest(stream,'sha256').hexdigest()}")


if __name__=="__main__":
    main()

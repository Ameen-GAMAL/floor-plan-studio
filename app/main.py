"""Same-origin local browser app. Solver candidates must pass exported-geometry checks."""
from __future__ import annotations

import html
import logging
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .exporter import svg_export
from .generator import generate
from .models import Brief, GenerateResult, ValidationRequest, brief_hash
from .presets import preset
from .requirements import register
from .validator import validate

ROOT=Path(__file__).resolve().parent.parent
STATIC=Path(__file__).with_name("static")
STATIC.mkdir(exist_ok=True)
app=FastAPI(title="Floor Plan Studio",docs_url=None,redoc_url=None,openapi_url=None)
app.mount("/static",StaticFiles(directory=STATIC),name="static")
generation_slot=threading.BoundedSemaphore(1)
logger=logging.getLogger("floorplan")


@app.exception_handler(RequestValidationError)
async def input_error(_request, exc):
    return JSONResponse(status_code=422,content={"search_status":"invalid_input","validation_status":"not_run",
        "message":"Review the indicated fields. No requirements were changed.",
        "errors":[{"field":".".join(str(p) for p in e["loc"] if p!="body"),"message":e["msg"]} for e in exc.errors()]})


@app.get("/")
def index():
    return FileResponse(STATIC/"index.html",headers={"Cache-Control":"no-store"})


@app.get("/api/health")
def health():
    return {"status":"ok","application":"Floor Plan Studio","version":"1.0","runtime":"local; no external runtime services"}


@app.get("/api/presets/{name}",response_model=Brief)
def get_preset(name: str):
    try:
        return preset(name)
    except KeyError:
        raise HTTPException(404,"Unknown preset")


@app.get("/api/requirements")
def requirements():
    return {"scope":"Prototype geometry requirements and assumptions; no selected regulatory rules", "requirements":register()}


@app.post("/api/generate",response_model=GenerateResult)
def generate_request(brief: Brief):
    if not generation_slot.acquire(blocking=False):
        raise HTTPException(429,"A layout is already being generated. Wait for it to finish.")
    started=time.perf_counter()
    try:
        result=generate(brief)
        if result["search_status"]=="feasible":
            candidate=result["layout"]
            report=validate(brief,candidate)
            result.update(report=report,validation_status=report.validation_status)
            if report.validation_status=="passed":
                result.update(svg=svg_export(brief,candidate,report),message="Layout passed every implemented mandatory geometry check. Architectural, operational and regulatory review remains unverified.")
            else:
                result.update(layout=None,message="The generated candidate failed independent geometry checks and was not released as a valid layout.")
                logger.error("Candidate failed validator: %s",[c.id for c in report.checks if c.status=="fail"])
        return GenerateResult(brief=brief,brief_revision=brief.revision,brief_hash=brief_hash(brief),elapsed_seconds=round(time.perf_counter()-started,6),**result)
    except Exception:
        logger.exception("Generation error")
        return GenerateResult(brief=brief,brief_revision=brief.revision,brief_hash=brief_hash(brief),search_status="error",
                              message="Generation could not be completed. Your requirements were retained. See the local application log.",elapsed_seconds=round(time.perf_counter()-started,6))
    finally:
        generation_slot.release()


@app.post("/api/validate")
def validate_export(payload: ValidationRequest):
    return validate(payload.brief,payload.layout)


@app.post("/api/export/svg")
def export_svg(payload: ValidationRequest):
    report=validate(payload.brief,payload.layout)
    if report.validation_status!="passed":
        return JSONResponse(status_code=422,content={"message":"Export blocked: geometry does not pass checks for this brief.","report":report.model_dump(mode="json")})
    return Response(svg_export(payload.brief,payload.layout,report),media_type="image/svg+xml",headers={"Content-Disposition":'attachment; filename="office-floor-plan.svg"'})


def document_page(filename):
    content=html.escape((ROOT/filename).read_text(encoding="utf-8"))
    return HTMLResponse(f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{filename} — Floor Plan Studio</title><style>body{{max-width:1000px;margin:40px auto;padding:0 24px;font:15px/1.7 system-ui;color:#25334a;background:#f6f8fc}}header{{display:flex;justify-content:space-between;align-items:center}}a{{color:#2863eb}}pre{{white-space:pre-wrap;background:white;border:1px solid #dde4ed;border-radius:16px;padding:28px;font:14px/1.7 ui-monospace,monospace}}</style><header><h1>{filename}</h1><a href="/">Back to the app</a><a href="/downloads/{filename}">Download</a></header><pre>{content}</pre></html>')


@app.get("/plan")
def plan():
    return document_page("PLAN.md")


@app.get("/guide")
def guide():
    return document_page("README.md")


@app.get("/validation")
def validation_document():
    return document_page("VALIDATION.md")


@app.get("/downloads/{filename}")
def download(filename: str):
    allowed={"PLAN.md","README.md","VALIDATION.md","floor-plan-studio.zip"}
    path=ROOT/filename if filename!="floor-plan-studio.zip" else ROOT/"outputs"/filename
    if filename not in allowed or not path.is_file():
        raise HTTPException(404,"File unavailable")
    return FileResponse(path,filename=filename)

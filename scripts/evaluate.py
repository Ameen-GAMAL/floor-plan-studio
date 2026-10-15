"""Measure saved inputs through the running local API and retain exact evidence."""
import argparse
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8000)
    args=parser.parse_args()
    opener=build_opener(ProxyHandler({}))
    base=f"http://127.0.0.1:{args.port}"
    output=ROOT/"outputs"
    output.mkdir(exist_ok=True)
    rows=[]
    for name in ["baseline","changed","impossible","alternative"]:
        payload=(ROOT/"examples"/f"{name}.json").read_bytes()
        request=Request(base+"/api/generate",data=payload,headers={"Content-Type":"application/json"})
        started=time.perf_counter()
        with opener.open(request,timeout=40) as response:
            result=json.load(response)
        wall=time.perf_counter()-started
        expected="infeasible" if name=="impossible" else "feasible"
        assert result["search_status"]==expected,result
        if name!="impossible":
            assert result["validation_status"]=="passed",result
            (output/f"{name}-plan.svg").write_text(result["svg"],encoding="utf-8")
        evidence={k:v for k,v in result.items() if k!="svg"}
        (output/f"{name}-result.json").write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding="utf-8")
        meeting=next((r for r in (result.get("report") or {}).get("room_schedule",[]) if r["id"]=="meeting"),None)
        row=dict(scenario=name,search_status=result["search_status"],validation_status=result["validation_status"],
                 optimality=result["optimality"],api_wall_seconds=round(wall,6),backend_seconds=result["elapsed_seconds"],
                 meeting_area_m2=meeting["area_m2"] if meeting else None,under_30_seconds=wall<30)
        rows.append(row)
        print(json.dumps(row),flush=True)
    summary=dict(executed_at=datetime.now(timezone.utc).isoformat(),python=sys.version,platform=platform.platform(),processor=platform.processor(),
                 dependencies={n:importlib.metadata.version(n) for n in ["fastapi","uvicorn","pydantic","ortools","shapely","networkx","pytest","httpx"]},
                 target_seconds=30,scenarios=rows,architect_review="not performed; geometry evidence only")
    (output/"evaluation.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    assert all(r["under_30_seconds"] for r in rows),rows


if __name__=="__main__":
    main()

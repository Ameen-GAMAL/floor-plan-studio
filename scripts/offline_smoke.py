"""Fresh-process smoke check with non-loopback TCP connections prohibited.

This does not change the computer's network settings. Static frontend assets
are audited separately; this is not a claim of OS-level network isolation.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def serve():
    original=socket.socket.connect
    original_ex=socket.socket.connect_ex
    def allowed(address):
        if isinstance(address,tuple) and address[0] not in {"127.0.0.1","::1","localhost"}:
            raise OSError("Offline check blocks all non-loopback TCP connections")
    def connect(sock,address):
        allowed(address)
        return original(sock,address)
    def connect_ex(sock,address):
        allowed(address)
        return original_ex(sock,address)
    socket.socket.connect=connect
    socket.socket.connect_ex=connect_ex
    try:
        with socket.socket() as probe:
            probe.connect(("example.com",443))
        raise AssertionError("External connection guard was not active")
    except OSError as exc:
        assert "Offline check blocks" in str(exc)
    print("EXTERNAL_TCP_BLOCKED",flush=True)
    import uvicorn
    uvicorn.run("app.main:app",host="127.0.0.1",port=8002,log_level="warning")


def check():
    work=ROOT/"work"
    work.mkdir(exist_ok=True)
    logpath=work/"offline-server.log"
    opener=build_opener(ProxyHandler({}))
    base="http://127.0.0.1:8002"
    with logpath.open("w",encoding="utf-8") as log:
        process=subprocess.Popen([sys.executable,__file__,"--serve"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:
            ready=False
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError("Offline server did not start; inspect work/offline-server.log")
                try:
                    with opener.open(base+"/api/health",timeout=.3) as response:
                        ready=json.load(response)["status"]=="ok"
                    break
                except OSError:
                    time.sleep(.05)
            assert ready,"Offline server did not become ready"
            results=[]
            for name in ["baseline","changed"]:
                payload=(ROOT/"examples"/f"{name}.json").read_bytes()
                req=Request(base+"/api/generate",data=payload,headers={"Content-Type":"application/json"})
                with opener.open(req,timeout=35) as response:
                    result=json.load(response)
                assert result["validation_status"]=="passed",result
                results.append(dict(scenario=name,status=result["validation_status"],elapsed_seconds=result["elapsed_seconds"]))
            for path in ["/","/static/app.js","/static/styles.css"]:
                with opener.open(base+path,timeout=5) as response:
                    assert response.status==200
            assert "EXTERNAL_TCP_BLOCKED" in logpath.read_text(encoding="utf-8")
            evidence=dict(status="passed",fresh_server=True,external_tcp_blocked_in_server=True,os_network_settings_changed=False,
                          frontend_asset_audit="All scripts, stylesheet and favicon are local/data assets; no CDN or remote font dependency.",
                          scenarios=results)
            (ROOT/"outputs"/"offline-check.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
            print(json.dumps(evidence,indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__=="__main__":
    serve() if "--serve" in sys.argv else check()

"""Run with .venv/Scripts/python.exe run.py (Windows), or .venv/bin/python run.py."""
import argparse

import uvicorn

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Local office floor plan application")
    parser.add_argument("--port",type=int,default=8000)
    args=parser.parse_args()
    uvicorn.run("app.main:app",host="127.0.0.1",port=args.port,log_level="info")

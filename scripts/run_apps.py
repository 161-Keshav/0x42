"""Run all portals with one local Chroma writer. Ctrl+C stops their processes."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from skill_erosion.config import data_dir
from skill_erosion.embeddings.service import start_chroma, stop_chroma, stop_process

ROOT = Path(__file__).resolve().parents[1]
APPS = [("teacher_dashboard", 8501), ("student_portal", 8502), ("parent_portal", 8503)]
CHROMA_PORT = 8504


def main():
    for name, port in APPS + [("shared Chroma", CHROMA_PORT)]:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"Port {port} ({name}) is already in use; stop the existing app before launching another copy.")
    logdir = ROOT / "data/logs"
    logdir.mkdir(parents=True, exist_ok=True)
    processes, handles = [], []
    chroma = None
    resolved_data = data_dir().resolve()
    chroma_path = resolved_data / "processed/chroma"
    try:
        output = (logdir / "chroma-server.log").open("a", encoding="utf-8")
        handles.append(output)
        chroma = start_chroma(chroma_path, CHROMA_PORT, output)
        print(f"Shared Chroma: http://127.0.0.1:{CHROMA_PORT} (PID {chroma.pid})", flush=True)
        for app, port in APPS:
            handle = (logdir / f"{app}-server.log").open("a", encoding="utf-8")
            handles.append(handle)
            process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(ROOT / f"apps/{app}/app.py"),
                 "--server.port", str(port), "--server.address", "127.0.0.1", "--server.headless", "true"],
                cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                env={**os.environ, "SKILL_EROSION_DATA_DIR": str(resolved_data)},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            processes.append(process)
            print(f"{app}: http://127.0.0.1:{port} (PID {process.pid})", flush=True)
        (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
        (ROOT / "data/processed/app_processes.json").write_text(json.dumps(
            [dict(app=a, port=p, pid=proc.pid) for (a, p), proc in zip(APPS, processes)], indent=2))
        while chroma.poll() is None and all(p.poll() is None for p in processes):
            time.sleep(1)
        raise RuntimeError("A GapTrace service stopped; inspect the logs under data/logs.")
    except KeyboardInterrupt:
        print("Stopping GapTrace portals.")
    finally:
        for process in processes:
            stop_process(process)
        if chroma is not None:
            stop_chroma(chroma, chroma_path)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()

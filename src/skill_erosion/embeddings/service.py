"""Own one loopback-only Chroma writer when several portal processes share data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import chromadb
from chromadb.config import Settings


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Python's Windows venv launcher can have a real interpreter child.
        # Only terminate the tree that this launcher created.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def start_chroma(path, port, output):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-c", "from chromadb.cli.cli import app; app()", "run",
               "--path", str(path), "--host", "127.0.0.1", "--port", str(port)]
    process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                               env={**os.environ, "ANONYMIZED_TELEMETRY": "False"},
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 35
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("The shared Chroma service stopped during startup. Check chroma-server.log.")
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/v2/heartbeat", timeout=1) as response:
                    if response.status == 200:
                        token = uuid4().hex
                        client = chromadb.HttpClient(host="127.0.0.1", port=port, settings=Settings(anonymized_telemetry=False))
                        try:
                            identity = client.get_or_create_collection("gaptrace-service-identity", embedding_function=None)
                            identity.modify(metadata={"instance_token": token})
                        finally:
                            client.close()
                        descriptor = {"path": str(path), "port": port, "pid": process.pid, "instance_token": token}
                        marker = path.parent / "chroma-server.json"
                        temporary = marker.with_suffix(f".{process.pid}.tmp")
                        temporary.write_text(json.dumps(descriptor), encoding="utf-8")
                        temporary.replace(marker)
                        return process
            except (URLError, TimeoutError):
                time.sleep(.15)
        raise RuntimeError("The shared Chroma service did not become ready. Check chroma-server.log.")
    except BaseException:
        stop_process(process)
        raise


def stop_chroma(process, path):
    stop_process(process)
    marker = Path(path).resolve().parent / "chroma-server.json"
    if marker.exists():
        descriptor = json.loads(marker.read_text(encoding="utf-8"))
        if descriptor.get("pid") == process.pid:
            marker.unlink()

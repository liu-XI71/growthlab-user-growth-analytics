from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamlit_starts_headlessly_without_api_dependency() -> None:
    port = _free_port()
    environment = dict(os.environ)
    environment["GROWTHLAB_API_URL"] = "http://127.0.0.1:9"
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/streamlit_app.py",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
    ]
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = ""
    try:
        deadline = time.monotonic() + 35
        url = f"http://127.0.0.1:{port}/_stcore/health"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise AssertionError(f"Streamlit exited before becoming healthy:\n{output}")
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    body = response.read().decode("utf-8").strip().lower()
                    assert response.status == 200
                    assert body == "ok"
                    return
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        raise AssertionError("Streamlit did not become healthy within 35 seconds")
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

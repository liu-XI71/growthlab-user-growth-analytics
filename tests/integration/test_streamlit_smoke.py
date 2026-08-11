from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamlit_starts_headlessly_without_api_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    real_urlopen = urllib.request.urlopen
    health_attempts = 0

    def reset_first_health_request(*args, **kwargs):
        """Exercise the Windows listen-before-ready reset retry path deterministically."""
        nonlocal health_attempts
        health_attempts += 1
        if health_attempts == 1:
            raise ConnectionResetError(10054, "connection reset during Streamlit startup")
        return real_urlopen(*args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", reset_first_health_request)
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
            # Windows can accept the socket and reset it once before Streamlit is ready.
            # Retry all transport-level OSErrors only inside the bounded startup deadline.
            except OSError:
                time.sleep(0.25)
        raise AssertionError("Streamlit did not become healthy within 35 seconds")
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

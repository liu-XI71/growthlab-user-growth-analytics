from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from streamlit.testing.v1 import AppTest

from scripts.generate_demo_data import generate_database

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_all_six_option_b_streamlit_modules_execute_against_live_api(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "streamlit-pages.duckdb"
    generate_database(database, users=5_000, seed=42)
    port = _free_port()
    environment = dict(os.environ)
    environment["GROWTHLAB_DB_PATH"] = str(database)
    environment["GROWTHLAB_AUTO_GENERATE_DEMO"] = "false"
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        deadline = time.monotonic() + 35
        health_url = f"http://127.0.0.1:{port}/health"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise AssertionError(f"FastAPI exited before page testing:\n{output}")
            try:
                with urllib.request.urlopen(health_url, timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        else:
            raise AssertionError("FastAPI did not become healthy within 35 seconds")

        monkeypatch.setenv("GROWTHLAB_API_URL", f"http://127.0.0.1:{port}")
        pages = [
            "frontend/pages/executive_cockpit.py",
            "frontend/pages/growth_lifecycle.py",
            "frontend/pages/investigation_studio.py",
            "frontend/pages/experiment_causal_lab.py",
            "frontend/pages/growth_economics.py",
            "frontend/pages/decision_governance.py",
        ]
        for page in pages:
            app = AppTest.from_file(str(PROJECT_ROOT / page), default_timeout=30).run()
            assert not list(app.exception), f"Streamlit page raised an exception: {page}"
            assert len(app.markdown) + len(app.title) + len(app.header) > 0
        shell = AppTest.from_file(
            str(PROJECT_ROOT / "frontend" / "streamlit_app.py"), default_timeout=30
        ).run()
        assert not list(shell.exception), "Streamlit navigation shell raised an exception"
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

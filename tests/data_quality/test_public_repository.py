from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}


def _public_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        tracked = [PROJECT_ROOT / line for line in result.stdout.splitlines() if line]
        if tracked:
            return [path for path in tracked if path.is_file()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return [
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file()
        and not any(part in EXCLUDED_PARTS for part in path.parts)
        and not ("data" in path.parts and "demo" in path.parts and path.suffix == ".duckdb")
    ]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_public_repository_contains_no_real_company_or_internal_scale_markers() -> None:
    forbidden = {
        # Build terms at runtime so the QA rule does not itself publish the protected identifiers.
        "company_name": "\u6296" + "\u97f3",
        "business_product": "\u7ea2" + "\u679c",
        "internal_org_phrase": "\u4e8b\u4e1a" + "\u90e8-\u7ea2\u679c",
        "real_dau_current": "6500" + "w",
        "real_dau_target": "8000" + "w",
        "real_experiment_scale_cn": "700" + "\u4e07",
        "real_experiment_scale_ascii": "700" + "w",
        "real_reward_low": "55" + "\u5143",
        "real_reward_high": "88" + "\u5143",
    }
    findings: list[str] = []
    for path in _public_files():
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Dockerfile",
            "Makefile",
            "LICENSE",
        }:
            continue
        text = _read_text(path).lower()
        for label, term in forbidden.items():
            if term.lower() in text:
                findings.append(f"{path.relative_to(PROJECT_ROOT)}: {label}")
    assert not findings, "Confidential/internal markers found:\n" + "\n".join(findings)


def test_public_repository_contains_no_obvious_credentials_or_private_keys() -> None:
    prefix = "sk" + "-"
    patterns = {
        "private_key": re.compile("BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
        "generic_openai_style_token": re.compile(re.escape(prefix) + r"[A-Za-z0-9_-]{20,}"),
        "github_personal_token": re.compile("gh" + r"[pousr]_[A-Za-z0-9]{30,}"),
        "aws_access_key": re.compile("AK" + r"IA[0-9A-Z]{16}"),
        "credential_url": re.compile(r"(?:postgres|mysql)://[^\s/:]+:[^\s/@]+@", re.IGNORECASE),
        "assigned_secret": re.compile(
            r"(?i)(?:api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"
        ),
    }
    findings: list[str] = []
    for path in _public_files():
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile", "Makefile"}:
            continue
        text = _read_text(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(PROJECT_ROOT)}: {label}")
    assert not findings, "Potential credentials found:\n" + "\n".join(findings)


def test_no_local_environment_or_large_binary_is_publication_candidate() -> None:
    files = _public_files()
    forbidden_environment_files = [
        path.relative_to(PROJECT_ROOT)
        for path in files
        if path.name.startswith(".env") and path.name != ".env.example"
    ]
    assert not forbidden_environment_files
    oversized = [
        f"{path.relative_to(PROJECT_ROOT)} ({path.stat().st_size} bytes)"
        for path in files
        if path.stat().st_size > 10 * 1024 * 1024
    ]
    assert not oversized, "Files over 10 MiB should not be published:\n" + "\n".join(oversized)

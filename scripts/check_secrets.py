"""Chequeo simple de secretos en archivos staged antes de commitear."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SECRET_ASSIGNMENT_PATTERNS = [
    re.compile(
        r"^\s*(SECRET_KEY|GEMINI_API_KEY|CLAUDE_API_KEY|WP_APP_PASSWORD|META_ACCESS_TOKEN|"
        r"TWITTER_API_KEY|TWITTER_API_SECRET|TWITTER_ACCESS_TOKEN|TWITTER_ACCESS_SECRET|"
        r"TELEGRAM_BOT_TOKEN)\s*=\s*(.+?)\s*$"
    ),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
]

PLACEHOLDER_VALUES = {
    "",
    '""',
    "''",
    "cambiar-esto",
    "changeme",
    "example",
    "tu-token-aqui",
    "your-token-here",
}

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".env",
    ".example",
    ".sh",
    ".ps1",
    ".jsx",
    ".js",
    ".css",
    ".html",
}


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _staged_files() -> list[str]:
    output = _run_git("diff", "--cached", "--name-only", "--diff-filter=ACM")
    return [line.strip() for line in output.splitlines() if line.strip()]


def _should_scan(path: str) -> bool:
    suffixes = Path(path).suffixes
    if not suffixes:
        return Path(path).name.startswith(".env")
    return any(suffix in TEXT_EXTENSIONS for suffix in suffixes)


def _staged_content(path: str) -> str:
    return _run_git("show", f":{path}")


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"').strip("'").lower()
    return normalized in PLACEHOLDER_VALUES


def find_secret_issues() -> list[str]:
    issues: list[str] = []
    for path in _staged_files():
        if not _should_scan(path):
            continue
        try:
            content = _staged_content(path)
        except subprocess.CalledProcessError:
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            for pattern in SECRET_ASSIGNMENT_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if match.lastindex and match.lastindex >= 2:
                    value = match.group(2).strip()
                    if _is_placeholder(value):
                        continue
                issues.append(f"{path}:{lineno}")
    return issues


def main() -> int:
    try:
        issues = find_secret_issues()
    except subprocess.CalledProcessError as error:
        print(f"No se pudo ejecutar git para revisar secretos: {error}", file=sys.stderr)
        return 1

    if not issues:
        print("Chequeo de secretos OK.")
        return 0

    print("Se detectaron posibles secretos en archivos staged:", file=sys.stderr)
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)
    print("Abortando commit. Revisa esos valores o muevelos a .env.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

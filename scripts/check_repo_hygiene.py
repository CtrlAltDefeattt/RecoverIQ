from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT_BYTES = 2_000_000
FORBIDDEN_NAMES = {".env", ".env.local", ".env.production", ".env.preview"}
FORBIDDEN_SUFFIXES = {".db", ".key", ".pem", ".sqlite", ".sqlite3"}
REQUIRED_IGNORES = {".env.*", ".next/", ".vercel/", "*.key", "*.pem", "*.sqlite3"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{32,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{32,}\b"),
    "Razorpay live key": re.compile(r"\brzp_live_[A-Za-z0-9]{8,}\b"),
    "Stripe live key": re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}


def tracked_paths(root: Path = ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [root / item.decode() for item in result.stdout.split(b"\0") if item]


def check_repository(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    paths = tracked_paths(root)

    for path in paths:
        relative = path.relative_to(root)
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            issues.append(f"forbidden tracked file: {relative}")
            continue
        if not path.is_file() or path.stat().st_size > MAX_TEXT_BYTES:
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            continue
        text = raw.decode("utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                issues.append(f"possible {label} in {relative}")

    gitignore = (root / ".gitignore").read_text().splitlines()
    configured = {line.strip() for line in gitignore if line.strip() and not line.startswith("#")}
    for rule in sorted(REQUIRED_IGNORES - configured):
        issues.append(f"missing .gitignore rule: {rule}")
    return issues


def main() -> None:
    issues = check_repository()
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}")
        raise SystemExit(1)
    print("Repository hygiene check passed: no tracked secrets or local state detected.")


if __name__ == "__main__":
    main()

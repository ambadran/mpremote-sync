"""Core logic: hashing, mpremote commands, deploy list management."""

from __future__ import annotations

import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path

NOT_FOUND = "__NOT_FOUND__"  # sentinel: file doesn't exist on device


# ── File discovery ────────────────────────────────────────────────────────────


def discover_files(directory: Path, exclude_patterns: list[str]) -> list[str]:
    """Auto-discover .py files in *directory*, excluding *exclude_patterns*."""
    files = []
    for f in sorted(directory.iterdir()):
        if f.suffix == ".py" and not any(
            fnmatch.fnmatch(f.name, pat) for pat in exclude_patterns
        ):
            files.append(f.name)
    return files


# ── Hash helpers ──────────────────────────────────────────────────────────────


def local_sha256(filepath: Path) -> str:
    """Compute SHA-256 of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_sha256(filename: str) -> str | None:
    """Run ``mpremote sha256sum <file>``.

    Returns:
        The hex hash, :data:`NOT_FOUND` if the file is missing on device,
        or ``None`` on a connection/time-out error.
    """
    try:
        result = subprocess.run(
            ["mpremote", "sha256sum", filename],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = result.stdout.strip().splitlines()
        if result.returncode != 0 or len(lines) < 2:
            if "No such file" in result.stderr or "No such file" in result.stdout:
                return NOT_FOUND
            return None
        return lines[-1].strip()
    except FileNotFoundError:
        print("Error: 'mpremote' not found. Is it installed and in PATH?", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return None


# ── Deploy list helpers ──────────────────────────────────────────────────────


def load_deploy_files(path: Path) -> list[str]:
    """Read the pinned deploy list. Exits with usage hint if missing."""
    if not path.exists():
        print(
            f"Error: deploy list '{path}' not found.\n"
            f"  Run with --update first to create it.",
            file=sys.stderr,
        )
        sys.exit(1)
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def write_deploy_files(path: Path, files: list[str]) -> None:
    """Write the deploy list (one filename per line)."""
    path.write_text("\n".join(files) + "\n")
    print(f"Wrote {len(files)} file(s) to {path}")


# ── File upload ──────────────────────────────────────────────────────────────


def upload_file(local_path: Path, filename: str) -> bool:
    """Run ``mpremote cp <local> :<remote>``. Returns ``True`` on success."""
    print(f"       uploading {local_path} -> :{filename} ...", end=" ", flush=True)
    try:
        result = subprocess.run(
            ["mpremote", "cp", str(local_path), f":{filename}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("done")
            return True
        print("failed")
        if result.stderr:
            print(f"       {result.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print("timed out")
        return False

"""CLI entry-point: argument parsing and orchestration."""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

from . import __version__
from .core import (
    NOT_FOUND,
    discover_files,
    local_sha256,
    load_deploy_files,
    remote_sha256,
    upload_file,
    write_deploy_files,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mpremote-sync",
        description=(
            "Verify that Python files on a MicroPython device match your local copies.\n"
            "Reads a pinned deploy list (.deploy_files) — create/update it with --update."
        ),
        epilog=(
            "Examples:\n"
            "  mpremote-sync -d ./firmware --update   Scan and save deploy list\n"
            "  mpremote-sync -d ./firmware            Check files\n"
            "  mpremote-sync -d ./firmware --fix      Sync mismatches to device\n"
            "\n"
            "Typical workflow:\n"
            "  1. Add/remove .py files in your project directory\n"
            "  2. mpremote-sync -d ./firmware --update         (regenerate deploy list)\n"
            "  3. mpremote-sync -d ./firmware --fix            (upload anything new/changed)\n"
            "  4. Daily: mpremote-sync -d ./firmware --fix     (keep device in sync)\n"
            "\n"
            "The deploy list defaults to <directory>/.deploy_files (one filename per line).\n"
            "Override its location with --list.\n"
            "Excluded patterns default to '*_template.py' — override with --exclude."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-d", "--directory",
        default=".",
        metavar="DIR",
        help="Directory containing the Python files to deploy (default: current directory)",
    )
    parser.add_argument(
        "-l", "--list",
        default=None,
        metavar="FILE",
        dest="deploy_list",
        help="Path to the deploy list file (default: <directory>/.deploy_files)",
    )
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        default=["*_template.py"],
        metavar="PATTERN",
        help="Glob pattern to exclude during --update. Repeat for multiple patterns. (default: *_template.py)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="After checking, auto-upload any mismatched or missing files using `mpremote cp` and verify the upload",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rescan the source directory for .py files, apply exclusion patterns, and write the deploy list. Exits immediately after.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    source_dir = Path(args.directory).resolve()
    deploy_list_path = (
        Path(args.deploy_list).resolve()
        if args.deploy_list
        else source_dir / ".deploy_files"
    )

    if not source_dir.is_dir():
        print(f"Error: '{source_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # ── --update: rescan and write the list, then exit ────────────────────
    if args.update:
        files = discover_files(source_dir, args.exclude)
        if not files:
            print("No Python files found to deploy.")
            sys.exit(0)
        print(f"Scanned {source_dir}: {', '.join(files)}")
        write_deploy_files(deploy_list_path, files)
        sys.exit(0)

    # ── Normal run: use the pinned deploy list ────────────────────────────
    files = load_deploy_files(deploy_list_path)
    if not files:
        print("Deploy list is empty. Run with --update first.", file=sys.stderr)
        sys.exit(1)

    print(f"Checking files in: {source_dir}")
    print(f"Deploy list ({len(files)}): {', '.join(files)}")
    if args.fix:
        print("(mismatched files will be auto-uploaded)")
    print("-" * 72)

    all_ok = True
    fixed = 0
    failed = 0

    for filename in files:
        local_path = source_dir / filename

        if not local_path.exists():
            print(f"  {filename:<20} ❌  local file not found")
            all_ok = False
            continue

        local_hash = local_sha256(local_path)
        remote_hash = remote_sha256(filename)

        if remote_hash is None:
            print(f"  {filename:<20} ⚠️  could not fetch remote hash")
            all_ok = False
            continue

        if remote_hash == NOT_FOUND:
            print(f"  {filename:<20} ❌  not on device")
            all_ok = False
        elif local_hash == remote_hash:
            print(f"  {filename:<20} ✅  match ({local_hash[:16]}...)")
            continue
        else:
            print(f"  {filename:<20} ❌  MISMATCH")
            print(f"       local  : {local_hash}")
            print(f"       remote : {remote_hash}")
            all_ok = False

        if args.fix:
            if upload_file(local_path, filename):
                new_remote_hash = remote_sha256(filename)
                if new_remote_hash == local_hash:
                    print(f"       ✅  upload verified")
                    all_ok = True
                    fixed += 1
                else:
                    print(f"       ❌  upload did not fix hash")
                    print(f"       remote : {new_remote_hash}")
                    failed += 1
            else:
                print(f"       ❌  could not upload {filename}")
                failed += 1

    print("-" * 72)
    if all_ok:
        if fixed:
            print(f"All files are in sync now ({fixed} uploaded). 🎉")
        else:
            print("All files are in sync. 🎉")
    else:
        if args.fix and failed:
            print(f"{failed} file(s) could not be fixed. Review above.")
        else:
            print("Some files are out of sync. Review the mismatches above.")
        sys.exit(1)

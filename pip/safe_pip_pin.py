#!/usr/bin/env python3
"""Resolve PyPI packages to the latest version published ≥ 7 days ago and
generate a requirements.txt with pinned versions and sha256 hashes for the
full dependency tree (via pip-compile).

Usage:
    python safe_pip_pin.py requests flask numpy
    python safe_pip_pin.py requests flask numpy -o requirements.txt
    python safe_pip_pin.py requests flask numpy --min-age 14
    python safe_pip_pin.py requests flask numpy --no-compile

Requires: pip-tools (will be auto-installed if missing).
"""

import argparse
import datetime
import json
import sys
import urllib.request
import urllib.error


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


try:
    from packaging.version import Version as _PkgVersion

    def is_stable_version(version: str) -> bool:
        """Use PEP 440 parsing (via packaging) to detect pre-releases."""
        try:
            return not _PkgVersion(version).is_prerelease
        except Exception:
            return _is_stable_fallback(version)
except ImportError:
    def is_stable_version(version: str) -> bool:
        return _is_stable_fallback(version)


def _is_stable_fallback(version: str) -> bool:
    """Simple string-based check as fallback when packaging is unavailable."""
    import re
    v = version.lower()
    if ".dev" in v or v.startswith("dev"):
        return False
    if re.search(r"(a|alpha|b|beta|rc|c)\d*(\.|$)", v):
        return False
    return True


def get_safe_version(package: str, min_age_days: int) -> str:
    data = fetch_json(f"https://pypi.org/pypi/{package}/json")
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=min_age_days)
    candidates = []
    for version, files in data["releases"].items():
        if not files:
            continue
        if not is_stable_version(version):
            continue
        upload_time = datetime.datetime.fromisoformat(files[0]["upload_time_iso_8601"])
        if upload_time <= cutoff:
            candidates.append((version, upload_time))
    if not candidates:
        raise SystemExit(
            f"ERROR: No stable version of '{package}' is older than {min_age_days} days. "
            f"If this is a critical security patch, verify the release manually and pin it by hand."
        )
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def ensure_pip_tools():
    """Check that pip-compile is available, offer to install pip-tools if not."""
    import shutil
    if shutil.which("pip-compile"):
        return
    sys.stderr.write("pip-compile not found. Installing pip-tools ...\n")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pip-tools"],
                          stdout=sys.stderr, stderr=sys.stderr)
    # Verify it's available now
    if not shutil.which("pip-compile"):
        raise SystemExit(
            "ERROR: pip-compile still not found after installing pip-tools. "
            "Please install it manually: pip install pip-tools"
        )


def main():
    import os
    import subprocess

    parser = argparse.ArgumentParser(
        description="Pin PyPI packages with age filter and hashes (via pip-compile)."
    )
    parser.add_argument("packages", nargs="+", help="Package names to resolve.")
    parser.add_argument("-o", "--output", default="requirements.txt",
                        help="Output requirements.txt file (default: requirements.txt).")
    parser.add_argument("--min-age", type=int, default=7, help="Minimum age in days (default: 7).")
    parser.add_argument("--no-compile", action="store_true",
                        help="Only write requirements.in, skip pip-compile.")
    args = parser.parse_args()

    # Determine the .in file path from the output path
    base, ext = os.path.splitext(args.output)
    in_file = base + ".in"

    # Resolve safe versions and write requirements.in
    in_lines = [
        f"# Auto-generated — top-level versions are ≥ {args.min_age} days old.",
        f"# Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"# Run pip-compile --generate-hashes to produce {args.output}",
        "",
    ]

    for pkg in args.packages:
        sys.stderr.write(f"Resolving {pkg} ... ")
        version = get_safe_version(pkg, args.min_age)
        sys.stderr.write(f"{version}\n")
        in_lines.append(f"{pkg}=={version}")

    in_content = "\n".join(in_lines) + "\n"

    with open(in_file, "w") as f:
        f.write(in_content)
    sys.stderr.write(f"\nWritten {in_file}\n")

    if args.no_compile:
        sys.stderr.write(
            f"\nNext steps:\n"
            f"  1. pip install pip-tools     (if not installed)\n"
            f"  2. pip-compile --generate-hashes {in_file} -o {args.output}\n"
            f"  3. pip install --require-hashes -r {args.output}\n"
        )
        return

    # Run pip-compile to resolve full dependency tree with hashes
    ensure_pip_tools()
    sys.stderr.write(f"\nRunning pip-compile to resolve full dependency tree ...\n")
    try:
        subprocess.check_call([
            "pip-compile",
            "--generate-hashes",
            "--strip-extras",
            "--no-header",
            "--output-file", args.output,
            in_file,
        ], stderr=sys.stderr)
    except subprocess.CalledProcessError:
        raise SystemExit(
            f"ERROR: pip-compile failed. You can retry manually:\n"
            f"  pip-compile --generate-hashes {in_file} -o {args.output}"
        )

    sys.stderr.write(
        f"\nDone! {args.output} contains all dependencies with sha256 hashes.\n"
        f"\nInstall with:\n"
        f"  pip install --require-hashes -r {args.output}\n"
    )


if __name__ == "__main__":
    main()

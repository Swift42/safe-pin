#!/usr/bin/env python3
"""Resolve Packagist (Composer) packages to the latest version published ≥ 7 days ago
and generate a composer.json with pinned exact versions.

After running this, run `composer update` to generate composer.lock (which includes
dist references and shasums), then always install with `composer install`.

Usage:
    python safe_composer_pin.py monolog/monolog guzzlehttp/guzzle
    python safe_composer_pin.py monolog/monolog guzzlehttp/guzzle -o composer.json
    python safe_composer_pin.py monolog/monolog --min-age 14
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
import urllib.error


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "safe-composer-pin/1.0 (supply-chain-safety)"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def is_stable_version(version: str) -> bool:
    """Return True if the version string looks like a stable release (no dev/alpha/beta/RC)."""
    v = version.lower()
    if v.startswith("dev-") or v.endswith("-dev"):
        return False
    if re.search(r"(alpha|beta|rc|patch)\d*$", v, re.IGNORECASE):
        return False
    return True


def get_safe_version(package: str, min_age_days: int) -> tuple[str, str | None]:
    """Return (version, dist_shasum) for the latest stable Packagist version ≥ min_age_days old."""
    data = fetch_json(f"https://packagist.org/packages/{package}.json")
    versions = data.get("package", {}).get("versions", {})
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=min_age_days)

    candidates = []
    for ver_key, ver_data in versions.items():
        if not is_stable_version(ver_key):
            continue
        time_str = ver_data.get("time")
        if not time_str:
            continue
        # Parse ISO 8601 timestamp
        try:
            upload_time = datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if upload_time.tzinfo is None:
            upload_time = upload_time.replace(tzinfo=datetime.timezone.utc)
        if upload_time <= cutoff:
            shasum = ver_data.get("dist", {}).get("shasum", "") or None
            candidates.append((ver_key, upload_time, shasum))

    if not candidates:
        raise SystemExit(
            f"ERROR: No stable version of '{package}' is older than {min_age_days} days. "
            f"If this is a critical security patch, verify the release manually and pin it by hand."
        )

    # Sort by time descending, pick newest safe version
    candidates.sort(key=lambda x: x[1], reverse=True)
    chosen = candidates[0]
    return chosen[0], chosen[2]


def normalize_version(version: str) -> str:
    """Strip a leading 'v' for the composer.json constraint (e.g. v3.5.0 -> 3.5.0)."""
    if version.startswith("v"):
        return version[1:]
    return version


def main():
    parser = argparse.ArgumentParser(description="Pin Composer packages with age filter.")
    parser.add_argument("packages", nargs="+", help="Package names (vendor/package).")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: stdout).")
    parser.add_argument("--min-age", type=int, default=7, help="Minimum age in days (default: 7).")
    args = parser.parse_args()

    deps = {}
    notes = []

    for pkg in args.packages:
        if "/" not in pkg:
            raise SystemExit(f"ERROR: '{pkg}' does not look like a Composer package name (expected vendor/package).")
        sys.stderr.write(f"Resolving {pkg} ... ")
        version, shasum = get_safe_version(pkg, args.min_age)
        pinned = normalize_version(version)
        sys.stderr.write(f"{version}")
        if shasum:
            sys.stderr.write(f" (shasum: {shasum[:12]}...)")
            notes.append(f"# {pkg}=={pinned} dist shasum: {shasum}")
        else:
            sys.stderr.write(" (no dist shasum available — rely on composer.lock reference)")
        sys.stderr.write("\n")
        deps[pkg] = pinned

    # Build or merge composer.json
    target_path = args.output or "composer.json"
    pkg_json = {}
    if os.path.exists(target_path):
        try:
            with open(target_path) as f:
                pkg_json = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    if "require" not in pkg_json:
        pkg_json["require"] = {}

    pkg_json["require"].update(deps)

    result = json.dumps(pkg_json, indent=4, ensure_ascii=False) + "\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        sys.stderr.write(f"\nWritten to {args.output}\n")
        if notes:
            sys.stderr.write("\nDist checksums (for reference):\n")
            for n in notes:
                sys.stderr.write(f"  {n}\n")
        sys.stderr.write(
            "\nNext steps:\n"
            "  1. composer update          (generates composer.lock with dist references)\n"
            "  2. composer install          (use this for all future installs)\n"
        )
    else:
        print(result)
        if notes:
            sys.stderr.write("\nDist checksums (for reference):\n")
            for n in notes:
                sys.stderr.write(f"  {n}\n")
        sys.stderr.write(
            "\nNext steps:\n"
            "  1. Save the above as composer.json\n"
            "  2. composer update          (generates composer.lock with dist references)\n"
            "  3. composer install          (use this for all future installs)\n"
        )


if __name__ == "__main__":
    main()

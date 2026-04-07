---
name: pip
description: >
  Secure Python dependency management with pip. Use this skill whenever you need to install
  Python packages with pip, add dependencies to a Python project, or generate a requirements.txt.
  This skill enforces supply chain safety: pinned versions, age filtering, and sha256 hash
  verification. Trigger on any mention of pip, requirements.txt, pip install, or adding Python
  packages to a project — even if the user doesn't explicitly ask for security hardening.
---

# pip — Secure Dependency Pinning

## Package managers — CRITICAL

Never install Python packages with loose or unpinned versions. Every dependency must be:

1. **Pinned to an exact version** — no ranges or wildcards.
2. **At least 7 days old** — to let the community catch supply chain attacks before you adopt a release.
3. **Verified by sha256 hash** — so a compromised registry cannot swap out the file contents.

## How to pin

Use the `safe_pip_pin.py` script bundled in this skill's folder:

```bash
python safe_pip_pin.py requests flask numpy -o requirements.txt
pip install --require-hashes -r requirements.txt
```

The script accepts `--min-age <days>` (default: 7) and `--no-compile` (to only write the `.in` file without running pip-compile).

### What the script does

1. Queries the PyPI JSON API for each package.
2. Filters out pre-release versions (dev, alpha, beta, RC) using PEP 440 parsing.
3. Finds the latest stable version published ≥ 7 days ago.
4. Writes a `requirements.in` with exact top-level pins.
5. Runs `pip-compile --generate-hashes` (from `pip-tools`) to resolve the **full dependency tree** — including all transitive dependencies — and writes a `requirements.txt` with exact pins and sha256 hashes for every package.

If `pip-tools` is not installed, the script will auto-install it.

### How to install

Always use `--require-hashes` so pip verifies every download:

```bash
pip install --require-hashes -r requirements.txt
```

### Important: requirements.in vs requirements.txt

- `requirements.in` — your top-level dependencies (age-filtered, human-editable).
- `requirements.txt` — the full resolved tree with hashes (auto-generated, do not edit by hand).

When updating dependencies, edit or re-run the script to update `requirements.in`, then let `pip-compile` regenerate `requirements.txt`.

## Emergency overrides

If a critical security patch was released less than 7 days ago, you may override the age rule **only after** manually verifying the release (check changelog, diff the source, confirm the publisher). Document the override with a comment in `requirements.txt`.

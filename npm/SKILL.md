---
name: npm
description: >
  Secure Node.js dependency management with npm. Use this skill whenever you need to install
  npm packages, add dependencies to a Node.js project, or generate a package.json / package-lock.json.
  This skill enforces supply chain safety: pinned versions, age filtering, and integrity hash
  verification. Trigger on any mention of npm, package.json, npm install, or adding Node.js
  packages to a project — even if the user doesn't explicitly ask for security hardening.
---

# npm — Secure Dependency Pinning

## Package managers — CRITICAL

Never install npm packages with loose or unpinned versions. Every dependency must be:

1. **Pinned to an exact version** — no `^`, `~`, or ranges.
2. **At least 7 days old** — to let the community catch supply chain attacks before you adopt a release.
3. **Verified by integrity hash** — so a compromised registry cannot swap out the file contents.

## How to pin

Use the `safe_npm_pin.js` script bundled in this skill's folder:

```bash
node safe_npm_pin.js express lodash axios --output package.json
node safe_npm_pin.js jest eslint --dev --output package.json
npm install   # generates package-lock.json with integrity hashes
npm ci        # use this for all future installs
```

The script accepts `--min-age <days>` (default: 7) and `--dev` / `-D` to write to `devDependencies`.

### What the script does

1. Runs `npm view <package> time --json` to get publication dates for every version.
2. Filters out pre-release versions (any version containing a `-`, per semver: dev, alpha, beta, rc, etc.).
3. Finds the latest stable version published ≥ 7 days ago.
3. Writes the exact version (no `^` or `~`) into `dependencies` (or `devDependencies` with `--dev`).
4. If the package already exists in the other section, removes it to avoid duplicates.
5. If an existing `package.json` exists at the output path, merges into it.

### How to install

After generating `package.json`, run `npm install` once to create `package-lock.json` (which automatically includes `sha512` integrity hashes for every resolved package). For all subsequent installs, always use:

```bash
npm ci
```

`npm ci` installs from the lock file and verifies every package against its recorded integrity hash. It fails if the lock file and `package.json` are out of sync.

## Emergency overrides

If a critical security patch was released less than 7 days ago, you may override the age rule **only after** manually verifying the release (check changelog, diff the source, confirm the publisher). Document the override with a comment in `package.json`.

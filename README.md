# safe-pin — Install dependencies safely (manually and/or automatically as a Claude Code skill)

When you run `pip install flask` or `npm install express`, you trust that the package you get today is the same one everyone else has been using. But what if it isn't?

Supply chain attacks on package registries are real and increasingly common. An attacker compromises a maintainer's account, pushes a malicious version, and within minutes thousands of developers install it. By the time it's discovered and pulled — hours or days later — the damage is done.

**safe-pin** is a set of small scripts that add two simple safety rules to your dependency management:

1. **Only install versions that have been public for at least 7 days.** This gives the community, security scanners, and registry maintainers time to catch and remove malicious releases before you ever touch them.

2. **Verify every download with a cryptographic hash.** Even if a registry is compromised or a CDN serves the wrong file, the hash check will catch it.

That's it. No new tools to learn, no infrastructure to set up. Just a thin safety layer on top of pip, npm, and Composer.

## tl;dr: Using as Claude Code Skills

Each script lives in its own folder with a `SKILL.md` file, making them ready to use as [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills). Copy the folders to `~/.claude/skills/`:

```bash
cp -r pip npm composer ~/.claude/skills/
```

The skills can be invoked explicitly with `/pip`, `/npm`, or `/composer`, or Claude can pick them up automatically when it detects you're installing packages.

For the best results, add the text from the attached CLAUDE.md to your `~/.claude/CLAUDE.md`:

```markdown
## Supply chain safety — ALWAYS ENFORCE

When installing, adding, or updating dependencies with pip, npm, or composer:
- ALWAYS use the corresponding skill (`/pip`, `/npm`, `/composer`) to pin versions securely.
- NEVER run `pip install`, `npm install`, `composer require`, or equivalent with unpinned versions.
- Every dependency must be pinned to an exact version that is at least 7 days old, with hash verification.
- If you are about to install a package without using the skill, stop and use the skill first.
```

## How it works — the short version

Instead of this:

```bash
pip install flask requests        # latest version, no verification
npm install express               # might include a release published 5 minutes ago
composer require monolog/monolog  # trusting the registry blindly
```

You do this:

```bash
# Python
python safe_pip_pin.py flask requests -o requirements.txt
pip install --require-hashes -r requirements.txt

# Node.js
node safe_npm_pin.js express --output package.json
npm install && npm ci

# PHP
python safe_composer_pin.py monolog/monolog -o composer.json
composer update && composer install
```

Each script queries the registry, finds the latest version that's at least 7 days old, and pins it. The lock files and hashes take care of the rest.

## Why 7 days?

Most malicious packages are discovered and removed within hours or days. A 7-day quarantine period means you're never the first to try a new release — you let the ecosystem vet it first. It's a simple heuristic, not a guarantee, but it eliminates the most common "smash-and-grab" attacks where a compromised package is published, collects credentials, and gets pulled shortly after.

If a critical security patch drops and you need it immediately, you can override the age rule — but you do it consciously, after checking the changelog and diffing the source. The scripts will tell you clearly when no version meets the age threshold.

## What this does NOT protect against

This approach is defense-in-depth, not a silver bullet.

- **Long-running compromises** — If a trusted maintainer's account is hijacked and the malicious code is subtle enough to evade detection for weeks (like the xz-utils backdoor), the 7-day rule won't help.
- **Transitive dependencies** — The age filter applies to your top-level dependencies. Transitive dependencies (packages pulled in by your dependencies) are resolved normally by the package manager. Once resolved, they are locked and hash-verified on subsequent installs — but their initial resolution doesn't have the age filter.

## Detailed setup

### Python / pip

**Requirements:** Python 3.9+, [pip-tools](https://github.com/jazzband/pip-tools) (auto-installed if missing)

```bash
python safe_pip_pin.py requests flask numpy -o requirements.txt
```

What happens:

1. For each package, the script queries the PyPI JSON API and finds the latest stable version (filtering out dev/alpha/beta/RC releases) published ≥ 7 days ago.
2. Writes a `requirements.in` with the pinned top-level versions.
3. Runs `pip-compile --generate-hashes` to resolve the full dependency tree and produce a `requirements.txt` with sha256 hashes for every package — including transitive dependencies.

Install with hash verification:

```bash
pip install --require-hashes -r requirements.txt
```

Options:

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output file (default: `requirements.txt`) |
| `--min-age` | Minimum version age in days (default: `7`) |
| `--no-compile` | Only write `requirements.in`, skip `pip-compile` |

### Node.js / npm

**Requirements:** Node.js, npm

```bash
node safe_npm_pin.js express lodash axios --output package.json
npm install
npm ci
```

What happens:

1. For each package, the script runs `npm view <package> time --json` and finds the latest version published ≥ 7 days ago.
2. Writes the exact version (no `^` or `~`) into `package.json` — into `dependencies` by default, or `devDependencies` with `--dev`.
3. If the package already exists in the other section (dependencies vs devDependencies), removes it to avoid duplicates.

Then `npm install` generates `package-lock.json` with sha512 integrity hashes for the full dependency tree. Use `npm ci` for all subsequent installs — it verifies every hash.

Options:

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output file (default: `package.json`) |
| `--min-age` | Minimum version age in days (default: `7`) |
| `--dev`, `-D` | Write to `devDependencies` instead of `dependencies` |

### PHP / Composer

**Requirements:** Python 3.9+ (for the script), Composer (for resolving)

```bash
python safe_composer_pin.py monolog/monolog guzzlehttp/guzzle -o composer.json
composer update
composer install
```

What happens:

1. For each package, the script queries the Packagist JSON API and finds the latest stable version (filtering out dev/alpha/beta/RC releases) published ≥ 7 days ago.
2. Writes the exact version into `composer.json`.
3. If an existing `composer.json` exists at the output path, merges into it.

Then `composer update` resolves the full dependency tree and writes `composer.lock` with dist references and shasums. Use `composer install` for all subsequent installs.

Note: not all Packagist packages provide a dist shasum. When missing, `composer.lock` still records the exact git commit reference.

Options:

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output file (default: `composer.json`) |
| `--min-age` | Minimum version age in days (default: `7`) |

## Project structure

```
safe-pin/
├── README.md
├── CLAUDE.md
├── pip/
│   ├── SKILL.md              # Claude Code skill definition
│   └── safe_pip_pin.py       # Script (Python, stdlib + pip-tools)
├── npm/
│   ├── SKILL.md              # Claude Code skill definition
│   └── safe_npm_pin.js       # Script (Node.js, stdlib only)
└── composer/
    ├── SKILL.md              # Claude Code skill definition
    └── safe_composer_pin.py  # Script (Python, stdlib only)
```

All scripts use only standard library modules (plus `pip-tools` for the pip script) and have zero other dependencies.

## Emergency overrides

Sometimes you need a version that's less than 7 days old — typically a critical security patch. All three scripts will exit with a clear error when no version meets the age threshold. In that case:

1. Check the changelog and release notes.
2. Diff the source between the previous and new version.
3. Confirm the publisher is the expected maintainer.
4. Pin the version manually and add a comment explaining the override.

## License

MIT

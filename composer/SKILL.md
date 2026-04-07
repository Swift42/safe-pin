---
name: composer
description: >
  Secure PHP dependency management with Composer. Use this skill whenever you need to install
  Composer packages, add dependencies to a PHP project, or generate a composer.json / composer.lock.
  This skill enforces supply chain safety: pinned versions, age filtering, and hash verification.
  Trigger on any mention of composer, composer.json, composer require, Packagist, or adding PHP
  packages to a project — even if the user doesn't explicitly ask for security hardening.
---

# Composer — Secure Dependency Pinning

## Package managers — CRITICAL

Never install Composer packages with loose or unpinned versions. Every dependency must be:

1. **Pinned to an exact version** — no `^`, `~`, or ranges.
2. **At least 7 days old** — to let the community catch supply chain attacks before you adopt a release.
3. **Verified by hash** — so a compromised registry cannot swap out the file contents.

## How to pin

Use the `safe_composer_pin.py` script bundled in this skill's folder:

```bash
python safe_composer_pin.py monolog/monolog guzzlehttp/guzzle -o composer.json
composer update   # generates composer.lock with dist references and shasums
composer install  # use this for all future installs
```

The script accepts `--min-age <days>` (default: 7).

### What the script does

1. Queries the Packagist JSON API (`https://packagist.org/packages/{vendor}/{package}.json`) for each package.
2. Filters out dev, alpha, beta, and RC versions.
3. Finds the latest stable version published ≥ 7 days ago.
4. Writes the exact version into `composer.json`.
5. If an existing `composer.json` exists at the output path, merges into it.

### How to install

After generating `composer.json`, run `composer update` once to create `composer.lock` (which records dist references and shasums). For all subsequent installs, always use:

```bash
composer install
```

`composer install` installs exactly the versions recorded in `composer.lock`.

### Note on hash verification

Not all Packagist packages include a `dist.shasum`. The script reports when a shasum is missing. In those cases, `composer.lock` still records the exact git commit reference, which provides integrity verification through a different mechanism. When a shasum is available, Composer verifies it automatically on download.

## Emergency overrides

If a critical security patch was released less than 7 days ago, you may override the age rule **only after** manually verifying the release (check changelog, diff the source, confirm the publisher). Document the override with a comment in `composer.json`.

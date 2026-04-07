#!/usr/bin/env node
/**
 * Resolve npm packages to the latest version published ≥ 7 days ago
 * and generate a package.json with exact pinned versions.
 * After running this, run `npm install` to generate package-lock.json with integrity hashes,
 * then always install with `npm ci`.
 *
 * Usage:
 *   node safe_npm_pin.js express lodash axios
 *   node safe_npm_pin.js express lodash axios --output package.json
 *   node safe_npm_pin.js express lodash axios --min-age 14
 *   node safe_npm_pin.js jest eslint --dev --output package.json
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

function parseArgs() {
  const args = process.argv.slice(2);
  const result = { packages: [], output: null, minAge: 7, dev: false };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--output" || args[i] === "-o") {
      result.output = args[++i];
    } else if (args[i] === "--min-age") {
      result.minAge = parseInt(args[++i], 10);
    } else if (args[i] === "--dev" || args[i] === "-D") {
      result.dev = true;
    } else if (!args[i].startsWith("-")) {
      result.packages.push(args[i]);
    }
  }
  if (result.packages.length === 0) {
    console.error("Usage: node safe_npm_pin.js <package1> [package2 ...] [--output file] [--min-age days] [--dev]");
    process.exit(1);
  }
  return result;
}

function getSafeVersion(packageName, minAgeDays) {
  const raw = execSync(`npm view ${packageName} time --json`, { encoding: "utf-8" });
  const times = JSON.parse(raw);
  const cutoff = new Date(Date.now() - minAgeDays * 86400000);

  const candidates = Object.entries(times)
    .filter(([v]) => v !== "created" && v !== "modified")
    .filter(([, t]) => new Date(t) <= cutoff)
    .sort((a, b) => new Date(b[1]) - new Date(a[1]));

  if (candidates.length === 0) {
    console.error(
      `ERROR: No version of '${packageName}' is older than ${minAgeDays} days. ` +
      `If this is a critical security patch, verify the release manually and pin it by hand.`
    );
    process.exit(1);
  }
  return candidates[0][0];
}

function main() {
  const { packages, output, minAge, dev } = parseArgs();
  const deps = {};
  const targetField = dev ? "devDependencies" : "dependencies";
  const otherField = dev ? "dependencies" : "devDependencies";

  for (const pkg of packages) {
    process.stderr.write(`Resolving ${pkg} ... `);
    const version = getSafeVersion(pkg, minAge);
    process.stderr.write(`${version}\n`);
    deps[pkg] = version;
  }

  // If an existing package.json exists at the output path, merge into it
  let pkgJson = { name: "project", version: "1.0.0" };
  const targetPath = output || "package.json";
  if (fs.existsSync(targetPath)) {
    try {
      pkgJson = JSON.parse(fs.readFileSync(targetPath, "utf-8"));
    } catch (_) {
      // ignore parse errors, start fresh
    }
  }

  if (!pkgJson[targetField]) pkgJson[targetField] = {};

  for (const pkg of Object.keys(deps)) {
    // Remove from the OTHER section to avoid duplicates
    if (pkgJson[otherField] && pkgJson[otherField][pkg]) {
      delete pkgJson[otherField][pkg];
      process.stderr.write(`  Removed old ${pkg} from ${otherField}\n`);
    }
    pkgJson[targetField][pkg] = deps[pkg];
  }

  const result = JSON.stringify(pkgJson, null, 2) + "\n";

  if (output) {
    fs.writeFileSync(output, result);
    process.stderr.write(
      `\nWritten to ${output}\n` +
      `Next steps:\n` +
      `  1. npm install        (generates package-lock.json with integrity hashes)\n` +
      `  2. npm ci             (use this for all future installs)\n`
    );
  } else {
    console.log(result);
    process.stderr.write(
      `\nNext steps:\n` +
      `  1. Save the above as package.json\n` +
      `  2. npm install        (generates package-lock.json with integrity hashes)\n` +
      `  3. npm ci             (use this for all future installs)\n`
    );
  }
}

main();

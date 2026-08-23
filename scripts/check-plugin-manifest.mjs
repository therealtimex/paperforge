#!/usr/bin/env node
// The manifest is the contract with the RealtimeX host, and nothing in this
// repo checked it: the host's own validator lives in a skill directory, not
// here, so it only ran when someone remembered to run it. This is the repo's
// own copy of the rules that matter, run on the host's Node so the JSON is
// parsed by the same runtime that will parse it in production.
//
// Rules encoded here come from the RealtimeX manifest reference:
//   - id, name and version are required; version is MAJOR.MINOR.PATCH
//   - a declarative-only plugin (skills, workspace_skills,
//     workspace_provisions, local_apps) needs no entrypoint; declaring hooks,
//     api_routes or providers makes one mandatory
//   - every skill directory must exist and contain SKILL.md
//   - skill bundles may not contain symbolic links
import { readFileSync, lstatSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { assertNodeRuntime } from "./node-runtime-contract.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PLUGIN = path.join(ROOT, "plugin");
const RUNTIME_CAPABILITIES = ["hooks", "api_routes", "providers"];
const DECLARATIVE = ["skills", "workspace_skills", "workspace_provisions", "local_apps"];

const problems = [];
const fail = (message) => problems.push(message);

function walkForSymlinks(dir, found) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) {
      found.push(path.relative(PLUGIN, full));
    } else if (entry.isDirectory()) {
      walkForSymlinks(full, found);
    }
  }
  return found;
}

assertNodeRuntime();

const manifestPath = path.join(PLUGIN, "realtimex.plugin.json");
if (!existsSync(manifestPath)) {
  console.error(`missing ${path.relative(ROOT, manifestPath)}`);
  process.exit(1);
}

let manifest;
try {
  manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
} catch (error) {
  console.error(`realtimex.plugin.json is not valid JSON: ${error.message}`);
  process.exit(1);
}

for (const field of ["id", "name", "version"]) {
  if (!manifest[field]) fail(`manifest is missing required field "${field}"`);
}
if (manifest.version && !/^\d+\.\d+\.\d+$/.test(manifest.version)) {
  fail(`version "${manifest.version}" is not MAJOR.MINOR.PATCH`);
}
if (manifest.id && !/^[a-z0-9]+(\.[a-z0-9-]+)+$/.test(manifest.id)) {
  fail(`id "${manifest.id}" is not reverse-DNS (e.g. ai.realtimex.paperforge)`);
}

const capabilities = manifest.capabilities ?? {};
const declared = Object.keys(capabilities).filter(
  (key) => capabilities[key] && Object.keys(capabilities[key]).length > 0,
);
if (declared.length === 0) fail("manifest declares no capabilities");

const needsEntrypoint = declared.some((key) => RUNTIME_CAPABILITIES.includes(key));
if (needsEntrypoint && !manifest.entrypoint) {
  fail(`capabilities ${declared.join(", ")} require an entrypoint`);
}
if (!needsEntrypoint && manifest.entrypoint) {
  fail("declarative-only plugin declares an entrypoint it will never run");
}
for (const key of declared) {
  if (!RUNTIME_CAPABILITIES.includes(key) && !DECLARATIVE.includes(key)) {
    fail(`unknown capability "${key}"`);
  }
}

for (const skill of capabilities.skills ?? []) {
  if (!skill.name) fail("a skill declares no name");
  if (!skill.directory) {
    fail(`skill "${skill.name}" declares no directory`);
    continue;
  }
  const dir = path.join(PLUGIN, skill.directory);
  if (!existsSync(dir) || !lstatSync(dir).isDirectory()) {
    fail(`skill "${skill.name}" directory ${skill.directory} does not exist`);
    continue;
  }
  const skillFile = path.join(dir, "SKILL.md");
  if (!existsSync(skillFile)) {
    fail(`skill "${skill.name}" has no SKILL.md`);
    continue;
  }
  const front = readFileSync(skillFile, "utf8").split("---")[1] ?? "";
  for (const field of ["name", "description"]) {
    if (!new RegExp(`^${field}:`, "m").test(front)) {
      fail(`${skill.directory}/SKILL.md frontmatter has no "${field}"`);
    }
  }
  const links = walkForSymlinks(dir, []);
  if (links.length > 0) {
    fail(`skill bundle contains symbolic links, which the host rejects: ${links.join(", ")}`);
  }
}

if (problems.length > 0) {
  for (const problem of problems) console.error(`  ${problem}`);
  console.error(`plugin manifest: ${problems.length} problem(s)`);
  process.exit(1);
}
console.log(
  `OK: ${manifest.id} ${manifest.version}, ${declared.join(" + ")}, ` +
    `${(capabilities.skills ?? []).length} skill(s)`,
);

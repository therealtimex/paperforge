#!/usr/bin/env node
// The Node that RealtimeX ships. Anything in this repo that runs on Node is
// checking a contract with that host, so it should run on the host's runtime
// rather than on whatever the runner happens to provide.
//
// Signals asserts the module ABI as well, because it loads native addons that
// must match the host binary. Paperforge ships no native modules and no
// JavaScript the host executes - its plugin is declarative - so the version is
// the whole contract here. Asserting an ABI we do not depend on would look
// rigorous and check nothing.
import path from "node:path";
import { pathToFileURL } from "node:url";
import { readFileSync } from "node:fs";

export const NODE_VERSION = readFileSync(
  new URL("../.nvmrc", import.meta.url),
  "utf8",
).trim();

export function assertNodeRuntime({ version = process.version } = {}) {
  if (version !== `v${NODE_VERSION}`) {
    throw new Error(
      `Paperforge targets Node ${NODE_VERSION}, the version RealtimeX ships; ` +
        `received ${version}. Update .nvmrc deliberately if the host has moved.`,
    );
  }
}

const isDirectExecution =
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;

if (isDirectExecution) {
  try {
    assertNodeRuntime();
    console.log(`OK: Node ${NODE_VERSION}, matching the RealtimeX host`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

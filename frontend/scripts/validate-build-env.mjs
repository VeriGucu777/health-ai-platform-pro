/**
 * Fail-fast guard for `next build`: NODE_ENV must be unset or "production".
 * Cross-platform (Node process.env only).
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

const ALLOWED = new Set(["production"]);

/**
 * @param {string | undefined} rawValue - process.env.NODE_ENV (may be undefined)
 * @returns {{ ok: true } | { ok: false; message: string }}
 */
export function validateBuildNodeEnv(rawValue) {
  if (rawValue === undefined) {
    return { ok: true };
  }

  const trimmed = String(rawValue).trim();
  if (trimmed === "") {
    return { ok: true };
  }

  if (ALLOWED.has(trimmed)) {
    return { ok: true };
  }

  return {
    ok: false,
    message: `ERROR: next build requires NODE_ENV to be unset or 'production'. Current NODE_ENV: ${trimmed}.`,
  };
}

function runCli() {
  const result = validateBuildNodeEnv(process.env.NODE_ENV);
  if (!result.ok) {
    console.error(result.message);
    process.exit(1);
  }
}

const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(__filename)) {
  runCli();
}

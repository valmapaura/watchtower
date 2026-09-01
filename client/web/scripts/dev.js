/**
 * Starts the Watchtower backend (Python/FastAPI) and the Next.js frontend
 * together with one command, so users don't have to run two terminals.
 *
 * Usage:
 *   node scripts/dev.js            # start both in dev mode
 *   node scripts/dev.js --prod     # start backend + production frontend
 */
const { spawn } = require("child_process");
const path = require("path");

// Repo root is three levels up from client/web/scripts.
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const CONFIG = path.join(REPO_ROOT, "config.json");
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

const isProd = process.argv.includes("--prod");

// Exit code the backend uses to signal "please restart me" (see api.py).
const RESTART_EXIT_CODE = 42;

function start(name, command, args, opts = {}) {
  const child = spawn(command, args, {
    cwd: opts.cwd || REPO_ROOT,
    shell: false,
    stdio: "inherit",
    env: { ...process.env, ...(opts.env || {}) },
  });
  child.on("error", (err) => {
    console.error(`[${name}] failed to start: ${err.message}`);
  });
  child.on("exit", (code) => {
    console.log(`[${name}] exited with code ${code}`);
  });
  return child;
}

// Start the backend, and respawn it if it exits with the restart code
// (triggered by the "Restart server" button in Settings).
function startBackend() {
  const child = start(
    "backend",
    "python",
    ["-m", "watchtower.api", "--config", CONFIG],
    { cwd: REPO_ROOT }
  );
  child.on("exit", (code) => {
    if (code === RESTART_EXIT_CODE) {
      console.log("\n[backend] restart requested — starting again…\n");
      startBackend();
    }
  });
  return child;
}

console.log("==============================================");
console.log("  Watchtower — starting backend + frontend");
console.log("==============================================");

// 1. Backend (Python FastAPI)
const backend = startBackend();

// 2. Frontend (Next.js). Invoke npm through node + npm-cli.js so it works
// cross-platform without relying on shell resolution of .cmd shims.
function resolveNpmCli() {
  if (process.env.npm_execpath) return process.env.npm_execpath;
  return path.join(
    path.dirname(process.execPath),
    "node_modules",
    "npm",
    "bin",
    "npm-cli.js"
  );
}
const npmCli = resolveNpmCli();
const frontend = start(
  "frontend",
  process.execPath,
  [npmCli, "run", isProd ? "start" : "dev"],
  {
    cwd: path.join(REPO_ROOT, "client", "web"),
    env: { NEXT_PUBLIC_API_URL: `http://localhost:${BACKEND_PORT}` },
  }
);

console.log(`\n  Backend:  http://localhost:${BACKEND_PORT}`);
console.log(`  Frontend: http://localhost:${FRONTEND_PORT}\n`);
console.log("  Press Ctrl+C to stop both.\n");

// Stop both when this script is interrupted.
function shutdown() {
  console.log("\nStopping Watchtower…");
  backend.kill();
  frontend.kill();
  process.exit(0);
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

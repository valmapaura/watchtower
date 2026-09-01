// Watchtower desktop app — main process.
//
// Starts the Python backend and serves the static frontend, then opens a
// desktop window. The backend is auto-started and auto-retried so the app
// "just works" for non-technical users. When the window closes, it shuts the
// backend down.
const { app, BrowserWindow, shell, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");
const { createServer } = require("http");

// Repo root is two levels up from client/desktop (dev mode).
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

// In a packaged build, resources live under process.resourcesPath.
const isPackaged = app.isPackaged;
const RESOURCES = isPackaged ? process.resourcesPath : __dirname;

// In dev, the backend is `python -m watchtower.api`; in a packaged build it's
// the bundled exe in resources.
const BACKEND_EXE = path.join(RESOURCES, "watchtower-backend.exe");
// In dev, the frontend is the static export in client/web/out; packaged it's
// in resources/web-out.
const FRONTEND_DIR = isPackaged
  ? path.join(RESOURCES, "web-out")
  : path.join(REPO_ROOT, "client", "web", "out");

// In dev we point the backend at the repo's config.json. In a packaged build
// the backend defaults to %APPDATA%/Watchtower/config.json, so we don't pass
// --config at all — the app works without touching the install folder.
const CONFIG = isPackaged ? null : path.join(REPO_ROOT, "config.json");

let backend = null;
let frontendServer = null;
let mainWindow = null;
let backendAttempts = 0;
let backendTimer = null;
let backendStarting = false;

// Wait for a URL to respond before opening the window.
function waitFor(url, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Timed out waiting for ${url}`));
        } else {
          setTimeout(check, 500);
        }
      });
    };
    check();
  });
}

// Check if the backend is responding.
function backendOnline() {
  return new Promise((resolve) => {
    const req = http.get(`http://localhost:${BACKEND_PORT}/health`, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// Tell the UI what the backend is doing.
function sendStatus(message, state = "starting") {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("backend-status", { message, state });
  }
}

function startBackend() {
  if (backendStarting) return;
  backendStarting = true;
  backendAttempts += 1;
  sendStatus("Starting the Watchtower service…", "starting");

  const useBundled = fs.existsSync(BACKEND_EXE);
  const cmd = useBundled ? BACKEND_EXE : "python";
  // Packaged: no --config (backend uses %APPDATA%). Dev: point at repo config.
  const args = useBundled
    ? (CONFIG ? ["--config", CONFIG] : [])
    : ["-m", "watchtower.api", "--config", CONFIG];

  backend = spawn(cmd, args, {
    cwd: REPO_ROOT,
    shell: false,
    stdio: "inherit",
  });

  backend.on("error", (err) => {
    console.error("[backend] failed to start:", err.message);
    backendStarting = false;
    scheduleRetry();
  });

  backend.on("exit", (code) => {
    backendStarting = false;
    backend = null;
    if (code === 42) {
      // Restart requested by the UI — start again immediately.
      sendStatus("Restarting the Watchtower service…", "starting");
      startBackend();
    } else if (code !== 0 && code !== null) {
      // Crashed — retry.
      scheduleRetry();
    }
  });

  // Once it's up, tell the UI.
  const check = async () => {
    if (await backendOnline()) {
      sendStatus("Watchtower is running.", "running");
    } else {
      setTimeout(check, 1000);
    }
  };
  setTimeout(check, 1500);
}

function scheduleRetry() {
  if (backendTimer) return;
  if (backendAttempts >= 5) {
    sendStatus(
      "Watchtower couldn't start after several tries. Please restart the app.",
      "error"
    );
    return;
  }
  sendStatus(
    `The service didn't start. Trying again (attempt ${backendAttempts + 1} of 5)…`,
    "starting"
  );
  backendTimer = setTimeout(() => {
    backendTimer = null;
    startBackend();
  }, 3000);
}

// Serve the static frontend (out/) over HTTP so the app works like a website.
function startFrontend() {
  const mime = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
  };

  frontendServer = createServer((req, res) => {
    let urlPath = decodeURIComponent(req.url.split("?")[0]);
    if (urlPath === "/") urlPath = "/index.html";
    let filePath = path.join(FRONTEND_DIR, urlPath);
    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(FRONTEND_DIR, urlPath, "index.html");
    }
    if (!fs.existsSync(filePath)) {
      filePath = path.join(FRONTEND_DIR, "index.html");
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": mime[ext] || "application/octet-stream" });
    fs.createReadStream(filePath).pipe(res);
  });

  frontendServer.listen(FRONTEND_PORT, () => {
    console.log(`[frontend] serving ${FRONTEND_DIR} on :${FRONTEND_PORT}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "Watchtower",
    backgroundColor: "#09090b",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}`);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
    shutdown();
  });
}

function shutdown() {
  if (backendTimer) {
    clearTimeout(backendTimer);
    backendTimer = null;
  }
  if (backend) {
    backend.kill();
    backend = null;
  }
  if (frontendServer) {
    frontendServer.close();
    frontendServer = null;
  }
}

app.whenReady().then(async () => {
  // IPC: the UI can ask the main process to (re)start the backend.
  ipcMain.handle("start-backend", async () => {
    backendAttempts = 0;
    startBackend();
    return { ok: true, message: "Starting…" };
  });

  startBackend();
  startFrontend();

  try {
    await waitFor(`http://localhost:${FRONTEND_PORT}`);
    createWindow();
  } catch (err) {
    console.error("Couldn't start the frontend:", err.message);
    app.quit();
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", shutdown);
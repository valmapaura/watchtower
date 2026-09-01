// Preload script — exposes a minimal, safe API to the renderer.
// Provides native actions like "start the backend" that the web UI can call
// when it detects the service is down.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("watchtower", {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  // Ask the main process to (re)start the backend. Returns a message.
  startBackend: () => ipcRenderer.invoke("start-backend"),
  // Listen for backend status updates from the main process.
  onBackendStatus: (callback) => {
    const listener = (_event, data) => callback(data);
    ipcRenderer.on("backend-status", listener);
    return () => ipcRenderer.removeListener("backend-status", listener);
  },
  // Whether this is running inside the desktop app (vs a browser).
  isDesktop: true,
});
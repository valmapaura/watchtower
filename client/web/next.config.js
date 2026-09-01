/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so the desktop app can serve the UI without a Node server.
  output: "export",
  // The UI is served by Electron from a file:// or local server; disable
  // image optimization (needs a server) and use unoptimized images.
  images: { unoptimized: true },
  // Trailing slash keeps relative asset paths working under file://.
  trailingSlash: true,
};

module.exports = nextConfig;

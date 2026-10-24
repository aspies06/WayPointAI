// Where api.py is running. Override without editing code:
//   - at build time: VITE_API_BASE=http://127.0.0.1:9000 npm run build
//   - in the browser: add ?api=http://127.0.0.1:9000 to the page address
// The browser override only accepts this computer's own addresses, so a shared link can't
// send someone's stories to another server.
const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);

function localOverride(value) {
  try {
    const url = new URL(value);
    return /^https?:$/.test(url.protocol) && LOOPBACK.has(url.hostname) ? url.origin : "";
  } catch {
    return "";
  }
}

export const API_BASE =
  localOverride(new URLSearchParams(window.location.search).get("api") || "") ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000";

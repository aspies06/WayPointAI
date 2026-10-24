// Where api.py is running. Override without editing code:
//   - at build time: VITE_API_BASE=http://127.0.0.1:9000 npm run build
//   - in the browser: add ?api=http://127.0.0.1:9000 to the page address
export const API_BASE =
  new URLSearchParams(window.location.search).get("api") ||
  import.meta.env.VITE_API_BASE ||
  "http://127.0.0.1:8000";

// Where api.py is running. Override without editing code: index.html?api=http://127.0.0.1:9000
export const API_BASE =
  new URLSearchParams(window.location.search).get("api") || "http://127.0.0.1:8000";

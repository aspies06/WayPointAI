import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// npm run dev     -> http://127.0.0.1:5173 (instant reload as you edit)
// npm run build   -> dist/ (optimized static files; VS Code Live Server can serve these too)
// npm run preview -> http://127.0.0.1:4173 (try the built site)
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true },
});

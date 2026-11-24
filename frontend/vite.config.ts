import { defineConfig } from 'vite';

// Development only. In normal use FastAPI (port 8000) serves both the API and the
// built frontend (frontend/dist), so relative /api requests are same-origin.
// When running `npm run dev` (Vite on port 5173), this proxy forwards those same
// relative /api requests to FastAPI, so application code never needs absolute URLs.
// `server` settings have no effect on `npm run build`.
export default defineConfig({
  server: {
    proxy: {
      // 127.0.0.1 rather than localhost: Node may resolve localhost to IPv6 (::1),
      // while uvicorn is started on IPv4 127.0.0.1.
      '/api': 'http://127.0.0.1:8000',
    },
  },
});

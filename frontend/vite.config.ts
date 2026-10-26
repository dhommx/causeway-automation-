import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // AG Grid is large; keep it in its own cached chunk. Internal app on a local network.
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: { manualChunks: { aggrid: ["ag-grid-community", "ag-grid-react"] } },
    },
  },
  server: {
    port: 3500,
    strictPort: true,
    proxy: { "/api": "http://localhost:4500" },
  },
});

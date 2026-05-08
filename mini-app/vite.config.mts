import { defineConfig, Plugin } from "vite";
import zaloMiniApp from "zmp-vite-plugin";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * SPA Fallback — Internal URL rewrite for Vite dev server
 * 
 * With root: "./src", Vite serves index.html at /src/index.html.
 * But ZMP wrapper iframe loads localhost:2999/ → 404.
 * 
 * This plugin rewrites / → /src/index.html server-side only.
 * Browser's window.location stays at "/" so React Router works correctly.
 */
function spaFallback(): Plugin {
  return {
    name: "spa-fallback",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url || "/";
        const skip =
          /\.\w+(\?.*)?$/.test(url) ||
          url.startsWith("/@") ||
          url.startsWith("/node_modules") ||
          url.startsWith("/src/") ||
          url.includes("__vite");
        if (!skip) {
          req.url = "/src/index.html";
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default () => {
  return defineConfig({
    root: "./src",
    base: "",
    plugins: [
      spaFallback(), // MUST be first
      zaloMiniApp(),
      react(),
    ],
    build: {
      assetsInlineLimit: 0,
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
  });
};

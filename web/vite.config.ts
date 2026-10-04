/// <reference types="vitest/config" />
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

import { resolve } from "node:path";

// Comma-separated hostnames the dev server answers to besides localhost and
// bare IPs, e.g. VITE_ALLOWED_HOSTS=app.example.com,dev.example.com. Set it in
// the repo-root .env (docker-compose passes it to web-frontend) or web/.env.local.
function parseAllowedHosts(value: string | undefined): string[] {
	return (value ?? "")
		.split(",")
		.map((host) => host.trim())
		.filter(Boolean);
}

export default defineConfig(({ mode }) => ({
	plugins: [TanStackRouterVite(), viteReact(), tailwindcss()],
	build: {
		chunkSizeWarningLimit: 1024,
	},
	server: {
		host: "0.0.0.0",
		port: 3000,
		// Vite 5.4.12+/6+/7 reject requests whose Host header is not listed here
		// (localhost / bare IPs are always allowed). Needed to serve the dev
		// server through a reverse proxy on your own hostname.
		allowedHosts: parseAllowedHosts(
			loadEnv(mode, __dirname, "VITE_").VITE_ALLOWED_HOSTS,
		),
		watch: {
			usePolling: true,
		},
		proxy: {
			"/api": {
				target: process.env.VITE_API_URL || "http://web:8000",
				changeOrigin: true,
				secure: false,
			},
		},
	},
	test: {
		globals: true,
		environment: "jsdom",
		setupFiles: "src/test-utils/setup-tests.ts",
	},
	resolve: {
		alias: {
			"@": resolve(__dirname, "./src"),
			"@/features": resolve(__dirname, "./src/features"),
			"@/components": resolve(__dirname, "./src/components"),
			"@/lib": resolve(__dirname, "./src/lib"),
			"@/integrations": resolve(__dirname, "./src/integrations"),
			"@/i18n": resolve(__dirname, "./src/i18n"),
		},
	},
}));

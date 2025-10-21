/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

import { resolve } from "node:path";

export default defineConfig({
	plugins: [TanStackRouterVite(), viteReact(), tailwindcss()],
	build: {
		chunkSizeWarningLimit: 1024,
	},
	server: {
		host: "0.0.0.0",
		port: 3000,
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
});

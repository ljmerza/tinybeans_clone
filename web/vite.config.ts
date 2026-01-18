/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");

	const devServerHost = env.VITE_DEV_SERVER_HOST || "0.0.0.0";

	const parsedPort = Number(env.VITE_DEV_SERVER_PORT);
	const devServerPort = Number.isFinite(parsedPort) ? parsedPort : 3000;

	const devProxyTarget =
		env.VITE_DEV_PROXY_TARGET || env.VITE_BACKEND_URL || "http://web:8000";

	return {
		plugins: [TanStackRouterVite(), viteReact(), tailwindcss()],
		build: {
			chunkSizeWarningLimit: 1024,
		},
		server: {
			host: devServerHost,
			port: devServerPort,
			watch: {
				usePolling: true,
			},
			proxy: {
				"/api": {
					target: devProxyTarget,
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
	};
});

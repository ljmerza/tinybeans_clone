#!/usr/bin/env node

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const ROOT = new URL("..", import.meta.url).pathname;
const SRC_DIR = path.join(ROOT, "src");

const ALLOWLIST = [
	"src/lib/api/client.ts",
	"src/lib/httpClient.ts",
	"src/lib/csrf.ts",
	"src/features/auth/utils/refreshToken.ts",
	"src/features/twofa/api/services.ts",
];

async function collectFiles(dir) {
	const entries = await readdir(dir, { withFileTypes: true });
	const files = [];

	for (const entry of entries) {
		const fullPath = path.join(dir, entry.name);

		if (entry.isDirectory()) {
			files.push(...(await collectFiles(fullPath)));
		} else if (
			entry.isFile() &&
			(entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
		) {
			files.push(fullPath);
		}
	}

	return files;
}

function isAllowed(filePath) {
	const relative = path.relative(ROOT, filePath).replace(/\\/g, "/");
	return ALLOWLIST.some((allowed) => relative === allowed);
}

function containsFetch(source) {
	return /\bfetch\s*\(/.test(source);
}

async function main() {
	const files = await collectFiles(SRC_DIR);
	const violations = [];

	for (const file of files) {
		if (isAllowed(file)) continue;

		const content = await readFile(file, "utf8");
		if (containsFetch(content)) {
			const relative = path.relative(ROOT, file).replace(/\\/g, "/");
			violations.push(relative);
		}
	}

	if (violations.length) {
		console.error(
			[
				"Raw fetch usage detected outside approved modules:",
				...violations.map((file) => `  - ${file}`),
				"",
				"Move network calls into shared service modules.",
			].join("\n"),
		);
		process.exit(1);
	}
}

main().catch((error) => {
	console.error("Failed to run raw fetch guard:", error);
	process.exit(1);
});

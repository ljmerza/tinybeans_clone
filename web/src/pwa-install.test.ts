/**
 * Guards the "Add to Home Screen" / "Install app" setup: the manifest fields
 * Chrome requires for installability, icons that really exist at their declared
 * sizes, and the iOS tags in index.html.
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const webRoot = resolve(__dirname, "..");
const publicDir = resolve(webRoot, "public");

interface ManifestIcon {
	src: string;
	sizes: string;
	type: string;
	purpose?: string;
}

const manifest = JSON.parse(
	readFileSync(resolve(publicDir, "manifest.json"), "utf8"),
) as Record<string, unknown> & { icons: ManifestIcon[] };
const indexHtml = readFileSync(resolve(webRoot, "index.html"), "utf8");

/** Reads width/height/color type from a PNG's IHDR chunk. */
const readPng = (publicPath: string) => {
	const bytes = readFileSync(`${publicDir}${publicPath}`);
	expect(bytes.subarray(1, 4).toString("latin1")).toBe("PNG");
	return {
		width: bytes.readUInt32BE(16),
		height: bytes.readUInt32BE(20),
		hasAlpha: bytes[25] === 4 || bytes[25] === 6,
	};
};

const pngIcons = manifest.icons.filter((icon) => icon.type === "image/png");

describe("web app manifest", () => {
	it("has the fields Chrome needs to offer install", () => {
		expect(manifest.name).toBe("Circles");
		expect(manifest.short_name).toBe("Circles");
		expect(manifest.start_url).toBe("/");
		expect(manifest.scope).toBe("/");
		expect(manifest.display).toBe("standalone");
		expect(manifest.prefer_related_applications).toBeUndefined();
		expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i);
		expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i);
	});

	it("declares 192px, 512px and maskable icons", () => {
		const anySizes = pngIcons
			.filter((icon) => (icon.purpose ?? "any").split(" ").includes("any"))
			.map((icon) => icon.sizes);
		expect(anySizes).toEqual(expect.arrayContaining(["192x192", "512x512"]));
		expect(pngIcons.some((icon) => icon.purpose === "maskable")).toBe(true);
	});

	it.each(manifest.icons.map((icon) => [icon.src, icon] as const))(
		"icon %s exists in public/ at its declared size",
		(src, icon) => {
			expect(existsSync(`${publicDir}${src}`)).toBe(true);
			if (icon.type !== "image/png") return;
			const [width, height] = icon.sizes.split("x").map(Number);
			expect(readPng(src)).toMatchObject({ width, height });
		},
	);
});

describe("index.html install tags", () => {
	it("links the manifest", () => {
		expect(indexHtml).toContain(
			'<link rel="manifest" href="/manifest.json" />',
		);
	});

	it("has an opaque 180px apple-touch-icon", () => {
		const href = indexHtml.match(
			/<link rel="apple-touch-icon" href="([^"]+)"/,
		)?.[1];
		expect(href).toBeDefined();
		// iOS renders transparent pixels black, so the icon must be opaque.
		expect(readPng(href as string)).toEqual({
			width: 180,
			height: 180,
			hasAlpha: false,
		});
	});

	it("names the iOS home-screen app like the manifest", () => {
		expect(indexHtml).toContain(
			`<meta name="apple-mobile-web-app-title" content="${manifest.short_name}" />`,
		);
		expect(indexHtml).toContain(
			'<meta name="apple-mobile-web-app-capable" content="yes" />',
		);
	});
});

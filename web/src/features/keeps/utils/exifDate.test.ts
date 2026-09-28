import { describe, expect, it } from "vitest";

import { readExifDate } from "./exifDate";

const TYPE_ASCII = 2;
const TYPE_LONG = 4;

interface Options {
	little?: boolean;
	/** Where the date lives: the Exif IFD's DateTimeOriginal or IFD0's DateTime. */
	tag?: "original" | "ifd0";
	date?: string;
}

/** A minimal JPEG: SOI, a JFIF APP0 to skip, an EXIF APP1, then SOS. */
function jpegWithExif({
	little = false,
	tag = "original",
	date = "2024:03:05 14:22:10",
}: Options = {}) {
	const tiff = new DataView(new ArrayBuffer(64));
	const u16 = (at: number, value: number) => tiff.setUint16(at, value, little);
	const u32 = (at: number, value: number) => tiff.setUint32(at, value, little);
	tiff.setUint16(0, little ? 0x4949 : 0x4d4d);
	u16(2, 42);
	u32(4, 8); // IFD0 right after the header
	// IFD0 (8..26): one entry, then the next-IFD pointer.
	u16(8, 1);
	if (tag === "original") {
		u16(10, 0x8769); // Exif IFD pointer
		u16(12, TYPE_LONG);
		u32(14, 1);
		u32(18, 26);
		// Exif IFD (26..44): DateTimeOriginal.
		u16(26, 1);
		u16(28, 0x9003);
		u16(30, TYPE_ASCII);
		u32(32, 20);
		u32(36, 44);
	} else {
		u16(10, 0x0132); // DateTime
		u16(12, TYPE_ASCII);
		u32(14, 20);
		u32(18, 44);
	}
	for (let i = 0; i < date.length; i++) {
		tiff.setUint8(44 + i, date.charCodeAt(i));
	}

	const app0 = [0xff, 0xe0, 0x00, 0x10, ...new Array(14).fill(0)];
	const app1Length = 2 + 6 + tiff.byteLength;
	const app1 = [
		0xff,
		0xe1,
		app1Length >> 8,
		app1Length & 0xff,
		...[0x45, 0x78, 0x69, 0x66, 0, 0], // "Exif\0\0"
		...new Uint8Array(tiff.buffer),
	];
	const bytes = [0xff, 0xd8, ...app0, ...app1, 0xff, 0xda, 0x00, 0x02];
	return new File([new Uint8Array(bytes)], "photo.jpg", {
		type: "image/jpeg",
	});
}

describe("readExifDate", () => {
	it("reads DateTimeOriginal in big-endian EXIF", async () => {
		expect(await readExifDate(jpegWithExif())).toBe("2024-03-05");
	});

	it("reads little-endian EXIF", async () => {
		expect(await readExifDate(jpegWithExif({ little: true }))).toBe(
			"2024-03-05",
		);
	});

	it("falls back to IFD0's DateTime", async () => {
		expect(
			await readExifDate(
				jpegWithExif({ tag: "ifd0", date: "2023:12:31 23:59:59" }),
			),
		).toBe("2023-12-31");
	});

	it("ignores a camera clock that was never set", async () => {
		expect(
			await readExifDate(jpegWithExif({ date: "0000:00:00 00:00:00" })),
		).toBeNull();
	});

	it("returns null without EXIF or for non-JPEGs", async () => {
		const bare = new File(
			[new Uint8Array([0xff, 0xd8, 0xff, 0xda, 0, 2])],
			"a.jpg",
		);
		const png = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "a.png");
		expect(await readExifDate(bare)).toBeNull();
		expect(await readExifDate(png)).toBeNull();
		expect(await readExifDate(new File([], "empty.jpg"))).toBeNull();
	});
});

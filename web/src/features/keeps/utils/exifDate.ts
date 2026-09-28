/**
 * The day a photo was taken, from its EXIF data.
 *
 * Reads only JPEG, which is what phones hand the browser (HEIC isn't
 * accepted). EXIF lives in an APP1 segment near the start of the file, so
 * only the first chunk is read, never the whole photo.
 */

/** APP1 segments are at most 64 KB; this leaves room for any ahead of it. */
const HEAD_BYTES = 256 * 1024;

const TAG_EXIF_IFD = 0x8769;
const TAG_DATE_TIME = 0x0132;
const TAG_DATE_TIME_ORIGINAL = 0x9003;
const TAG_DATE_TIME_DIGITIZED = 0x9004;
const TYPE_ASCII = 2;
const IFD_ENTRY_BYTES = 12;

function readHead(file: Blob): Promise<ArrayBuffer> {
	const head = file.slice(0, HEAD_BYTES);
	if (typeof head.arrayBuffer === "function") return head.arrayBuffer();
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as ArrayBuffer);
		reader.onerror = () => reject(reader.error);
		reader.readAsArrayBuffer(head);
	});
}

/** Offset of the TIFF header inside the EXIF APP1 segment, or null. */
function findTiffHeader(view: DataView): number | null {
	if (view.byteLength < 4 || view.getUint16(0) !== 0xffd8) return null;
	let offset = 2;
	while (offset + 4 <= view.byteLength) {
		if (view.getUint8(offset) !== 0xff) return null;
		const marker = view.getUint8(offset + 1);
		// Start of scan: image data follows, no more metadata.
		if (marker === 0xda) return null;
		const length = view.getUint16(offset + 2);
		const isExif =
			marker === 0xe1 &&
			offset + 10 <= view.byteLength &&
			view.getUint32(offset + 4) === 0x45786966 && // "Exif"
			view.getUint16(offset + 8) === 0;
		if (isExif) return offset + 10;
		offset += 2 + length;
	}
	return null;
}

interface IfdEntry {
	type: number;
	count: number;
	/** The value itself for small values, else its offset from the TIFF header. */
	valueOffset: number;
}

function readIfd(
	view: DataView,
	tiff: number,
	ifdOffset: number,
	little: boolean,
): Map<number, IfdEntry> {
	const entries = new Map<number, IfdEntry>();
	const start = tiff + ifdOffset;
	if (start + 2 > view.byteLength) return entries;
	const count = view.getUint16(start, little);
	for (let i = 0; i < count; i++) {
		const entry = start + 2 + i * IFD_ENTRY_BYTES;
		if (entry + IFD_ENTRY_BYTES > view.byteLength) break;
		entries.set(view.getUint16(entry, little), {
			type: view.getUint16(entry + 2, little),
			count: view.getUint32(entry + 4, little),
			valueOffset: view.getUint32(entry + 8, little),
		});
	}
	return entries;
}

/** `YYYY-MM-DD` from an EXIF `YYYY:MM:DD HH:MM:SS` string entry, or null. */
function readDate(
	view: DataView,
	tiff: number,
	entry: IfdEntry | undefined,
): string | null {
	// The 19-character timestamp never fits inline, so it's always at an offset.
	if (!entry || entry.type !== TYPE_ASCII || entry.count < 10) return null;
	const start = tiff + entry.valueOffset;
	if (start + 10 > view.byteLength) return null;
	let text = "";
	for (let i = 0; i < 10; i++)
		text += String.fromCharCode(view.getUint8(start + i));
	const match = /^(\d{4}):(\d{2}):(\d{2})$/.exec(text);
	if (!match) return null;
	const [, year, month, day] = match;
	// Cameras without a set clock write zeros.
	if (Number(year) < 1900 || month === "00" || day === "00") return null;
	return `${year}-${month}-${day}`;
}

function parseExifDate(buffer: ArrayBuffer): string | null {
	const view = new DataView(buffer);
	const tiff = findTiffHeader(view);
	if (tiff === null || tiff + 8 > view.byteLength) return null;
	const order = view.getUint16(tiff);
	if (order !== 0x4949 && order !== 0x4d4d) return null; // "II" / "MM"
	const little = order === 0x4949;
	if (view.getUint16(tiff + 2, little) !== 42) return null;

	const ifd0 = readIfd(view, tiff, view.getUint32(tiff + 4, little), little);
	const exifPointer = ifd0.get(TAG_EXIF_IFD);
	const exif = exifPointer
		? readIfd(view, tiff, exifPointer.valueOffset, little)
		: new Map<number, IfdEntry>();

	// When the shutter fired, then when it was digitized, then last edited.
	return (
		readDate(view, tiff, exif.get(TAG_DATE_TIME_ORIGINAL)) ??
		readDate(view, tiff, exif.get(TAG_DATE_TIME_DIGITIZED)) ??
		readDate(view, tiff, ifd0.get(TAG_DATE_TIME))
	);
}

/**
 * `YYYY-MM-DD` the photo was taken, as the camera recorded it (its local
 * day), or null when the file has no usable EXIF date.
 */
export async function readExifDate(file: Blob): Promise<string | null> {
	try {
		return parseExifDate(await readHead(file));
	} catch {
		return null;
	}
}

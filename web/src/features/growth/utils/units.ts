/**
 * Growth measurements are stored metric (cm to 0.1, kg to the gram) and shown
 * in the viewer's units. Imperial shows ft/in to 0.1 in and lb/oz to 0.1 oz.
 *
 * The stored precision is finer than the imperial display, so a value typed in
 * imperial converts to metric and back to exactly what was typed: 0.05 cm is
 * 0.02 in and 0.5 g is 0.018 oz, both under half a display step. The edit form
 * relies on that, and also leaves untouched fields alone, so editing a
 * measurement never drifts its other value.
 */

export type MeasurementUnits = "imperial" | "metric";

export const DEFAULT_MEASUREMENT_UNITS: MeasurementUnits = "imperial";

/** Exact by definition. */
export const CM_PER_INCH = 2.54;
export const KG_PER_POUND = 0.45359237;
export const INCHES_PER_FOOT = 12;
export const OUNCES_PER_POUND = 16;

export function toMeasurementUnits(value: unknown): MeasurementUnits {
	return value === "metric" ? "metric" : DEFAULT_MEASUREMENT_UNITS;
}

/** Rounds to the stored precision: 0.1 cm. */
export function roundCm(cm: number) {
	return Math.round(cm * 10) / 10;
}

/** Rounds to the stored precision: 1 g. */
export function roundKg(kg: number) {
	return Math.round(kg * 1000) / 1000;
}

export function feetInchesToCm(feet: number, inches: number) {
	return roundCm((feet * INCHES_PER_FOOT + inches) * CM_PER_INCH);
}

export function poundsOuncesToKg(pounds: number, ounces: number) {
	return roundKg(
		((pounds * OUNCES_PER_POUND + ounces) / OUNCES_PER_POUND) * KG_PER_POUND,
	);
}

/**
 * Feet and inches, inches to 0.1. Rounded in whole tenths first, so 11.96 in
 * becomes 1 ft 0 in rather than 0 ft 12 in.
 */
export function cmToFeetInches(cm: number) {
	const tenths = Math.round((cm / CM_PER_INCH) * 10);
	const tenthsPerFoot = INCHES_PER_FOOT * 10;
	return {
		feet: Math.floor(tenths / tenthsPerFoot),
		inches: (tenths % tenthsPerFoot) / 10,
	};
}

/** Pounds and ounces, ounces to 0.1, carried like `cmToFeetInches`. */
export function kgToPoundsOunces(kg: number) {
	const tenths = Math.round((kg / KG_PER_POUND) * OUNCES_PER_POUND * 10);
	const tenthsPerPound = OUNCES_PER_POUND * 10;
	return {
		pounds: Math.floor(tenths / tenthsPerPound),
		ounces: (tenths % tenthsPerPound) / 10,
	};
}

/** Total inches to 0.1, for chart values. */
export function cmToInches(cm: number) {
	return Math.round((cm / CM_PER_INCH) * 10) / 10;
}

/** Total pounds to 0.01, for chart values. */
export function kgToPounds(kg: number) {
	return Math.round((kg / KG_PER_POUND) * 100) / 100;
}

function formatNumber(value: number, maxDigits: number, locale?: string) {
	return value.toLocaleString(locale, { maximumFractionDigits: maxDigits });
}

/** E.g. "2 ft 9.5 in", "11 in" or "84.5 cm". */
export function formatHeight(
	cm: number,
	units: MeasurementUnits,
	locale?: string,
) {
	if (units === "metric") return `${formatNumber(cm, 1, locale)} cm`;
	const { feet, inches } = cmToFeetInches(cm);
	const inchesText = `${formatNumber(inches, 1, locale)} in`;
	return feet > 0 ? `${feet} ft ${inchesText}` : inchesText;
}

/** E.g. "13 lb 13 oz", "12.5 oz" or "6.265 kg". */
export function formatWeight(
	kg: number,
	units: MeasurementUnits,
	locale?: string,
) {
	if (units === "metric") return `${formatNumber(kg, 3, locale)} kg`;
	const { pounds, ounces } = kgToPoundsOunces(kg);
	const ouncesText = `${formatNumber(ounces, 1, locale)} oz`;
	return pounds > 0 ? `${pounds} lb ${ouncesText}` : ouncesText;
}

/** A chart axis/tooltip value: "33.5 in", "21.75 lb", "85 cm", "9.87 kg". */
export function formatChartValue(
	value: number,
	unit: "in" | "lb" | "cm" | "kg",
	locale?: string,
) {
	const digits = unit === "lb" || unit === "kg" ? 2 : 1;
	return `${formatNumber(value, digits, locale)} ${unit}`;
}

/**
 * Form fields for one height or weight, as typed. Imperial uses both fields
 * (ft + in, lb + oz); metric only `major` (cm, kg).
 */
export interface QuantityFields {
	major: string;
	minor: string;
}

const EMPTY_FIELDS: QuantityFields = { major: "", minor: "" };

/** Plain digits for an input's value: no grouping, "." decimals. */
function fieldNumber(value: number) {
	return String(value);
}

export function heightToFields(
	cm: number | null,
	units: MeasurementUnits,
): QuantityFields {
	if (cm === null) return EMPTY_FIELDS;
	if (units === "metric") return { major: fieldNumber(cm), minor: "" };
	const { feet, inches } = cmToFeetInches(cm);
	return { major: fieldNumber(feet), minor: fieldNumber(inches) };
}

export function weightToFields(
	kg: number | null,
	units: MeasurementUnits,
): QuantityFields {
	if (kg === null) return EMPTY_FIELDS;
	if (units === "metric") return { major: fieldNumber(kg), minor: "" };
	const { pounds, ounces } = kgToPoundsOunces(kg);
	return { major: fieldNumber(pounds), minor: fieldNumber(ounces) };
}

/**
 * Parses a typed number; accepts "," as the decimal mark. Blank is null,
 * anything else unreadable or negative is NaN.
 */
export function parseField(text: string): number | null {
	const trimmed = text.trim().replace(",", ".");
	if (trimmed === "") return null;
	if (!/^\d*\.?\d*$/.test(trimmed) || trimmed === ".") return Number.NaN;
	return Number(trimmed);
}

/**
 * The stored value for the typed fields: null when both are blank, NaN when
 * either can't be read, else cm/kg rounded to the stored precision.
 */
export function fieldsToHeightCm(
	fields: QuantityFields,
	units: MeasurementUnits,
): number | null {
	const major = parseField(fields.major);
	if (units === "metric") {
		return major === null || Number.isNaN(major) ? major : roundCm(major);
	}
	const minor = parseField(fields.minor);
	if (major === null && minor === null) return null;
	if (Number.isNaN(major) || Number.isNaN(minor)) return Number.NaN;
	return feetInchesToCm(major ?? 0, minor ?? 0);
}

export function fieldsToWeightKg(
	fields: QuantityFields,
	units: MeasurementUnits,
): number | null {
	const major = parseField(fields.major);
	if (units === "metric") {
		return major === null || Number.isNaN(major) ? major : roundKg(major);
	}
	const minor = parseField(fields.minor);
	if (major === null && minor === null) return null;
	if (Number.isNaN(major) || Number.isNaN(minor)) return Number.NaN;
	return poundsOuncesToKg(major ?? 0, minor ?? 0);
}

export function sameFields(a: QuantityFields, b: QuantityFields) {
	return a.major.trim() === b.major.trim() && a.minor.trim() === b.minor.trim();
}

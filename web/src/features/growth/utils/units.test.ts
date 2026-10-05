import { describe, expect, it } from "vitest";
import {
	cmToFeetInches,
	feetInchesToCm,
	fieldsToHeightCm,
	fieldsToWeightKg,
	formatChartValue,
	formatHeight,
	formatWeight,
	heightToFields,
	kgToPoundsOunces,
	parseField,
	poundsOuncesToKg,
	toMeasurementUnits,
	weightToFields,
} from "./units";

describe("conversions", () => {
	it("converts imperial to metric at the stored precision", () => {
		expect(feetInchesToCm(1, 8)).toBe(50.8);
		expect(feetInchesToCm(0, 20.25)).toBe(51.4);
		expect(poundsOuncesToKg(7, 8)).toBe(3.402);
		expect(poundsOuncesToKg(1, 0)).toBe(0.454);
		expect(poundsOuncesToKg(13, 13)).toBe(6.265);
	});

	it("converts metric to feet/inches and pounds/ounces", () => {
		expect(cmToFeetInches(50.8)).toEqual({ feet: 1, inches: 8 });
		expect(cmToFeetInches(84.5)).toEqual({ feet: 2, inches: 9.3 });
		expect(kgToPoundsOunces(3.402)).toEqual({ pounds: 7, ounces: 8 });
		expect(kgToPoundsOunces(6.265)).toEqual({ pounds: 13, ounces: 13 });
	});

	it("carries a rounded-up 12 in or 16 oz into the next foot or pound", () => {
		// 11.98 in and 15.98 oz round to 12.0 and 16.0.
		expect(cmToFeetInches(30.43)).toEqual({ feet: 1, inches: 0 });
		expect(kgToPoundsOunces(0.9067)).toEqual({ pounds: 2, ounces: 0 });
	});

	it("reads back every imperial value exactly as typed (no drift)", () => {
		for (let tenths = 0; tenths < 160 * 60; tenths += 7) {
			const pounds = Math.floor(tenths / 160);
			const ounces = (tenths % 160) / 10;
			expect(kgToPoundsOunces(poundsOuncesToKg(pounds, ounces))).toEqual({
				pounds,
				ounces,
			});
		}
		for (let tenths = 0; tenths < 120 * 7; tenths += 3) {
			const feet = Math.floor(tenths / 120);
			const inches = (tenths % 120) / 10;
			expect(cmToFeetInches(feetInchesToCm(feet, inches))).toEqual({
				feet,
				inches,
			});
		}
	});

	it("survives repeated edits without creeping", () => {
		let kg = 6.265;
		let cm = 84.5;
		for (let i = 0; i < 20; i++) {
			kg = fieldsToWeightKg(
				weightToFields(kg, "imperial"),
				"imperial",
			) as number;
			cm = fieldsToHeightCm(
				heightToFields(cm, "imperial"),
				"imperial",
			) as number;
		}
		expect(kg).toBe(6.265);
		expect(cm).toBe(84.6);
		// The first trip snaps to the 0.1 in grid; after that it is stable.
		expect(fieldsToHeightCm(heightToFields(84.6, "imperial"), "imperial")).toBe(
			84.6,
		);
	});
});

describe("formatting", () => {
	it("shows imperial by default units", () => {
		expect(formatHeight(84.5, "imperial", "en")).toBe("2 ft 9.3 in");
		expect(formatHeight(27.9, "imperial", "en")).toBe("11 in");
		expect(formatWeight(6.265, "imperial", "en")).toBe("13 lb 13 oz");
		expect(formatWeight(3.4, "imperial", "en")).toBe("7 lb 7.9 oz");
		expect(formatWeight(0.35, "imperial", "en")).toBe("12.3 oz");
	});

	it("shows metric trimmed to the stored precision", () => {
		expect(formatHeight(84.5, "metric", "en")).toBe("84.5 cm");
		expect(formatHeight(84, "metric", "en")).toBe("84 cm");
		expect(formatWeight(6.265, "metric", "en")).toBe("6.265 kg");
		expect(formatWeight(6.25, "metric", "en")).toBe("6.25 kg");
	});

	it("uses the locale's decimal mark", () => {
		expect(formatHeight(84.5, "metric", "it")).toBe("84,5 cm");
		expect(formatWeight(3.4, "imperial", "es")).toBe("7 lb 7,9 oz");
	});

	it("formats chart values", () => {
		expect(formatChartValue(33.25, "in", "en")).toBe("33.3 in");
		expect(formatChartValue(21.754, "lb", "en")).toBe("21.75 lb");
	});

	it("falls back to imperial for unknown preferences", () => {
		expect(toMeasurementUnits("metric")).toBe("metric");
		expect(toMeasurementUnits(undefined)).toBe("imperial");
		expect(toMeasurementUnits("furlongs")).toBe("imperial");
	});
});

describe("form fields", () => {
	it("parses typed numbers", () => {
		expect(parseField("")).toBeNull();
		expect(parseField(" 8.5 ")).toBe(8.5);
		expect(parseField("8,5")).toBe(8.5);
		expect(parseField("abc")).toBeNaN();
		expect(parseField("-2")).toBeNaN();
	});

	it("fills and reads imperial fields", () => {
		expect(weightToFields(3.402, "imperial")).toEqual({
			major: "7",
			minor: "8",
		});
		expect(heightToFields(null, "imperial")).toEqual({ major: "", minor: "" });
		expect(fieldsToWeightKg({ major: "7", minor: "" }, "imperial")).toBe(3.175);
		expect(fieldsToWeightKg({ major: "", minor: "12" }, "imperial")).toBe(0.34);
		expect(fieldsToHeightCm({ major: "", minor: "" }, "imperial")).toBeNull();
		expect(fieldsToHeightCm({ major: "2", minor: "x" }, "imperial")).toBeNaN();
	});

	it("fills and reads metric fields", () => {
		expect(heightToFields(61.5, "metric")).toEqual({
			major: "61.5",
			minor: "",
		});
		expect(fieldsToHeightCm({ major: "61.54", minor: "" }, "metric")).toBe(
			61.5,
		);
		expect(fieldsToWeightKg({ major: "6,2654", minor: "" }, "metric")).toBe(
			6.265,
		);
	});
});

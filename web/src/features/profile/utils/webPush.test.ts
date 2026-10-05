import { afterEach, describe, expect, it, vi } from "vitest";
import { getPushSupport, vapidKeyToBytes } from "./webPush";

const IPHONE_SAFARI =
	"Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";

afterEach(() => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	Reflect.deleteProperty(navigator, "serviceWorker");
});

function withPushApis() {
	vi.stubGlobal("PushManager", function PushManager() {});
	vi.stubGlobal("Notification", { permission: "default" });
	Object.defineProperty(navigator, "serviceWorker", {
		configurable: true,
		value: {},
	});
}

describe("vapidKeyToBytes", () => {
	it("decodes unpadded base64url", () => {
		// "-_8" is 0xfb 0xff in base64url (would be "+/8=" in base64).
		expect(Array.from(vapidKeyToBytes("-_8"))).toEqual([0xfb, 0xff]);
		expect(Array.from(vapidKeyToBytes("BBBB"))).toEqual([4, 16, 65]);
	});
});

describe("getPushSupport", () => {
	it("is supported on a secure page with push APIs", () => {
		withPushApis();
		vi.stubGlobal("isSecureContext", true);

		expect(getPushSupport()).toBe("supported");
	});

	it("is unsupported on an insecure page even with push APIs", () => {
		withPushApis();
		vi.stubGlobal("isSecureContext", false);

		expect(getPushSupport()).toBe("unsupported");
	});

	it("asks iPhone Safari users to install the app first", () => {
		vi.spyOn(navigator, "userAgent", "get").mockReturnValue(IPHONE_SAFARI);

		expect(getPushSupport()).toBe("install-required");
	});

	it("is unsupported in an installed iPhone app on an iOS without push", () => {
		vi.spyOn(navigator, "userAgent", "get").mockReturnValue(IPHONE_SAFARI);
		vi.stubGlobal("matchMedia", (query: string) => ({
			matches: query === "(display-mode: standalone)",
		}));

		expect(getPushSupport()).toBe("unsupported");
	});
});

import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The loading state renders Layout, which needs the auth session.
vi.mock("@/components/Layout", () => ({
	Layout: { Loading: ({ message }: { message?: string }) => <p>{message}</p> },
}));

import { circleServices } from "@/features/circles/api/services";
import type { CircleMembershipSummary } from "@/features/circles/types";
import {
	type NotificationChannels,
	type NotificationPreferences,
	profileServices,
} from "../api/services";
import { ProfileNotificationSettingsCard } from "./ProfileNotificationSettingsCard";

const preferences = (
	overrides: Partial<NotificationPreferences> = {},
): NotificationPreferences => ({
	notify_new_media: true,
	notify_comments: true,
	notify_replies: true,
	notify_likes: true,
	email_enabled: true,
	sms_enabled: false,
	push_enabled: false,
	email_digest: false,
	circle_id: null,
	per_circle_override: false,
	...overrides,
});

const channels = (
	overrides: Partial<NotificationChannels> = {},
): NotificationChannels => ({
	sms_available: false,
	phone_number: null,
	phone_verified: false,
	phone_verification_pending: false,
	push_available: false,
	vapid_public_key: "",
	push_device_count: 0,
	...overrides,
});

const membership = {
	membership_id: 1,
	circle: { id: 7, name: "Smith Family", slug: "smith-family" },
	role: "member",
	is_owner: false,
	created_at: "2026-09-01T00:00:00Z",
} as CircleMembershipSummary;

// "BBBB" in base64url: a stand-in VAPID key.
const VAPID_KEY = "BBBB";

function mockPreferences(overrides: Partial<NotificationPreferences> = {}) {
	vi.spyOn(profileServices, "getNotificationPreferences").mockImplementation(
		async (circleId) => ({
			data:
				circleId === 7
					? preferences({ circle_id: 7, ...overrides })
					: preferences(overrides),
		}),
	);
}

function mockChannels(overrides: Partial<NotificationChannels> = {}) {
	vi.spyOn(profileServices, "getNotificationChannels").mockResolvedValue({
		data: channels(overrides),
	});
}

/** A browser with service workers and push, like Chrome on Android. */
function installPushBrowser(permission: NotificationPermission = "granted") {
	const subscription = {
		endpoint: "https://fcm.googleapis.com/fcm/send/device-1",
		options: { applicationServerKey: null },
		toJSON: () => ({
			endpoint: "https://fcm.googleapis.com/fcm/send/device-1",
			keys: { p256dh: "device-key", auth: "device-auth" },
		}),
		unsubscribe: vi.fn().mockResolvedValue(true),
	};
	const pushManager = {
		getSubscription: vi.fn().mockResolvedValue(null),
		subscribe: vi.fn().mockResolvedValue(subscription),
	};
	const registration = { pushManager };
	const serviceWorker = {
		register: vi.fn().mockResolvedValue(registration),
		ready: Promise.resolve(registration),
		getRegistration: vi.fn().mockResolvedValue(undefined),
	};
	const NotificationStub = {
		permission: "default" as NotificationPermission,
		requestPermission: vi.fn(async () => {
			NotificationStub.permission = permission;
			return permission;
		}),
	};
	vi.stubGlobal("PushManager", function PushManager() {});
	vi.stubGlobal("Notification", NotificationStub);
	vi.stubGlobal("isSecureContext", true);
	Object.defineProperty(navigator, "serviceWorker", {
		configurable: true,
		value: serviceWorker,
	});
	return { pushManager, serviceWorker, Notification: NotificationStub };
}

beforeEach(() => {
	Element.prototype.scrollIntoView = vi.fn();
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: { circles: [membership] },
	});
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	Reflect.deleteProperty(navigator, "serviceWorker");
});

describe("notification channel switches", () => {
	it("shows only email when the server offers nothing else", async () => {
		mockPreferences();
		mockChannels();
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ email_enabled: false }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const email = await screen.findByRole("switch", { name: "Email" });
		expect(email).toBeChecked();
		expect(
			screen.queryByRole("switch", { name: "Text message" }),
		).not.toBeInTheDocument();
		expect(
			screen.queryByRole("switch", { name: "Push notifications" }),
		).not.toBeInTheDocument();

		fireEvent.click(email);
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { email_enabled: false }),
		);
	});

	it("keeps text messages off until a phone is confirmed", async () => {
		mockPreferences({ sms_enabled: true });
		mockChannels({ sms_available: true });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const sms = await screen.findByRole("switch", { name: "Text message" });
		expect(sms).toBeDisabled();
		expect(sms).not.toBeChecked();
		expect(
			screen.getByText("Add and confirm a phone number below to turn this on."),
		).toBeInTheDocument();
	});

	it("adds and confirms a phone, then turns texts on", async () => {
		mockPreferences();
		mockChannels({ sms_available: true });
		const start = vi
			.spyOn(profileServices, "startPhoneVerification")
			.mockResolvedValue({
				data: channels({
					sms_available: true,
					phone_number: "+15551234567",
					phone_verification_pending: true,
				}),
			});
		const verify = vi.spyOn(profileServices, "verifyPhone").mockResolvedValue({
			data: channels({
				sms_available: true,
				phone_number: "+15551234567",
				phone_verified: true,
			}),
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ sms_enabled: true }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		fireEvent.change(await screen.findByLabelText("Mobile number"), {
			target: { value: "+1 555 123 4567" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Text me a code" }));
		await waitFor(() => expect(start).toHaveBeenCalledWith("+1 555 123 4567"));

		fireEvent.change(await screen.findByRole("textbox", { name: "Code" }), {
			target: { value: "123456" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
		await waitFor(() => expect(verify).toHaveBeenCalledWith("123456"));

		expect(
			await screen.findByText("Texts go to +15551234567."),
		).toBeInTheDocument();
		const sms = screen.getByRole("switch", { name: "Text message" });
		await waitFor(() => expect(sms).toBeEnabled());
		fireEvent.click(sms);
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { sms_enabled: true }),
		);
	});

	it("sets up phones and devices only in the default settings", async () => {
		mockPreferences();
		mockChannels({ sms_available: true, push_available: true });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		const trigger = await screen.findByRole("combobox", {
			name: /settings for/i,
		});
		fireEvent.keyDown(trigger, { key: "ArrowDown" });
		fireEvent.click(
			await screen.findByRole("option", { name: "Smith Family" }),
		);

		expect(
			await screen.findByText(
				"Add and confirm a phone number in your default settings to turn this on.",
			),
		).toBeInTheDocument();
		expect(screen.queryByLabelText("Mobile number")).not.toBeInTheDocument();
		expect(screen.queryByText("Push on this device")).not.toBeInTheDocument();
		expect(
			screen.getByRole("switch", { name: "Push notifications" }),
		).toBeInTheDocument();
	});
});

describe("push on this device", () => {
	it("explains when the browser has no push support", async () => {
		mockPreferences();
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		expect(
			await screen.findByText("This browser can't receive push notifications."),
		).toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: "Enable push on this device" }),
		).not.toBeInTheDocument();
	});

	it("subscribes the device and switches push on", async () => {
		const browser = installPushBrowser("granted");
		mockPreferences();
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });
		const save = vi
			.spyOn(profileServices, "savePushSubscription")
			.mockResolvedValue({
				data: channels({
					push_available: true,
					vapid_public_key: VAPID_KEY,
					push_device_count: 1,
				}),
			});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ push_enabled: true }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Enable push on this device" }),
		);

		await waitFor(() =>
			expect(save).toHaveBeenCalledWith({
				endpoint: "https://fcm.googleapis.com/fcm/send/device-1",
				keys: { p256dh: "device-key", auth: "device-auth" },
			}),
		);
		expect(browser.Notification.requestPermission).toHaveBeenCalled();
		expect(browser.serviceWorker.register).toHaveBeenCalledWith("/sw.js", {
			scope: "/",
		});
		expect(browser.pushManager.subscribe).toHaveBeenCalledWith({
			userVisibleOnly: true,
			applicationServerKey: new Uint8Array([4, 16, 65]),
		});
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { push_enabled: true }),
		);
		expect(
			await screen.findByText("Push is on for this device."),
		).toBeInTheDocument();
	});

	it("explains how to unblock when permission is denied", async () => {
		const browser = installPushBrowser("denied");
		mockPreferences();
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });
		const save = vi.spyOn(profileServices, "savePushSubscription");

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Enable push on this device" }),
		);

		expect(
			await screen.findByText(/Notifications are blocked for this site/),
		).toBeInTheDocument();
		expect(browser.pushManager.subscribe).not.toHaveBeenCalled();
		expect(save).not.toHaveBeenCalled();
	});

	it("turns push off for this device", async () => {
		const browser = installPushBrowser("granted");
		const subscription = {
			endpoint: "https://fcm.googleapis.com/fcm/send/device-1",
			unsubscribe: vi.fn().mockResolvedValue(true),
		};
		browser.serviceWorker.getRegistration.mockResolvedValue({
			pushManager: { getSubscription: async () => subscription },
		});
		mockPreferences({ push_enabled: true });
		mockChannels({
			push_available: true,
			vapid_public_key: VAPID_KEY,
			push_device_count: 1,
		});
		const remove = vi
			.spyOn(profileServices, "removePushSubscription")
			.mockResolvedValue({
				data: channels({ push_available: true, vapid_public_key: VAPID_KEY }),
			});

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Turn off on this device" }),
		);

		await waitFor(() =>
			expect(remove).toHaveBeenCalledWith(
				"https://fcm.googleapis.com/fcm/send/device-1",
			),
		);
		expect(subscription.unsubscribe).toHaveBeenCalled();
		expect(
			await screen.findByRole("button", { name: "Enable push on this device" }),
		).toBeInTheDocument();
	});
});

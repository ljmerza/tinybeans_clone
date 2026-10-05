import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
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
	new_media_email: true,
	new_media_sms: false,
	new_media_push: false,
	comments_email: true,
	comments_sms: false,
	comments_push: false,
	replies_email: true,
	replies_sms: false,
	replies_push: false,
	likes_email: true,
	likes_sms: false,
	likes_push: false,
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

const EVENT_TITLES = [
	"New photos and videos",
	"Comments on my posts",
	"Replies and mentions",
	"Likes on my posts",
];

/** The toggle for one event (by its row title) on one channel (by its label). */
async function findToggle(event: string, channel: string) {
	const row = await screen.findByRole("group", { name: event });
	return within(row).findByRole("button", { name: channel });
}

function allToggles(channel: string) {
	return screen.queryAllByRole("button", { name: channel });
}

describe("event and channel toggles", () => {
	it("shows only the email column when the server offers nothing else", async () => {
		mockPreferences();
		mockChannels();
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ new_media_email: false }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const email = await findToggle("New photos and videos", "Email");
		expect(email).toHaveAttribute("aria-pressed", "true");

		fireEvent.click(email);
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { new_media_email: false }),
		);
		await waitFor(() => expect(email).toHaveAttribute("aria-pressed", "false"));
		// The channels have loaded by now.
		expect(profileServices.getNotificationChannels).toHaveBeenCalled();
		expect(allToggles("Email")).toHaveLength(4);
		expect(allToggles("Text message")).toHaveLength(0);
		expect(allToggles("Push")).toHaveLength(0);
		expect(
			screen.queryByText(/Message and data rates may apply/),
		).not.toBeInTheDocument();
	});

	it("sends only the pair that was toggled", async () => {
		mockPreferences();
		mockChannels({
			sms_available: true,
			phone_number: "+15551234567",
			phone_verified: true,
			push_available: true,
			vapid_public_key: VAPID_KEY,
			push_device_count: 1,
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ likes_push: true }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const likesPush = await findToggle("Likes on my posts", "Push");
		await waitFor(() => expect(likesPush).toBeEnabled());
		for (const title of EVENT_TITLES) {
			const row = screen.getByRole("group", { name: title });
			expect(
				within(row)
					.getAllByRole("button")
					.map((button) => button.getAttribute("aria-label")),
			).toEqual(["Email", "Text message", "Push"]);
		}
		expect(likesPush).toHaveAttribute("aria-pressed", "false");
		fireEvent.click(likesPush);

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { likes_push: true }),
		);
		expect(update).toHaveBeenCalledTimes(1);
		await waitFor(() =>
			expect(likesPush).toHaveAttribute("aria-pressed", "true"),
		);
		expect(await findToggle("New photos and videos", "Push")).toHaveAttribute(
			"aria-pressed",
			"false",
		);
	});

	it("keeps text messages off until a phone is confirmed", async () => {
		mockPreferences({ replies_sms: true });
		mockChannels({ sms_available: true });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const replies = await findToggle("Replies and mentions", "Text message");
		expect(replies).toHaveAttribute("aria-pressed", "false");
		for (const toggle of allToggles("Text message")) {
			expect(toggle).toBeDisabled();
		}
		expect(allToggles("Text message")).toHaveLength(4);
		expect(
			screen.getByText("To get texts, add and confirm a phone number below."),
		).toBeInTheDocument();
		expect(
			screen.getByText(/Message and data rates may apply/),
		).toBeInTheDocument();
	});

	it("adds and confirms a phone, then turns texts on for one event", async () => {
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
			.mockResolvedValue({ data: preferences({ comments_sms: true }) });

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
		expect(
			screen.queryByText(/To get texts, add and confirm/),
		).not.toBeInTheDocument();
		const sms = await findToggle("Comments on my posts", "Text message");
		await waitFor(() => expect(sms).toBeEnabled());
		fireEvent.click(sms);
		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { comments_sms: true }),
		);
	});

	it("disables push until a device is subscribed", async () => {
		installPushBrowser("granted");
		mockPreferences({ likes_push: true });
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const likes = await findToggle("Likes on my posts", "Push");
		expect(likes).toBeDisabled();
		expect(likes).toHaveAttribute("aria-pressed", "false");
		for (const toggle of allToggles("Push")) {
			expect(toggle).toBeDisabled();
		}
		expect(
			screen.getByText(
				"To get push notifications, turn on push for this device below.",
			),
		).toBeInTheDocument();
	});

	it("points to another device when this browser can't receive push", async () => {
		mockPreferences();
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		expect(
			await screen.findByText(
				"To get push notifications, turn on push from a phone or computer that supports it.",
			),
		).toBeInTheDocument();
		expect(await findToggle("Comments on my posts", "Push")).toBeDisabled();
	});

	it("lets push be chosen here once another device is subscribed", async () => {
		mockPreferences({ likes_push: true });
		mockChannels({
			push_available: true,
			vapid_public_key: VAPID_KEY,
			push_device_count: 1,
		});

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const likes = await findToggle("Likes on my posts", "Push");
		await waitFor(() => expect(likes).toBeEnabled());
		expect(likes).toHaveAttribute("aria-pressed", "true");
		expect(
			screen.queryByText(/To get push notifications/),
		).not.toBeInTheDocument();
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
				"To get texts, add and confirm a phone number in your default settings.",
			),
		).toBeInTheDocument();
		expect(screen.queryByLabelText("Mobile number")).not.toBeInTheDocument();
		expect(screen.queryByText("Push on this device")).not.toBeInTheDocument();
		expect(allToggles("Push")).toHaveLength(4);
		expect(allToggles("Text message")).toHaveLength(4);
	});

	it("saves a circle's pair to that circle", async () => {
		mockPreferences({ per_circle_override: true });
		mockChannels({
			push_available: true,
			vapid_public_key: VAPID_KEY,
			push_device_count: 1,
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({
				data: preferences({
					circle_id: 7,
					per_circle_override: true,
					new_media_push: true,
				}),
			});

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		const trigger = await screen.findByRole("combobox", {
			name: /settings for/i,
		});
		fireEvent.keyDown(trigger, { key: "ArrowDown" });
		fireEvent.click(
			await screen.findByRole("option", { name: "Smith Family" }),
		);
		await screen.findByText("This circle has its own settings.");

		const push = await findToggle("New photos and videos", "Push");
		await waitFor(() => expect(push).toBeEnabled());
		fireEvent.click(push);

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(7, { new_media_push: true }),
		);
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
			.mockResolvedValue({
				data: preferences({
					new_media_push: true,
					comments_push: true,
					replies_push: true,
					likes_push: true,
				}),
			});

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
			expect(update).toHaveBeenCalledWith(null, {
				new_media_push: true,
				comments_push: true,
				replies_push: true,
				likes_push: true,
			}),
		);
		expect(
			await screen.findByText("Push is on for this device."),
		).toBeInTheDocument();
		const likes = await findToggle("Likes on my posts", "Push");
		await waitFor(() => expect(likes).toBeEnabled());
		expect(likes).toHaveAttribute("aria-pressed", "true");
	});

	it("switches push on only for events that already reach this person", async () => {
		installPushBrowser("granted");
		mockPreferences({ likes_email: false, comments_email: false });
		mockChannels({ push_available: true, vapid_public_key: VAPID_KEY });
		vi.spyOn(profileServices, "savePushSubscription").mockResolvedValue({
			data: channels({
				push_available: true,
				vapid_public_key: VAPID_KEY,
				push_device_count: 1,
			}),
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences() });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Enable push on this device" }),
		);

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, {
				new_media_push: true,
				replies_push: true,
			}),
		);
	});

	it("leaves push choices alone when some event already uses push", async () => {
		installPushBrowser("granted");
		mockPreferences({ likes_push: true });
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
		const update = vi.spyOn(profileServices, "updateNotificationPreferences");

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		fireEvent.click(
			await screen.findByRole("button", { name: "Enable push on this device" }),
		);

		await waitFor(() => expect(save).toHaveBeenCalled());
		expect(
			await screen.findByText("Push is on for this device."),
		).toBeInTheDocument();
		expect(update).not.toHaveBeenCalled();
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
		mockPreferences({ likes_push: true });
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

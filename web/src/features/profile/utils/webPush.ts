/**
 * Browser side of web push: support checks, permission, and the push
 * subscription for this device. The service worker lives at /sw.js.
 */
import type { PushSubscriptionPayload } from "../api/services";

const SERVICE_WORKER_URL = "/sw.js";

/**
 * - "supported": this browser can subscribe.
 * - "install-required": iPhone/iPad Safari; push works only in the app added
 *   to the Home Screen (iOS 16.4+).
 * - "unsupported": no push in this browser, or not a secure (HTTPS) page.
 */
export type PushSupport = "supported" | "install-required" | "unsupported";

/** Notification permission was refused (or dismissed) instead of granted. */
export class PushPermissionDeniedError extends Error {
	constructor(permission: NotificationPermission) {
		super(`Notification permission ${permission}`);
		this.name = "PushPermissionDeniedError";
	}
}

function isAppleMobile(): boolean {
	return (
		/iPad|iPhone|iPod/.test(navigator.userAgent) ||
		// iPadOS reports itself as a Mac.
		(navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
	);
}

function isInstalledApp(): boolean {
	return (
		window.matchMedia?.("(display-mode: standalone)").matches ||
		(navigator as Navigator & { standalone?: boolean }).standalone === true
	);
}

export function getPushSupport(): PushSupport {
	if (
		window.isSecureContext &&
		"serviceWorker" in navigator &&
		"PushManager" in window &&
		"Notification" in window
	) {
		return "supported";
	}
	if (isAppleMobile() && !isInstalledApp()) {
		return "install-required";
	}
	return "unsupported";
}

export function getNotificationPermission(): NotificationPermission {
	return "Notification" in window ? Notification.permission : "default";
}

/** VAPID public key (base64url) to the bytes PushManager.subscribe expects. */
export function vapidKeyToBytes(base64Url: string): Uint8Array<ArrayBuffer> {
	const base64 = (base64Url + "=".repeat((4 - (base64Url.length % 4)) % 4))
		.replace(/-/g, "+")
		.replace(/_/g, "/");
	const raw = atob(base64);
	const bytes = new Uint8Array(new ArrayBuffer(raw.length));
	for (let i = 0; i < raw.length; i += 1) {
		bytes[i] = raw.charCodeAt(i);
	}
	return bytes;
}

function sameKey(current: ArrayBuffer | null, wanted: Uint8Array): boolean {
	if (!current) return false;
	const bytes = new Uint8Array(current);
	return (
		bytes.length === wanted.length &&
		bytes.every((byte, index) => byte === wanted[index])
	);
}

function toPayload(subscription: PushSubscription): PushSubscriptionPayload {
	const json = subscription.toJSON();
	return {
		endpoint: subscription.endpoint,
		keys: { p256dh: json.keys?.p256dh ?? "", auth: json.keys?.auth ?? "" },
	};
}

/** This device's current push subscription, if it has one. */
export async function getPushSubscription(): Promise<PushSubscription | null> {
	const registration = await navigator.serviceWorker.getRegistration("/");
	return registration ? registration.pushManager.getSubscription() : null;
}

/**
 * Ask for permission, register the service worker and subscribe this device.
 * Call it straight from a click: iOS only shows the prompt for a user gesture.
 */
export async function subscribeToPush(
	vapidPublicKey: string,
): Promise<PushSubscriptionPayload> {
	const permission = await Notification.requestPermission();
	if (permission !== "granted") {
		throw new PushPermissionDeniedError(permission);
	}
	await navigator.serviceWorker.register(SERVICE_WORKER_URL, { scope: "/" });
	const registration = await navigator.serviceWorker.ready;
	const applicationServerKey = vapidKeyToBytes(vapidPublicKey);

	const existing = await registration.pushManager.getSubscription();
	if (existing) {
		if (sameKey(existing.options.applicationServerKey, applicationServerKey)) {
			return toPayload(existing);
		}
		// Subscribed with an older server key; subscribe() would reject it.
		await existing.unsubscribe();
	}
	const subscription = await registration.pushManager.subscribe({
		userVisibleOnly: true,
		applicationServerKey,
	});
	return toPayload(subscription);
}

/** Unsubscribe this device; returns the endpoint to remove on the server. */
export async function unsubscribeFromPush(): Promise<string | null> {
	const subscription = await getPushSubscription();
	if (!subscription) return null;
	await subscription.unsubscribe();
	return subscription.endpoint;
}

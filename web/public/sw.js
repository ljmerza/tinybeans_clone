/*
 * Circles service worker: web push only.
 *
 * Registered from the notification settings page when someone turns on push
 * for a device (src/features/profile/utils/webPush.ts). It shows pushed
 * notifications and opens the post when one is tapped. There is deliberately
 * no fetch handler, so it never caches or serves app files.
 *
 * Payload (mysite/keeps/notifications.py::_send_push): {title, body, url, tag}.
 */

self.addEventListener("install", () => {
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
	let data = {};
	try {
		data = event.data ? event.data.json() : {};
	} catch {
		data = { body: event.data ? event.data.text() : "" };
	}
	event.waitUntil(
		self.registration.showNotification(data.title || "Circles", {
			body: data.body || "",
			icon: "/logo192.png",
			badge: "/logo192.png",
			tag: data.tag,
			data: { url: data.url || "/" },
		}),
	);
});

self.addEventListener("notificationclick", (event) => {
	event.notification.close();
	const target = new URL(event.notification.data?.url || "/", self.location.origin);
	// Only ever open pages of this app.
	const url = target.origin === self.location.origin ? target.href : self.location.origin;
	event.waitUntil(
		self.clients
			.matchAll({ type: "window", includeUncontrolled: true })
			.then((windows) => {
				const open = windows.find((client) => client.url === url);
				if (open) return open.focus();
				return self.clients.openWindow(url);
			}),
	);
});

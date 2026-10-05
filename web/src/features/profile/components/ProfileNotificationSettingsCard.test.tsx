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
import { type NotificationPreferences, profileServices } from "../api/services";
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

const membership = {
	membership_id: 1,
	circle: { id: 7, name: "Smith Family", slug: "smith-family" },
	role: "member",
	is_owner: false,
	created_at: "2026-09-01T00:00:00Z",
} as CircleMembershipSummary;

beforeEach(() => {
	// Radix Select scrolls the chosen option into view, which jsdom lacks.
	Element.prototype.scrollIntoView = vi.fn();
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: { circles: [membership] },
	});
	vi.spyOn(profileServices, "getNotificationChannels").mockResolvedValue({
		data: {
			sms_available: false,
			phone_number: null,
			phone_verified: false,
			phone_verification_pending: false,
			push_available: false,
			vapid_public_key: "",
			push_device_count: 0,
		},
	});
});

afterEach(() => {
	vi.restoreAllMocks();
});

async function openSelect(label: RegExp) {
	const trigger = await screen.findByRole("combobox", { name: label });
	// jsdom drops pointer event details, so open it the keyboard way.
	fireEvent.keyDown(trigger, { key: "ArrowDown" });
	return trigger;
}

describe("ProfileNotificationSettingsCard", () => {
	it("saves a toggle to the default preferences", async () => {
		vi.spyOn(profileServices, "getNotificationPreferences").mockResolvedValue({
			data: preferences(),
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ notify_likes: false }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const likes = await screen.findByRole("switch", {
			name: "Likes on my posts",
		});
		expect(likes).toBeChecked();
		fireEvent.click(likes);

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { notify_likes: false }),
		);
		await waitFor(() =>
			expect(
				screen.getByRole("switch", { name: "Likes on my posts" }),
			).not.toBeChecked(),
		);
	});

	it("turns on the daily email summary, off by default", async () => {
		vi.spyOn(profileServices, "getNotificationPreferences").mockResolvedValue({
			data: preferences(),
		});
		const update = vi
			.spyOn(profileServices, "updateNotificationPreferences")
			.mockResolvedValue({ data: preferences({ email_digest: true }) });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);

		const digest = await screen.findByRole("switch", {
			name: "Daily email summary",
		});
		expect(digest).not.toBeChecked();
		fireEvent.click(digest);

		await waitFor(() =>
			expect(update).toHaveBeenCalledWith(null, { email_digest: true }),
		);
		await waitFor(() =>
			expect(
				screen.getByRole("switch", { name: "Daily email summary" }),
			).toBeChecked(),
		);
	});

	it("edits a circle's override and can reset it to the defaults", async () => {
		const get = vi
			.spyOn(profileServices, "getNotificationPreferences")
			.mockImplementation(async (circleId) => ({
				data:
					circleId === 7
						? preferences({
								circle_id: 7,
								per_circle_override: true,
								notify_new_media: false,
							})
						: preferences(),
			}));
		const reset = vi
			.spyOn(profileServices, "resetCircleNotificationPreferences")
			.mockResolvedValue({ data: preferences() });

		renderWithQueryClient(<ProfileNotificationSettingsCard />);
		await openSelect(/settings for/i);
		fireEvent.click(
			await screen.findByRole("option", { name: "Smith Family" }),
		);

		await waitFor(() => expect(get).toHaveBeenCalledWith(7));
		expect(
			await screen.findByText("This circle has its own settings."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("switch", { name: "New photos and videos" }),
		).not.toBeChecked();
		// The summary covers every circle, so it's only on the defaults.
		expect(
			screen.queryByRole("switch", { name: "Daily email summary" }),
		).not.toBeInTheDocument();

		fireEvent.click(screen.getByRole("button", { name: "Use my defaults" }));

		await waitFor(() => expect(reset).toHaveBeenCalledWith(7));
		expect(
			await screen.findByText(/This circle uses your default settings/),
		).toBeInTheDocument();
	});
});

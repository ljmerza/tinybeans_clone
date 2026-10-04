import type { RequestOptions } from "@/features/auth/api/authClient";
import { apiClient as authApi } from "@/features/auth/api/authClient";
import type { AuthUser } from "@/features/auth/types";
import type { ApiResponseWithMessages } from "@/types";

export interface UserProfileResponse {
	user: AuthUser;
}

export type UpdateUserProfileRequest = Partial<AuthUser> & {
	[key: string]: unknown;
};

export type NotificationChannel = "email" | "sms";

export interface NotificationPreferences {
	notify_new_media: boolean;
	notify_comments: boolean;
	notify_replies: boolean;
	notify_likes: boolean;
	channel: NotificationChannel;
	/** Daily new-post email; only the default (all circles) preferences have it. */
	email_digest: boolean;
	circle_id: number | null;
	per_circle_override: boolean;
}

export type UpdateNotificationPreferencesRequest = Partial<
	Omit<NotificationPreferences, "circle_id" | "per_circle_override">
>;

const notificationPreferencesPath = (circleId: number | null) =>
	circleId === null
		? "/users/me/email-preferences/"
		: `/users/me/email-preferences/?circle_id=${circleId}`;

export const profileServices = {
	getProfile() {
		return authApi.get<ApiResponseWithMessages<UserProfileResponse>>(
			"/users/me/",
		);
	},

	updateProfile(body: UpdateUserProfileRequest, options?: RequestOptions) {
		return authApi.patch<ApiResponseWithMessages<UserProfileResponse>>(
			"/users/me/",
			body,
			options,
		);
	},

	getNotificationPreferences(circleId: number | null) {
		return authApi.get<ApiResponseWithMessages<NotificationPreferences>>(
			notificationPreferencesPath(circleId),
		);
	},

	updateNotificationPreferences(
		circleId: number | null,
		body: UpdateNotificationPreferencesRequest,
	) {
		return authApi.patch<ApiResponseWithMessages<NotificationPreferences>>(
			notificationPreferencesPath(circleId),
			body,
			{ suppressSuccessToast: true },
		);
	},

	resetCircleNotificationPreferences(circleId: number) {
		return authApi.delete<ApiResponseWithMessages<NotificationPreferences>>(
			notificationPreferencesPath(circleId),
			undefined,
			{ suppressSuccessToast: true },
		);
	},
};

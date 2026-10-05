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

export interface ChangePasswordRequest {
	current_password: string;
	password: string;
	password_confirm: string;
}

export interface ChangePasswordResponse {
	tokens: { access: string };
}

export type NotificationChannel = "email" | "sms" | "push";

export interface NotificationPreferences {
	notify_new_media: boolean;
	notify_comments: boolean;
	notify_replies: boolean;
	notify_likes: boolean;
	email_enabled: boolean;
	/** Texts go only to a verified phone (see NotificationChannels). */
	sms_enabled: boolean;
	push_enabled: boolean;
	/** Daily new-post email; only the default (all circles) preferences have it. */
	email_digest: boolean;
	circle_id: number | null;
	per_circle_override: boolean;
}

export type UpdateNotificationPreferencesRequest = Partial<
	Omit<NotificationPreferences, "circle_id" | "per_circle_override">
>;

/** What the server offers for each channel, plus this user's phone and devices. */
export interface NotificationChannels {
	sms_available: boolean;
	phone_number: string | null;
	phone_verified: boolean;
	phone_verification_pending: boolean;
	push_available: boolean;
	/** VAPID public key (base64url) for PushManager.subscribe; empty when push is off. */
	vapid_public_key: string;
	push_device_count: number;
}

/** A browser's PushSubscription.toJSON(). */
export interface PushSubscriptionPayload {
	endpoint: string;
	keys: { p256dh: string; auth: string };
}

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

	/**
	 * Change the signed-in user's password. The server revokes every refresh
	 * token, sets a new refresh cookie, and returns the matching access token.
	 */
	changePassword(body: ChangePasswordRequest) {
		return authApi.post<ApiResponseWithMessages<ChangePasswordResponse>>(
			"/auth/password/change/",
			body,
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

	getNotificationChannels() {
		return authApi.get<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/notification-channels/",
		);
	},

	/** Save the phone notification texts go to and text it a code. */
	startPhoneVerification(phoneNumber: string) {
		return authApi.post<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/notification-phone/",
			{ phone_number: phoneNumber },
		);
	},

	verifyPhone(code: string) {
		return authApi.post<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/notification-phone/verify/",
			{ code },
		);
	},

	removePhone() {
		return authApi.delete<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/notification-phone/",
		);
	},

	savePushSubscription(subscription: PushSubscriptionPayload) {
		return authApi.post<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/push-subscriptions/",
			subscription,
			{ suppressSuccessToast: true },
		);
	},

	removePushSubscription(endpoint: string) {
		return authApi.delete<ApiResponseWithMessages<NotificationChannels>>(
			"/users/me/push-subscriptions/",
			{ endpoint },
			{ suppressSuccessToast: true },
		);
	},
};

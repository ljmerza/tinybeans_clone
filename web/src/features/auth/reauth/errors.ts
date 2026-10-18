import { combineMessages, translateMessages } from "@/i18n/notificationUtils";
import type { HttpError } from "@/lib/httpClient";
import type { TFunction } from "i18next";

/**
 * The API's own messages for a failed request, translated, or `fallbackKey`
 * when it sent none (e.g. a network error).
 */
export function apiErrorMessage(
	error: unknown,
	t: TFunction,
	fallbackKey: string,
): string {
	const messages = (error as HttpError | null)?.messages;
	return combineMessages(translateMessages(messages, t)) || t(fallbackKey);
}

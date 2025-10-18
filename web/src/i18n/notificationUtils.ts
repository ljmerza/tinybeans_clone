/**
 * Notification Utilities
 *
 * Utilities for handling standardized API messages with i18n support.
 */
import type { TFunction } from "i18next";

// Re-export types for backward compatibility
export type { ApiMessage, ApiResponse };

/**
 * Infer severity level from HTTP status code
 */
export function inferSeverity(status: number): "success" | "warning" | "error" {
	if (status >= 500) return "error";
	if (status >= 400) return "error";
	if (status >= 300) return "warning";
	return "success";
}

/**
 * Translate API messages using i18next
 *
 * @param messages - Array of API messages from backend
 * @param t - Translation function from useTranslation()
 * @returns Array of translated message strings
 *
 * @example
 * ```typescript
 * const { t } = useTranslation();
 * const messages = translateMessages(response.messages, t);
 * ```
 */
type MessageLike = ApiMessage | string;

const isApiMessage = (message: MessageLike): message is ApiMessage => {
	return (
		typeof message === "object" && message !== null && "i18n_key" in message
	);
};

const ERROR_DETAIL_REGEX = /ErrorDetail\(string=['"]([^'"]+)['"]/;

const normalizeMessageKey = (key: string): string => {
	let normalized = key.trim();

	if (normalized.startsWith("[") && normalized.endsWith("]")) {
		normalized = normalized.slice(1, -1).trim();
	}

	const match = normalized.match(ERROR_DETAIL_REGEX);
	if (match?.[1]) {
		return match[1];
	}

	return normalized;
};

export function translateMessages(
	messages: ApiMessage[] | undefined,
	t: TFunction,
): string[] {
	if (!messages || messages.length === 0) return [];

	return (messages as MessageLike[]).map((msg) => translateMessage(msg, t));
}

/**
 * Translate a single API message
 *
 * @param message - Single API message from backend
 * @param t - Translation function from useTranslation()
 * @returns Translated message string
 */
export function translateMessage(message: MessageLike, t: TFunction): string {
	if (typeof message === "string") {
		const normalized = normalizeMessageKey(message);
		return t(normalized, { defaultValue: normalized });
	}

	try {
		const normalizedKey = normalizeMessageKey(message.i18n_key);
		return t(normalizedKey, {
			defaultValue: normalizedKey,
			...(message.context ?? {}),
		});
	} catch (error) {
		console.warn(`Translation failed for key: ${message.i18n_key}`, error);
		const normalizedKey = normalizeMessageKey(message.i18n_key);
		return t(normalizedKey, {
			defaultValue: normalizedKey,
			...(message.context ?? {}),
		});
	}
}

/**
 * Combine multiple messages into a single string
 *
 * @param messages - Array of translated message strings
 * @param separator - Separator between messages (default: '\n')
 * @returns Combined message string
 */
export function combineMessages(messages: string[], separator = "\n"): string {
	return messages.filter((msg) => msg.trim().length > 0).join(separator);
}

/**
 * Extract field-specific errors from messages
 *
 * @param messages - Array of API messages with field context
 * @param t - Translation function from useTranslation()
 * @returns Map of field names to error messages
 *
 * @example
 * ```typescript
 * const { t } = useTranslation();
 * const fieldErrors = extractFieldErrors(response.messages, t);
 * // { email: "Please enter a valid email address", password: "Password is too short" }
 * ```
 */
export function extractFieldErrors(
	messages: ApiMessage[] | undefined,
	t: TFunction,
): Record<string, string> {
	if (!messages || messages.length === 0) return {};

	const fieldErrors: Record<string, string> = {};

	for (const msg of messages as MessageLike[]) {
		if (!isApiMessage(msg)) continue;

		const field = msg.context?.field;
		if (field && typeof field === "string") {
			fieldErrors[field] = translateMessage(msg, t);
		}
	}

	return fieldErrors;
}

/**
 * Get general (non-field) errors from messages
 *
 * @param messages - Array of API messages
 * @param t - Translation function from useTranslation()
 * @returns Array of general error messages
 */
export function getGeneralErrors(
	messages: ApiMessage[] | undefined,
	t: TFunction,
): string[] {
	if (!messages || messages.length === 0) return [];

	return (messages as MessageLike[])
		.filter((msg) => !isApiMessage(msg) || !msg.context?.field)
		.map((msg) => translateMessage(msg, t));
}

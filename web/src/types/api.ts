/**
 * @fileoverview Shared API types used across the application.
 * Standardized message format for backend-frontend communication.
 * 
 * @module types/api
 */

/**
 * Message structure from backend API with i18n support.
 * 
 * Messages contain translation keys and optional context for interpolation.
 * Components should use `useApiMessages()` hook to translate these messages.
 * 
 * @example
 * ```typescript
 * {
 *   i18n_key: "auth.login.success",
 *   context: { username: "john_doe" }
 * }
 * ```
 */
export interface ApiMessage {
	/** Translation key for i18n */
	i18n_key: string;
	/** Optional context for message interpolation */
	context?: Record<string, string | number | boolean>;
}

/**
 * Standard API response structure.
 * 
 * All API responses follow this structure to provide consistent
 * handling of data, messages, and errors.
 * 
 * @template T - Type of the data payload
 * 
 * @example Success response with messages
 * ```typescript
 * {
 *   data: { id: 123, name: "John" },
 *   messages: [
 *     { i18n_key: "user.created", context: { name: "John" } }
 *   ]
 * }
 * ```
 * 
 * @example Error response
 * ```typescript
 * {
 *   error: "Invalid credentials",
 *   messages: [
 *     { i18n_key: "auth.invalid_credentials" }
 *   ]
 * }
 * ```
 */
export interface ApiResponse<T = unknown> {
	/** Response data payload */
	data?: T;
	/** Translatable messages (success, info, warnings) */
	messages?: ApiMessage[];
	/** Error message (typically for 4xx/5xx responses) */
	error?: string;
}

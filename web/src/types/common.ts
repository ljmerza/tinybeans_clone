/**
 * Common type definitions used across the application
 */

import type { ApiMessage } from "./api";
import type { FieldApi } from "@tanstack/react-form";

/**
 * Generic API response structure with messages
 */
export interface ApiResponseWithMessages<T = unknown> {
	messages?: ApiMessage[];
	data?: T;
	tokens?: {
		access: string;
		[key: string]: unknown;
	};
	[key: string]: unknown;
}

/**
 * Generic error object structure
 */
export interface ApiError extends Error {
	status?: number;
	messages?: ApiMessage[];
	data?: unknown;
	[key: string]: unknown;
}

/**
 * Form field type from TanStack Form
 * Represents a field from the form API
 */
export type FormField<TData = unknown, TFormData = unknown> = FieldApi<
	TFormData,
	TData
>;

/**
 * Mutation response type with data wrapper
 * Used by TanStack Query mutations that wrap response in { data: T }
 */
export interface MutationResponse<T> {
	data: T;
}

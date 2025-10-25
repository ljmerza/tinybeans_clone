/**
 * Form utilities for TanStack Form + Zod integration
 * Keep it simple - just helpers for common patterns
 */
import type { ZodSchema } from "zod";

/**
 * Create a simple validator for TanStack Form fields
 * Converts Zod validation errors to string messages
 *
 * @example
 * <form.Field
 *   name="email"
 *   validators={{ onBlur: zodValidator(emailSchema) }}
 * >
 *   {(field) => <input {...field} />}
 * </form.Field>
 */
export function zodValidator<T>(schema: ZodSchema<T>) {
	return ({ value }: { value: T }) => {
		const result = schema.safeParse(value);
		return result.success ? undefined : result.error.errors[0]?.message;
	};
}

/**
 * Map server validation errors to field error format
 * Handles Django/DRF error format: { field: ["error1", "error2"] }
 *
 * @example
 * const errors = mapServerErrors(response.data.errors)
 * // { email: "This email is already taken", first_name: "Too short" }
*/
export function mapServerErrors(
	serverErrors: Record<string, string[]>,
): Record<string, string> {
	const fieldErrors: Record<string, string> = {};

	for (const [field, messages] of Object.entries(serverErrors)) {
		if (messages?.length > 0) {
			fieldErrors[field] = messages.join(". ");
		}
	}

	return fieldErrors;
}

/**
 * Extract non-field errors for general display
 * Looks for common Django/DRF non-field error keys
 *
 * @example
 * const generalErrors = getGeneralErrors(response.data.errors)
 * if (generalErrors.length > 0) {
 *   setGeneralError(generalErrors.join('. '))
 * }
 */
export function getGeneralErrors(
	serverErrors: Record<string, string[]>,
): string[] {
	const generalKeys = ["non_field_errors", "__all__", "detail"];
	return generalKeys.flatMap((key) => serverErrors[key] || []);
}

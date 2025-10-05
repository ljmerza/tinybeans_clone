/**
 * Error Handling Utilities
 * 
 * Provides consistent error extraction and handling patterns
 * for authentication and 2FA operations.
 */

/**
 * Extracts API error message from error object
 * 
 * Handles the common pattern of extracting error messages from API responses
 * with a fallback chain: API message → Error message → Default message
 * 
 * @param err - The error object from catch block
 * @param fallbackMessage - Default message if no error message found
 * @returns Extracted error message string
 * 
 * @example
 * ```typescript
 * try {
 *   await someApiCall();
 * } catch (err) {
 *   const errorMsg = extractApiError(err, 'Operation failed');
 *   setError(errorMsg);
 * }
 * ```
 */
export function extractApiError(
	err: unknown,
	fallbackMessage = "An error occurred"
): string {
	// Try to extract API error message
	const apiMessage = (err as { data?: { error?: string } })?.data?.error;
	
	if (apiMessage) {
		return apiMessage;
	}
	
	// Fall back to Error message
	if (err instanceof Error) {
		return err.message;
	}
	
	// Use provided fallback
	return fallbackMessage;
}

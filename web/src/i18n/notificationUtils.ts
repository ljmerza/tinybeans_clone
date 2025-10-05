/**
 * Notification Utilities
 * Implements ADR-012: Notification Strategy
 * 
 * Utilities for handling standardized API messages with i18n support.
 */
import type { TFunction } from 'i18next';
import type { ApiMessage, ApiResponse } from '@/types';

// Re-export types for backward compatibility
export type { ApiMessage, ApiResponse };

/**
 * Infer severity level from HTTP status code
 */
export function inferSeverity(status: number): 'success' | 'warning' | 'error' {
  if (status >= 500) return 'error';
  if (status >= 400) return 'error';
  if (status >= 300) return 'warning';
  return 'success';
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
export function translateMessages(
  messages: ApiMessage[] | undefined,
  t: TFunction
): string[] {
  if (!messages || messages.length === 0) return [];
  
  return messages.map(msg => {
    try {
      return t(msg.i18n_key, msg.context || {});
    } catch (error) {
      // Fallback to key if translation fails
      console.warn(`Translation failed for key: ${msg.i18n_key}`, error);
      return msg.i18n_key;
    }
  });
}

/**
 * Translate a single API message
 * 
 * @param message - Single API message from backend
 * @param t - Translation function from useTranslation()
 * @returns Translated message string
 */
export function translateMessage(
  message: ApiMessage,
  t: TFunction
): string {
  try {
    return t(message.i18n_key, message.context || {});
  } catch (error) {
    console.warn(`Translation failed for key: ${message.i18n_key}`, error);
    return message.i18n_key;
  }
}

/**
 * Combine multiple messages into a single string
 * 
 * @param messages - Array of translated message strings
 * @param separator - Separator between messages (default: '\n')
 * @returns Combined message string
 */
export function combineMessages(
  messages: string[],
  separator: string = '\n'
): string {
  return messages.filter(msg => msg.trim().length > 0).join(separator);
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
  t: TFunction
): Record<string, string> {
  if (!messages || messages.length === 0) return {};
  
  const fieldErrors: Record<string, string> = {};
  
  for (const msg of messages) {
    const field = msg.context?.field;
    if (field && typeof field === 'string') {
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
  t: TFunction
): string[] {
  if (!messages || messages.length === 0) return [];
  
  return messages
    .filter(msg => !msg.context?.field)
    .map(msg => translateMessage(msg, t));
}

/**
 * useApiMessages Hook
 * Implements ADR-012: Notification Strategy
 * 
 * Provides utilities for handling API messages with i18n translation
 */
import { useTranslation } from 'react-i18next';
import { showToast } from '@/lib/toast';
import { 
  translateMessages, 
  translateMessage,
  combineMessages, 
  extractFieldErrors,
  getGeneralErrors,
  inferSeverity,
  type ApiMessage,
  type ApiResponse
} from './notificationUtils';

export function useApiMessages() {
  const { t } = useTranslation();

  /**
   * Translate messages from API response
   */
  const translate = (messages: ApiMessage[] | undefined) => {
    return translateMessages(messages, t);
  };

  /**
   * Translate a single message
   */
  const translateOne = (message: ApiMessage) => {
    return translateMessage(message, t);
  };

  /**
   * Show API messages as toast
   * Combines multiple messages and infers severity from status
   */
  const showAsToast = (
    messages: ApiMessage[] | undefined,
    status: number,
    options?: { separator?: string }
  ) => {
    if (!messages || messages.length === 0) return;
    
    const translatedMessages = translate(messages);
    const message = combineMessages(translatedMessages, options?.separator);
    const level = inferSeverity(status);
    
    if (message) {
      showToast({ message, level });
    }
  };

  /**
   * Extract field errors for form validation
   */
  const getFieldErrors = (messages: ApiMessage[] | undefined) => {
    return extractFieldErrors(messages, t);
  };

  /**
   * Get general (non-field) errors
   */
  const getGeneral = (messages: ApiMessage[] | undefined) => {
    return getGeneralErrors(messages, t);
  };

  /**
   * Handle error response - show general errors as toast, return field errors
   */
  const handleError = (error: { messages?: ApiMessage[]; status?: number }) => {
    const generalErrors = getGeneral(error.messages);
    if (generalErrors.length > 0) {
      const message = combineMessages(generalErrors);
      const level = error.status ? inferSeverity(error.status) : 'error';
      showToast({ message, level });
    }
    return getFieldErrors(error.messages);
  };

  /**
   * Handle success response - optionally show as toast
   */
  const handleSuccess = (
    response: ApiResponse<unknown>,
    options?: { showToast?: boolean; status?: number }
  ) => {
    if (options?.showToast && response.messages) {
      showAsToast(response.messages, options.status ?? 200);
    }
  };

  return {
    translate,
    translateOne,
    showAsToast,
    getFieldErrors,
    getGeneral,
    handleError,
    handleSuccess,
  };
}

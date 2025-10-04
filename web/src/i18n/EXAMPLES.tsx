/**
 * Example: Using ADR-012 Notification Strategy
 * 
 * This file demonstrates the proper usage of the notification strategy
 * with i18n support. Use these patterns in your components.
 * 
 * @fileoverview Example code - not for production use
 */

/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useTranslation } from 'react-i18next';
import { useApiMessages, type ApiResponse } from '@/i18n';
import { showToast } from '@/lib/toast';
import { apiClient } from '@/features/auth/api/modernAuthClient';

/**
 * Example 1: Simple success with inline feedback
 * Component shows its own UI feedback, suppresses API messages
 */
export function ExampleUploadPhoto() {
  const uploadPhoto = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('photo', file);
      
      const response = await apiClient.post('/profile/photo/', formData);
      
      // Component shows inline UI feedback
      // Don't display response.messages - user already sees the new photo
      console.log('Photo uploaded:', response);
      
    } catch (error) {
      // Handle errors if needed
      console.error('Upload failed:', error);
    }
  };
  
  return null; // Your component JSX
}

/**
 * Example 2: Background operation with toast notification
 * Show success/error messages as toasts
 */
export function ExampleSyncData() {
  const { showAsToast } = useApiMessages();
  
  const syncData = async () => {
    try {
      const response = await apiClient.post<ApiResponse>('/sync/', {});
      
      // Show success messages as toast
      if (response.messages) {
        showAsToast(response.messages, 200);
      }
      
    } catch (error: any) {
      // Show error messages as toast
      if (error.messages) {
        showAsToast(error.messages, error.status || 400);
      }
    }
  };
  
  return null;
}

/**
 * Example 3: Form validation with field-level errors
 * Show errors inline next to form fields
 */
export function ExampleUpdateProfile() {
  const { handleError } = useApiMessages();
  
  const updateProfile = async (data: { email: string; password: string }) => {
    try {
      const response = await apiClient.patch('/profile/', data);
      
      // Success - show inline feedback or navigate away
      console.log('Profile updated:', response);
      
    } catch (error: any) {
      // Extract field errors and show them inline
      const fieldErrors = handleError(error);
      
      // fieldErrors = { email: "Please enter a valid email", password: "Password too short" }
      // Use these to set form field errors
      Object.entries(fieldErrors).forEach(([field, message]) => {
        console.log(`Set error for ${field}:`, message);
        // setFieldError(field, message); // Your form library
      });
    }
  };
  
  return null;
}

/**
 * Example 4: Multiple messages shown together
 * Combine and display all messages
 */
export function ExampleMultipleErrors() {
  const { translate } = useApiMessages();
  
  const validateForm = async (data: unknown) => {
    try {
      await apiClient.post('/validate/', data);
    } catch (error: any) {
      // Get all error messages
      const messages = translate(error.messages);
      
      // Show all together
      const allMessages = messages.join('\n');
      showToast({ message: allMessages, level: 'error' });
    }
  };
  
  return null;
}

/**
 * Example 5: Using translation directly
 * Translate messages for custom UI
 */
export function ExampleCustomDisplay() {
  const { t } = useTranslation();
  
  const doSomething = async () => {
    try {
      await apiClient.post('/action/', {});
    } catch (error: any) {
      // Manually translate each message for custom display
      error.messages?.forEach((msg: any) => {
        const translated = t(msg.i18n_key, msg.context);
        console.log('Translated message:', translated);
        // Display in your custom UI
      });
    }
  };
  
  return null;
}

/**
 * Example 6: Changing user language
 * Update language preference
 */
export function ExampleLanguageSwitcher() {
  const { i18n } = useTranslation();
  
  const changeLanguage = async (language: 'en' | 'es') => {
    // Change language immediately
    await i18n.changeLanguage(language);
    
    // Update user preference on backend
    await apiClient.patch('/profile/', { language });
  };
  
  return null;
}

/**
 * Example 7: Backend response format
 * 
 * Success response (no message needed):
 * {
 *   "data": { "photoUrl": "https://..." }
 * }
 * 
 * Error response:
 * {
 *   "error": "file_too_large",
 *   "messages": [
 *     {
 *       "i18n_key": "errors.file_too_large",
 *       "context": {
 *         "filename": "vacation-photo.jpg",
 *         "maxSize": "10MB"
 *       }
 *     }
 *   ]
 * }
 * 
 * Multiple validation errors:
 * {
 *   "error": "validation_failed",
 *   "messages": [
 *     {
 *       "i18n_key": "errors.email_invalid",
 *       "context": { "field": "email" }
 *     },
 *     {
 *       "i18n_key": "errors.password_too_short",
 *       "context": { "field": "password", "minLength": 8 }
 *     }
 *   ]
 * }
 */

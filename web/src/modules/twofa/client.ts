/**
 * Two-Factor Authentication API Client
 * Uses corrected endpoints matching backend implementation
 */

import { api, API_BASE } from '../login/client'
import { authStore } from '../login/store'
import type {
  TwoFactorSetupResponse,
  TwoFactorVerifyLoginResponse,
  TwoFactorStatusResponse,
  RecoveryCodesResponse,
  TrustedDevicesResponse,
} from './types'

export const twoFactorApi = {
  /**
   * Initialize 2FA setup
   * Returns QR code for TOTP or sends OTP for email/SMS
   */
  initializeSetup: (method: 'totp' | 'email' | 'sms', phone_number?: string) =>
    api.post<TwoFactorSetupResponse>('/auth/2fa/setup/', { method, phone_number }),

  /**
   * Verify setup code and enable 2FA
   * Returns recovery codes
   */
  verifySetup: (code: string) =>
    api.post<RecoveryCodesResponse>('/auth/2fa/verify-setup/', { code }),

  /**
   * Get current 2FA status
   */
  getStatus: () =>
    api.get<TwoFactorStatusResponse>('/auth/2fa/status/'),

  /**
   * Verify 2FA code during login (CORRECTED endpoint name)
   * Accepts both 6-digit codes and recovery codes
   * partial_token in body (not Authorization header)
   */
  verifyLogin: (partial_token: string, code: string, remember_me: boolean = false) =>
    api.post<TwoFactorVerifyLoginResponse>('/auth/2fa/verify-login/', {
      partial_token,
      code,
      remember_me,
    }),

  /**
   * Disable 2FA
   */
  disable: (code: string) =>
    api.post<{ enabled: boolean; message: string }>('/auth/2fa/disable/', { code }),

  /**
   * Generate new recovery codes (invalidates old ones)
   */
  generateRecoveryCodes: () =>
    api.post<RecoveryCodesResponse>('/auth/2fa/recovery-codes/generate/', {}),

  /**
   * Download recovery codes as TXT or PDF
   */
  downloadRecoveryCodes: (format: 'txt' | 'pdf' = 'txt') => {
    const url = `${API_BASE}/auth/2fa/recovery-codes/download/?format=${format}`
    window.open(url, '_blank')
  },

  /**
   * Get list of trusted devices
   */
  getTrustedDevices: () =>
    api.get<TrustedDevicesResponse>('/auth/2fa/trusted-devices/'),

  /**
   * Remove a trusted device (CORRECTED: uses DELETE method)
   */
  removeTrustedDevice: async (device_id: string): Promise<{ message: string }> => {
    const token = authStore.state.accessToken
    const res = await fetch(`${API_BASE}/auth/2fa/trusted-devices/${device_id}/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || data.detail || 'Failed to remove device')
    }
    return res.json()
  },
}

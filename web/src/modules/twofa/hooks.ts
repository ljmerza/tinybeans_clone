/**
 * Two-Factor Authentication React Query Hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { twoFactorApi } from './client'
import { setAccessToken } from '../login/store'
import type { TwoFactorMethod } from './types'

/**
 * Initialize 2FA setup
 */
export function useInitialize2FASetup() {
  return useMutation({
    mutationFn: ({ method, phone_number }: { method: TwoFactorMethod; phone_number?: string }) =>
      twoFactorApi.initializeSetup(method, phone_number),
  })
}

/**
 * Verify setup code and complete 2FA setup
 */
export function useVerify2FASetup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (code: string) => twoFactorApi.verifySetup(code),
    onSuccess: () => {
      // Invalidate status to refresh
      queryClient.invalidateQueries({ queryKey: ['2fa', 'status'] })
    },
  })
}

/**
 * Get 2FA status
 */
export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa', 'status'],
    queryFn: () => twoFactorApi.getStatus(),
  })
}

/**
 * Verify 2FA code during login
 */
export function useVerify2FALogin() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: ({
      partial_token,
      code,
      remember_me,
    }: {
      partial_token: string
      code: string
      remember_me?: boolean
    }) => twoFactorApi.verifyLogin(partial_token, code, remember_me),
    onSuccess: (data) => {
      console.log('2FA verify success:', data) // Debug log
      
      // Store access token
      if (data.tokens && data.tokens.access) {
        console.log('Setting access token:', data.tokens.access.substring(0, 20) + '...') // Debug log
        setAccessToken(data.tokens.access)
      } else {
        console.error('No access token in response:', data) // Debug log
      }

      // Device ID cookie is set by backend automatically
      if (data.trusted_device) {
        console.log('Device marked as trusted') // Debug log
      }

      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['user'] })
      queryClient.invalidateQueries({ queryKey: ['auth'] })

      // Navigate to home - use setTimeout to ensure navigation happens after state update
      console.log('Navigating to home page') // Debug log
      setTimeout(() => {
        navigate({ to: '/' })
      }, 0)
    },
    onError: (error) => {
      console.error('2FA verify error:', error) // Debug log
    },
  })
}

/**
 * Disable 2FA
 */
export function useDisable2FA() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (code: string) => twoFactorApi.disable(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa', 'status'] })
    },
  })
}

/**
 * Generate new recovery codes
 */
export function useGenerateRecoveryCodes() {
  return useMutation({
    mutationFn: () => twoFactorApi.generateRecoveryCodes(),
  })
}

/**
 * Get trusted devices
 */
export function useTrustedDevices() {
  return useQuery({
    queryKey: ['2fa', 'trusted-devices'],
    queryFn: () => twoFactorApi.getTrustedDevices(),
  })
}

/**
 * Remove a trusted device
 */
export function useRemoveTrustedDevice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (device_id: string) => twoFactorApi.removeTrustedDevice(device_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa', 'trusted-devices'] })
    },
  })
}

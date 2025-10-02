/**
 * 2FA Verification Page
 * Used during login when 2FA is required
 */

import { createFileRoute, useNavigate, useLocation, Navigate } from '@tanstack/react-router'
import { useState, useEffect, useRef } from 'react'
import { useVerify2FALogin } from '@/modules/twofa/hooks'
import { VerificationInput } from '@/modules/twofa/components/VerificationInput'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import type { TwoFactorVerifyState } from '@/modules/twofa/types'

function TwoFactorVerifyPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const hasLoadedData = useRef(false)
  
  // Initialize verify data state
  const [verifyData, setVerifyData] = useState<TwoFactorVerifyState | null>(null)
  
  // Load verify data once on mount
  useEffect(() => {
    if (hasLoadedData.current) return
    hasLoadedData.current = true
    
    // Check location state first
    const state = location.state as any as TwoFactorVerifyState | undefined
    if (state?.partialToken && state?.method) {
      console.log('2FA Verify Data from location state:', state)
      setVerifyData(state)
      return
    }
    
    // Fallback to sessionStorage
    const stored = sessionStorage.getItem('2fa_verify_data')
    if (stored) {
      try {
        const data = JSON.parse(stored)
        console.log('2FA Verify Data from sessionStorage:', data)
        setVerifyData(data)
        // Clean up after reading
        sessionStorage.removeItem('2fa_verify_data')
      } catch (error) {
        console.error('Failed to parse 2FA verify data:', error)
      }
    }
  }, [location.state])
  
  const [code, setCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [useRecoveryCode, setUseRecoveryCode] = useState(false)

  const verify = useVerify2FALogin()
  console.log('2FA Verify State:', { verifyData, code, rememberMe, useRecoveryCode, isPending: verify.isPending, error: verify.error })

  // Redirect if no partial token (direct access or page refresh)
  if (!verifyData?.partialToken || !verifyData?.method) {
    return null;
    // return <Navigate to="/login" />
  }

  const { partialToken, method, message } = verifyData

  const handleVerify = () => {
    if (useRecoveryCode && code.length < 14) return
    if (!useRecoveryCode && code.length !== 6) return

    console.log('Verifying 2FA code...') // Debug log
    verify.mutate({
      partial_token: partialToken,
      code,
      remember_me: rememberMe,
    })
  }

  const getMethodDisplay = () => {
    if (useRecoveryCode) return 'recovery code'
    switch (method) {
      case 'totp':
        return 'authenticator app'
      case 'email':
        return 'email'
      case 'sms':
        return 'phone'
      default:
        return method
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-2">Two-Factor Authentication</h1>
          
          {!useRecoveryCode && message && (
            <p className="text-gray-600">{message}</p>
          )}
          
          {!useRecoveryCode && !message && (
            <p className="text-gray-600">
              Enter the 6-digit code from your {getMethodDisplay()}
            </p>
          )}

          {useRecoveryCode && (
            <p className="text-gray-600">
              Enter one of your recovery codes
            </p>
          )}
        </div>

        <div className="space-y-4">
          {!useRecoveryCode ? (
            <VerificationInput
              value={code}
              onChange={setCode}
              onComplete={handleVerify}
              disabled={verify.isPending}
            />
          ) : (
            <div className="space-y-2">
              <Label htmlFor="recovery-code">Recovery Code</Label>
              <Input
                id="recovery-code"
                type="text"
                placeholder="XXXX-XXXX-XXXX"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                disabled={verify.isPending}
                className="text-center font-mono text-lg"
                maxLength={14}
              />
              <p className="text-xs text-gray-500 text-center">
                Format: XXXX-XXXX-XXXX (with dashes)
              </p>
            </div>
          )}

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="remember-me"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={verify.isPending}
              className="h-4 w-4 rounded border-gray-300"
            />
            <Label
              htmlFor="remember-me"
              className="text-sm font-normal cursor-pointer"
            >
              Remember this device for 30 days
            </Label>
          </div>

          <Button
            onClick={handleVerify}
            disabled={
              (useRecoveryCode ? code.length < 14 : code.length !== 6) ||
              verify.isPending
            }
            className="w-full"
          >
            {verify.isPending ? 'Verifying...' : 'Verify'}
          </Button>

          {verify.error && (
            <div className="bg-red-50 border border-red-200 rounded p-3">
              <p className="text-sm text-red-600 text-center">
                {(verify.error as any)?.message || 'Invalid code. Please try again.'}
              </p>
            </div>
          )}

          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setUseRecoveryCode(!useRecoveryCode)
                setCode('')
              }}
              disabled={verify.isPending}
              className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              {useRecoveryCode
                ? '← Use verification code instead'
                : 'Use recovery code instead →'}
            </button>
          </div>
        </div>

        <div className="pt-4 border-t text-center">
          <button
            type="button"
            onClick={() => navigate({ to: '/login' })}
            disabled={verify.isPending}
            className="text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
          >
            ← Back to login
          </button>
        </div>
      </div>
    </div>
  )
}

export const Route = createFileRoute('/2fa/verify')({
  component: TwoFactorVerifyPage,
})

/**
 * 2FA Settings Page
 * Manage 2FA configuration, recovery codes, and trusted devices
 */

import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { use2FAStatus, useDisable2FA, useGenerateRecoveryCodes } from '@/modules/twofa/hooks'
import { Button } from '@/components/ui/button'
import { RecoveryCodeList } from '@/modules/twofa/components/RecoveryCodeList'
import { VerificationInput } from '@/modules/twofa/components/VerificationInput'

function TwoFactorSettingsPage() {
  const navigate = useNavigate()
  const { data: status, isLoading } = use2FAStatus()
  const disable2FA = useDisable2FA()
  const generateCodes = useGenerateRecoveryCodes()

  const [showDisableConfirm, setShowDisableConfirm] = useState(false)
  const [disableCode, setDisableCode] = useState('')
  const [showNewCodes, setShowNewCodes] = useState(false)

  const handleDisable = async () => {
    if (disableCode.length !== 6) return

    try {
      await disable2FA.mutateAsync(disableCode)
      navigate({ to: '/' })
    } catch (error) {
      setDisableCode('')
    }
  }

  const handleGenerateNewCodes = async () => {
    try {
      await generateCodes.mutateAsync()
      setShowNewCodes(true)
    } catch (error) {
      console.error('Failed to generate codes:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    )
  }

  if (!status?.is_enabled) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center space-y-4">
          <h1 className="text-2xl font-semibold">Two-Factor Authentication</h1>
          <p className="text-gray-600">
            2FA is not enabled for your account. Enable it to add an extra layer of security.
          </p>
          <Button onClick={() => navigate({ to: '/2fa/setup' })} className="w-full">
            Enable 2FA
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-semibold mb-2">Two-Factor Authentication</h1>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
                  ✓ Enabled
                </span>
                <span className="text-sm text-gray-600">
                  Method: <span className="font-semibold">{status.preferred_method?.toUpperCase()}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recovery Codes */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Recovery Codes</h2>
          
          {!showNewCodes ? (
            <div className="space-y-4">
              <p className="text-gray-600 text-sm">
                Recovery codes can be used to access your account if you lose access to your
                authenticator device. Each code can only be used once.
              </p>
              
              <div className="flex gap-2">
                <Button
                  onClick={handleGenerateNewCodes}
                  disabled={generateCodes.isPending}
                  variant="outline"
                >
                  {generateCodes.isPending ? 'Generating...' : 'Generate New Recovery Codes'}
                </Button>
                
                <Button
                  onClick={() => navigate({ to: '/2fa/settings' })}
                  variant="outline"
                >
                  View Current Codes
                </Button>
              </div>

              {generateCodes.error && (
                <p className="text-sm text-red-600">
                  {(generateCodes.error as any)?.message || 'Failed to generate codes'}
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {generateCodes.data && (
                <RecoveryCodeList codes={generateCodes.data.recovery_codes} />
              )}
              <Button onClick={() => setShowNewCodes(false)} variant="outline">
                Done
              </Button>
            </div>
          )}
        </div>

        {/* Trusted Devices */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Trusted Devices</h2>
          <p className="text-gray-600 text-sm mb-4">
            Manage devices that can skip 2FA verification for 30 days.
          </p>
          <Button
            onClick={() => navigate({ to: '/2fa/trusted-devices' })}
            variant="outline"
          >
            Manage Trusted Devices
          </Button>
        </div>

        {/* Disable 2FA */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 text-red-600">Disable Two-Factor Authentication</h2>
          
          {!showDisableConfirm ? (
            <div className="space-y-4">
              <p className="text-gray-600 text-sm">
                Disabling 2FA will make your account less secure. You'll only need your password to log in.
              </p>
              <Button
                onClick={() => setShowDisableConfirm(true)}
                variant="outline"
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                Disable 2FA
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 rounded p-4">
                <p className="text-sm text-red-800 font-semibold mb-2">
                  ⚠️ Are you sure?
                </p>
                <p className="text-sm text-red-800">
                  Enter your 6-digit verification code to confirm disabling 2FA.
                </p>
              </div>

              <VerificationInput
                value={disableCode}
                onChange={setDisableCode}
                onComplete={handleDisable}
                disabled={disable2FA.isPending}
              />

              <div className="flex gap-2">
                <Button
                  onClick={handleDisable}
                  disabled={disableCode.length !== 6 || disable2FA.isPending}
                  variant="outline"
                  className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
                >
                  {disable2FA.isPending ? 'Disabling...' : 'Confirm Disable'}
                </Button>
                <Button
                  onClick={() => {
                    setShowDisableConfirm(false)
                    setDisableCode('')
                  }}
                  variant="outline"
                  className="flex-1"
                  disabled={disable2FA.isPending}
                >
                  Cancel
                </Button>
              </div>

              {disable2FA.error && (
                <p className="text-sm text-red-600 text-center">
                  {(disable2FA.error as any)?.message || 'Failed to disable 2FA'}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Back Button */}
        <div className="text-center">
          <button
            onClick={() => navigate({ to: '/' })}
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            ← Back to home
          </button>
        </div>
      </div>
    </div>
  )
}

export const Route = createFileRoute('/2fa/settings')({
  component: TwoFactorSettingsPage,
})

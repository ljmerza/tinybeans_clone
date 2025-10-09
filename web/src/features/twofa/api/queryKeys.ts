/**
 * Two-Factor Authentication Query Keys
 */

import type { TwoFactorMethod } from "../types";

const rootKey = ["2fa"] as const;

export const twoFaKeys = {
	all: () => rootKey,
	status: () => [...rootKey, "status"] as const,
	trustedDevices: () => [...rootKey, "trusted-devices"] as const,
	method: (method: TwoFactorMethod) => [...rootKey, "method", method] as const,
	recoveryCodes: () => [...rootKey, "recovery-codes"] as const,
};

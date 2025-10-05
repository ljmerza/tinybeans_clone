/**
 * @fileoverview Generic 2FA setup step components.
 * Consolidates duplicate step components across Email/SMS/TOTP methods.
 * 
 * @module features/twofa/components/setup/generic
 */

export { GenericIntroStep } from "./GenericIntroStep";
export { GenericVerifyStep } from "./GenericVerifyStep";
export { GenericRecoveryStep } from "./GenericRecoveryStep";
export type {
	IntroStepConfig,
	VerifyStepConfig,
	RecoveryStepConfig,
} from "./types";

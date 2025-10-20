/**
 * Two-factor authentication validation schemas
 * Each schema is separate for code splitting
 */
import { z } from "zod";

/**
 * 6-digit verification code
 * Used across TOTP, SMS, and Email 2FA
 */
export const verificationCodeSchema = z
	.string()
	.length(6, "validation.code_length")
	.regex(/^\d{6}$/, "validation.code_digits_only");

/**
 * Phone number for SMS 2FA setup
 */
export const phoneNumberSchema = z
	.string()
	.min(1, "validation.phone_required")
	.regex(/^\+?[1-9]\d{1,14}$/, "validation.phone_invalid");

/**
 * Device name for trusted devices
 */
export const deviceNameSchema = z
	.string()
	.min(1, "validation.device_name_required")
	.max(50, "validation.device_name_max_length");

export type VerificationCodeData = z.infer<typeof verificationCodeSchema>;
export type PhoneNumberData = z.infer<typeof phoneNumberSchema>;
export type DeviceNameData = z.infer<typeof deviceNameSchema>;

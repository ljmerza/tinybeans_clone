/**
 * Password reset validation schemas
 * Split between request and confirm to allow separate code splitting
 */
import { z } from "zod";
import { emailSchema, passwordSchema } from "./common.js";

/**
 * Password reset request (step 1)
 * Accepts email only
 */
export const passwordResetRequestSchema = z.object({
	email: emailSchema,
});

export type PasswordResetRequestFormData = z.infer<
	typeof passwordResetRequestSchema
>;

/**
 * Password reset confirm (step 2)
 * New password with confirmation
 */
export const passwordResetConfirmPasswordSchema = z
	.string()
	.min(1, "validation.confirm_password_required");

const passwordResetConfirmBaseSchema = z.object({
	password: passwordSchema,
	password_confirm: passwordResetConfirmPasswordSchema,
});

export const passwordResetConfirmSchema = passwordResetConfirmBaseSchema.refine(
	(data) => data.password === data.password_confirm,
	{
		message: "validation.passwords_must_match",
		path: ["password_confirm"],
	},
);

export const passwordResetConfirmFieldSchemas =
	passwordResetConfirmBaseSchema.shape;

export type PasswordResetConfirmFormData = z.infer<
	typeof passwordResetConfirmSchema
>;

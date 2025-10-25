/**
 * Signup form validation schema
 * Only imported by signup feature
 */
import { z } from "zod";
import {
	emailSchema,
	firstNameSchema,
	lastNameSchema,
	passwordSchema,
} from "./common";

const confirmPasswordSchema = z
	.string()
	.min(1, "validation.confirm_password_required");

// Base schema without refinement - needed for field-level validation
export const signupSchemaBase = z.object({
	first_name: firstNameSchema,
	last_name: lastNameSchema,
	email: emailSchema,
	password: passwordSchema,
	password_confirm: confirmPasswordSchema,
});

// Full schema with refinement for form-level validation
export const signupSchema = signupSchemaBase.refine(
	(data) => data.password === data.password_confirm,
	{
		message: "validation.passwords_must_match",
		path: ["password_confirm"],
	},
);

export type SignupFormData = z.infer<typeof signupSchema>;

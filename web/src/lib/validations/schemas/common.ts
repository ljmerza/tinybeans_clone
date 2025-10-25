/**
 * Common/shared validation primitives
 * These are tiny and imported by specific schemas
 */
import { z } from "zod";

/**
 * Email validation - RFC compliant
 */
export const emailSchema = z
	.string()
	.min(1, "validation.email_required")
	.email("validation.email_valid");

export const firstNameSchema = z
	.string()
	.min(1, "validation.first_name_required");

export const lastNameSchema = z
	.string()
	.min(1, "validation.last_name_required");

/**
 * Password validation - minimum 8 characters
 */
export const passwordSchema = z
	.string()
	.min(8, "validation.password_min_length");

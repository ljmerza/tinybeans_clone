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

/**
 * Username validation
 */
export const usernameSchema = z
	.string()
	.min(1, "validation.username_required")
	.min(3, "validation.username_min_length")
	.max(30, "validation.username_max_length")
	.regex(/^[a-zA-Z0-9_]+$/, "validation.username_invalid_chars");

/**
 * Password validation - minimum 8 characters
 */
export const passwordSchema = z
	.string()
	.min(8, "validation.password_min_length");

/**
 * Generic identifier (email or username)
 */
export const identifierSchema = z.string().min(1, "validation.field_required");

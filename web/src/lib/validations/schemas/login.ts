/**
 * Login form validation schema
 * Only imported by login feature - keeps bundle small
 */
import { z } from "zod";
import { emailSchema, passwordSchema } from "./common";

export const loginSchema = z.object({
	email: emailSchema,
	password: passwordSchema,
});

export type LoginFormData = z.infer<typeof loginSchema>;

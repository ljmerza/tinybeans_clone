/**
 * Login form validation schema
 * Only imported by login feature - keeps bundle small
 */
import { z } from "zod";
import { passwordSchema, usernameSchema } from "./common";

export const loginSchema = z.object({
	username: usernameSchema,
	password: passwordSchema,
});

export type LoginFormData = z.infer<typeof loginSchema>;

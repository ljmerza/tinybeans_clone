/**
 * Magic link request validation schema
 * Only imported by magic link feature
 */
import { z } from "zod";
import { emailSchema } from "./common";

export const magicLinkRequestSchema = z.object({
	email: emailSchema,
});

export type MagicLinkRequestFormData = z.infer<typeof magicLinkRequestSchema>;

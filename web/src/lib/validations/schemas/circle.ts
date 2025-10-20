import { z } from "zod";

export const circleNameSchema = z
	.string()
	.trim()
	.min(2, "validation.circle_name_min")
	.max(255, "validation.circle_name_max");

export const circleCreateSchema = z.object({
	name: circleNameSchema,
});

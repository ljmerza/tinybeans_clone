import { type VariantProps, cva } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
	"inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
	{
		variants: {
			variant: {
				default: "border-transparent bg-muted text-muted-foreground",
				success: "border-transparent bg-primary/10 text-primary",
				warning: "border-transparent bg-secondary text-secondary-foreground",
				destructive:
					"border-transparent bg-destructive/10 text-destructive-foreground",
				outline: "bg-transparent border-border text-foreground",
				accent: "border-transparent bg-accent text-accent-foreground",
			},
		},
		defaultVariants: {
			variant: "default",
		},
	},
);

interface BadgeProps
	extends HTMLAttributes<HTMLSpanElement>,
		VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
	return (
		<span
			data-slot="badge"
			className={cn(badgeVariants({ variant }), className)}
			{...props}
		/>
	);
}

export { badgeVariants };

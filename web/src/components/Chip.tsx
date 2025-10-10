import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export interface ChipProps {
	children: ReactNode;
	variant?:
		| "neutral"
		| "primary"
		| "success"
		| "warning"
		| "danger"
		| "info"
		| "custom";
	className?: string;
}

const variantStyles: Record<
	Exclude<NonNullable<ChipProps["variant"]>, "custom">,
	string
> = {
	neutral: "bg-muted text-muted-foreground",
	primary: "bg-primary/15 text-primary",
	success: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
	warning: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
	danger: "bg-destructive/10 text-destructive",
	info: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
};

export function Chip({ children, variant = "neutral", className }: ChipProps) {
	const baseClasses = "px-2 py-1 rounded inline-flex items-center";
	const variantClass = variant === "custom" ? "" : variantStyles[variant];

	return (
		<span className={cn(baseClasses, variantClass, className)}>{children}</span>
	);
}

interface ChipGroupProps {
	children: ReactNode;
	className?: string;
}

export function ChipGroup({ children, className }: ChipGroupProps) {
	return (
		<div className={cn("flex flex-wrap gap-2 text-xs", className)}>
			{children}
		</div>
	);
}

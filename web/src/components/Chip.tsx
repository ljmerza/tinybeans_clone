import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

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

const variantStyles: Record<Exclude<ChipProps["variant"], "custom">, string> = {
	neutral: "bg-gray-100 text-gray-700",
	primary: "bg-blue-100 text-blue-800",
	success: "bg-green-100 text-green-800",
	warning: "bg-yellow-100 text-yellow-800",
	danger: "bg-red-100 text-red-700",
	info: "bg-purple-100 text-purple-800",
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

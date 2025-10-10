import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type StatusVariant = "info" | "success" | "warning" | "error";

interface StatusMessageProps {
	children: ReactNode;
	variant?: StatusVariant;
	align?: "left" | "center" | "right";
	className?: string;
	role?: "status" | "alert" | "log" | "marquee" | "timer" | "progressbar";
	ariaLive?: "off" | "polite" | "assertive";
}

const variantStyles: Record<StatusVariant, string> = {
	info: "text-sky-600 dark:text-sky-300",
	success: "text-emerald-600 dark:text-emerald-300",
	warning: "text-amber-600 dark:text-amber-300",
	error: "text-destructive",
};

const alignStyles: Record<NonNullable<StatusMessageProps["align"]>, string> = {
	left: "text-left",
	center: "text-center",
	right: "text-right",
};

export function StatusMessage({
	children,
	variant = "info",
	align = "left",
	className,
	role,
	ariaLive,
}: StatusMessageProps) {
	const resolvedRole = role ?? (variant === "error" ? "alert" : "status");
	const resolvedAriaLive =
		ariaLive ?? (variant === "error" ? "assertive" : "polite");

	return (
		<p
			role={resolvedRole}
			aria-live={resolvedAriaLive}
			className={cn(
				"text-sm",
				variantStyles[variant],
				alignStyles[align],
				className,
			)}
		>
			{children}
		</p>
	);
}

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface InfoPanelProps {
	title?: ReactNode;
	children: ReactNode;
	variant?: "info" | "success" | "warning" | "danger";
	className?: string;
}

const variantClasses: Record<
	Exclude<InfoPanelProps["variant"], undefined>,
	string
> = {
	info: "bg-sky-500/15 border border-sky-500/30 dark:border-sky-500/40 text-sky-700 dark:text-sky-200 transition-colors",
	success:
		"bg-emerald-500/15 border border-emerald-500/20 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-200 transition-colors",
	warning:
		"bg-amber-500/15 border border-amber-500/30 dark:border-amber-500/40 text-amber-700 dark:text-amber-200 transition-colors",
	danger:
		"bg-destructive/10 border border-destructive/30 dark:border-destructive/40 text-destructive transition-colors",
};

export function InfoPanel({
	title,
	children,
	variant = "info",
	className,
}: InfoPanelProps) {
	return (
		<div
			className={cn(
				"rounded-lg p-4 transition-colors",
				variantClasses[variant],
				className,
			)}
		>
			{title ? <h3 className="font-semibold mb-2">{title}</h3> : null}
			<div className="text-sm leading-relaxed">{children}</div>
		</div>
	);
}

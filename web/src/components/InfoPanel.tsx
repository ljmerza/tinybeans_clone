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
	info: "bg-blue-50 border-blue-200 text-blue-900",
	success: "bg-green-50 border-green-200 text-green-900",
	warning: "bg-yellow-50 border-yellow-200 text-yellow-900",
	danger: "bg-red-50 border-red-200 text-red-900",
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
				"rounded-lg border p-4",
				variantClasses[variant],
				className,
			)}
		>
			{title ? <h3 className="font-semibold mb-2">{title}</h3> : null}
			<div className="text-sm leading-relaxed">{children}</div>
		</div>
	);
}

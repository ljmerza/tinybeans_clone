import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface EmptyStateProps {
	icon?: ReactNode;
	title: ReactNode;
	description?: ReactNode;
	actions?: ReactNode;
	children?: ReactNode;
	className?: string;
}

export function EmptyState({
	icon,
	title,
	description,
	actions,
	children,
	className,
}: EmptyStateProps) {
	return (
		<div
			className={cn(
				"flex flex-col items-center justify-center gap-4 py-16 text-center",
				className,
			)}
		>
			{icon ? (
				<div className="text-5xl" aria-hidden>
					{icon}
				</div>
			) : null}
			<div className="space-y-2 max-w-prose">
				<h2 className="heading-3">{title}</h2>
				{description ? <p className="text-body-sm">{description}</p> : null}
			</div>
			{actions ? (
				<div className="flex flex-wrap justify-center gap-2">{actions}</div>
			) : null}
			{children}
		</div>
	);
}

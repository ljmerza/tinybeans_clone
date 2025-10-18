import type { ReactNode } from "react";
import { LoadingSpinner } from "./LoadingSpinner";

interface StandardLoadingProps {
	message?: ReactNode;
	description?: ReactNode;
	icon?: ReactNode;
	className?: string;
	spinnerSize?: "sm" | "md" | "lg";
}

export function StandardLoading({
	message = "Loading...",
	description,
	icon,
	className = "",
	spinnerSize = "lg",
}: StandardLoadingProps) {
	return (
		<div
			className={`flex flex-col items-center justify-center text-center gap-3 py-16 ${className}`}
		>
			{icon ?? <LoadingSpinner size={spinnerSize} className="mx-auto" />}
			{message ? (
				<div className="text-lg font-medium text-foreground">{message}</div>
			) : null}
			{description ? (
				<div className="text-sm text-muted-foreground max-w-prose">
					{description}
				</div>
			) : null}
		</div>
	);
}

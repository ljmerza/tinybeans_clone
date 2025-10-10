import type { ReactNode } from "react";

interface StandardErrorProps {
	title?: ReactNode;
	message?: ReactNode;
	description?: ReactNode;
	actionLabel?: string;
	onAction?: () => void;
	extraContent?: ReactNode;
	icon?: ReactNode;
	className?: string;
}

export function StandardError({
	title = "Something went wrong",
	message,
	description,
	actionLabel,
	onAction,
	extraContent,
	icon,
	className = "",
}: StandardErrorProps) {
	return (
		<div
			className={`flex flex-col items-center justify-center text-center gap-4 py-16 ${className}`}
		>
			{icon}
			<div className="space-y-2">
				{title && (
					<h2 className="text-2xl font-semibold text-destructive">{title}</h2>
				)}
				{message && (
					<p className="text-base font-medium text-foreground">{message}</p>
				)}
				{description && (
					<p className="text-sm text-muted-foreground max-w-prose">
						{description}
					</p>
				)}
			</div>
			{actionLabel && onAction && (
				<button
					type="button"
					onClick={onAction}
					className="btn-primary shadow-sm"
				>
					{actionLabel}
				</button>
			)}
			{extraContent}
		</div>
	);
}

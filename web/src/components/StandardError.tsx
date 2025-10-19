import { Button } from "@/components/ui/button";
import type { VariantProps } from "class-variance-authority";
import type { buttonVariants } from "@/components/ui/button";
import type { ReactNode } from "react";

interface StandardErrorProps {
	title?: ReactNode;
	message?: ReactNode;
	description?: ReactNode;
	actionLabel?: string;
	onAction?: () => void;
	actionVariant?: VariantProps<typeof buttonVariants>["variant"];
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
	actionVariant = "primary",
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
				<Button
					type="button"
					onClick={onAction}
					variant={actionVariant}
					className="shadow-sm"
				>
					{actionLabel}
				</Button>
			)}
			{extraContent}
		</div>
	);
}

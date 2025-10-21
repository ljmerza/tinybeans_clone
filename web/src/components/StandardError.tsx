import { Button } from "@/components/ui/button";
import type { buttonVariants } from "@/components/ui/button";
import type { VariantProps } from "class-variance-authority";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

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
	title,
	message,
	description,
	actionLabel,
	onAction,
	actionVariant = "primary",
	extraContent,
	icon,
	className = "",
}: StandardErrorProps) {
	const { t } = useTranslation();
	const resolvedTitle =
		title === undefined
			? t("errors.generic.title", { defaultValue: "Something went wrong" })
			: title;
	const resolvedMessage =
		message === undefined
			? t("errors.generic.message", { defaultValue: "Please try again." })
			: message;

	return (
		<div
			className={`flex flex-col items-center justify-center text-center gap-4 py-16 ${className}`}
			role="alert"
		>
			{icon}
			<div className="space-y-2">
				{resolvedTitle ? (
					<h2 className="text-2xl font-semibold text-destructive">
						{resolvedTitle}
					</h2>
				) : null}
				{resolvedMessage ? (
					<p className="text-base font-medium text-foreground">
						{resolvedMessage}
					</p>
				) : null}
				{description ? (
					<p className="text-sm text-muted-foreground max-w-prose">
						{description}
					</p>
				) : null}
			</div>
			{actionLabel && onAction ? (
				<Button
					type="button"
					onClick={onAction}
					variant={actionVariant}
					className="shadow-sm"
				>
					{actionLabel}
				</Button>
			) : null}
			{extraContent}
		</div>
	);
}

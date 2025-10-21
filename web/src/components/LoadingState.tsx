import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

type LoadingLayout = "inline" | "section" | "fullscreen";

interface LoadingStateProps {
	message?: ReactNode;
	description?: ReactNode;
	icon?: ReactNode;
	layout?: LoadingLayout;
	spinnerSize?: "sm" | "md" | "lg";
	className?: string;
}

const sectionWrapperClass =
	"flex flex-col items-center justify-center text-center gap-3 py-16";

export function LoadingState({
	message,
	description,
	icon,
	layout = "section",
	spinnerSize,
	className,
}: LoadingStateProps) {
	const { t } = useTranslation();
	const resolvedMessage =
		message === undefined
			? t("common.loading", { defaultValue: "Loading..." })
			: message;

	if (layout === "inline") {
		return (
			<div
				className={cn(
					"inline-flex items-center gap-2 text-sm text-muted-foreground",
					className,
				)}
				aria-live="polite"
				aria-busy={resolvedMessage ? true : undefined}
			>
				{icon ?? (
					<LoadingSpinner size={spinnerSize ?? "sm"} className="text-primary" />
				)}
				<div className="flex flex-col">
					{resolvedMessage ? (
						<span className="font-medium text-foreground">
							{resolvedMessage}
						</span>
					) : null}
					{description ? (
						<span className="text-xs text-muted-foreground">{description}</span>
					) : null}
				</div>
			</div>
		);
	}

	const resolvedSpinnerSize = spinnerSize ?? "lg";
	const content = (
		<div
			className={cn(sectionWrapperClass, className)}
			aria-live="polite"
			aria-busy={resolvedMessage ? true : undefined}
		>
			{icon ?? (
				<LoadingSpinner
					size={resolvedSpinnerSize}
					className="mx-auto text-primary"
				/>
			)}
			{resolvedMessage ? (
				<div className="text-lg font-medium text-foreground">
					{resolvedMessage}
				</div>
			) : null}
			{description ? (
				<div className="text-sm text-muted-foreground max-w-prose">
					{description}
				</div>
			) : null}
		</div>
	);

	if (layout === "fullscreen") {
		return (
			<div className="min-h-screen w-full flex items-center justify-center bg-background transition-colors">
				{content}
			</div>
		);
	}

	return content;
}

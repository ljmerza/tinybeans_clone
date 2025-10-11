import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

import { StatusMessage } from "../StatusMessage";

type StatusMessageProps = ComponentProps<typeof StatusMessage>;

interface FormActionMessage
	extends Pick<
		StatusMessageProps,
		"variant" | "align" | "role" | "ariaLive" | "className"
	> {
	id?: string;
	content: ReactNode;
}

type SecondaryAlign = "start" | "center" | "end" | "between";

interface FormActionsProps {
	children: ReactNode;
	className?: string;
	secondary?: ReactNode;
	secondaryAlign?: SecondaryAlign;
	secondaryClassName?: string;
	messages?: FormActionMessage[];
}

const secondaryAlignClasses: Record<SecondaryAlign, string> = {
	start: "justify-start",
	center: "justify-center",
	end: "justify-end",
	between: "justify-between",
};

/**
 * Shared container for form action areas that keeps secondary actions,
 * submit buttons, and contextual status messaging aligned consistently.
 */
export function FormActions({
	children,
	className,
	secondary,
	secondaryAlign = "end",
	secondaryClassName,
	messages,
}: FormActionsProps) {
	return (
		<div className={cn("space-y-4", className)}>
			{secondary ? (
				<div
					className={cn(
						"flex",
						secondaryAlignClasses[secondaryAlign],
						secondaryClassName,
					)}
				>
					{secondary}
				</div>
			) : null}

			{children}

			{messages?.map((message, index) =>
				message.content ? (
					<StatusMessage
						key={message.id ?? index}
						variant={message.variant}
						align={message.align}
						role={message.role}
						ariaLive={message.ariaLive}
						className={message.className}
					>
						{message.content}
					</StatusMessage>
				) : null,
			)}
		</div>
	);
}

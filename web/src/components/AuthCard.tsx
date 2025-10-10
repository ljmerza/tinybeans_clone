import type { ReactNode } from "react";

import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from "@/components/Card";
import { cn } from "@/lib/utils";

interface AuthCardProps {
	title: string;
	description?: ReactNode;
	children: ReactNode;
	footer?: ReactNode;
	className?: string;
	containerClassName?: string;
	contentClassName?: string;
	headerClassName?: string;
	footerClassName?: string;
}

/**
 * Shared layout for authentication flows to ensure consistent card styling.
 */
export function AuthCard({
	title,
	description,
	children,
	footer,
	className,
	containerClassName,
	contentClassName,
	headerClassName,
	footerClassName,
}: AuthCardProps) {
	return (
		<div
			className={cn(
				"min-h-screen flex items-center justify-center bg-background px-4 transition-colors",
				containerClassName,
			)}
		>
			<Card className={cn("w-full max-w-sm shadow-md", className)}>
				<CardHeader className={cn("space-y-2 text-center", headerClassName)}>
					<CardTitle className="text-2xl font-semibold">{title}</CardTitle>
					{description ? (
						<CardDescription>{description}</CardDescription>
					) : null}
				</CardHeader>
				<CardContent className={cn("space-y-4", contentClassName)}>
					{children}
				</CardContent>
				{footer ? (
					<CardFooter className={cn("space-y-3 text-center", footerClassName)}>
						{footer}
					</CardFooter>
				) : null}
			</Card>
		</div>
	);
}

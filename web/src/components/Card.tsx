import { cn } from "@/lib/utils";
import type { ElementType, ReactNode } from "react";

interface CardProps {
	children: ReactNode;
	className?: string;
	as?: ElementType;
}

export function Card({
	children,
	className,
	as: Component = "div",
}: CardProps) {
	return (
		<Component
			className={cn(
				"rounded-lg border border-border bg-card text-card-foreground shadow-sm transition-colors",
				className,
			)}
		>
			{children}
		</Component>
	);
}

interface CardHeaderProps {
	children: ReactNode;
	className?: string;
}

export function CardHeader({ children, className }: CardHeaderProps) {
	return <div className={cn("p-6", className)}>{children}</div>;
}

interface CardTitleProps {
	children: ReactNode;
	className?: string;
}

export function CardTitle({ children, className }: CardTitleProps) {
	return (
		<h3 className={cn("text-lg font-semibold text-foreground", className)}>
			{children}
		</h3>
	);
}

interface CardDescriptionProps {
	children: ReactNode;
	className?: string;
}

export function CardDescription({ children, className }: CardDescriptionProps) {
	return (
		<p className={cn("text-sm text-muted-foreground", className)}>{children}</p>
	);
}

interface CardContentProps {
	children: ReactNode;
	className?: string;
}

export function CardContent({ children, className }: CardContentProps) {
	return <div className={cn("p-6 pt-0", className)}>{children}</div>;
}

interface CardFooterProps {
	children: ReactNode;
	className?: string;
}

export function CardFooter({ children, className }: CardFooterProps) {
	return <div className={cn("p-6 pt-0", className)}>{children}</div>;
}

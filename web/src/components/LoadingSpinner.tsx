interface LoadingSpinnerProps {
	size?: "sm" | "md" | "lg";
	className?: string;
}

export function LoadingSpinner({
	size = "md",
	className = "",
}: LoadingSpinnerProps) {
	const sizeClasses: Record<
		NonNullable<LoadingSpinnerProps["size"]>,
		string
	> = {
		sm: "w-4 h-4",
		md: "w-8 h-8",
		lg: "w-12 h-12",
	};

	return (
		<div className={`inline-block ${sizeClasses[size]} ${className}`}>
			<div className="w-full h-full border-4 border-border/60 border-t-primary rounded-full animate-spin" />
		</div>
	);
}

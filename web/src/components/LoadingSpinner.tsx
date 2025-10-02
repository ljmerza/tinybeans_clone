interface LoadingSpinnerProps {
	size?: "sm" | "md" | "lg";
	className?: string;
}

export function LoadingSpinner({
	size = "md",
	className = "",
}: LoadingSpinnerProps) {
	const sizeClasses = {
		sm: "w-4 h-4",
		md: "w-8 h-8",
		lg: "w-12 h-12",
	};

	return (
		<div className={`inline-block ${sizeClasses[size]} ${className}`}>
			<div className="w-full h-full border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
		</div>
	);
}

interface LoadingPageProps {
	message?: string;
}

export function LoadingPage({ message = "Loading..." }: LoadingPageProps) {
	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50">
			<div className="text-center">
				<LoadingSpinner size="lg" className="mx-auto mb-4" />
				<p className="text-gray-600">{message}</p>
			</div>
		</div>
	);
}

import type { ReactNode } from "react";
import { LoadingSpinner } from "./LoadingSpinner";

interface LoadingPageProps {
	message?: ReactNode;
	fullScreen?: boolean;
}

export function LoadingPage({
	message = "Loading...",
	fullScreen = true,
}: LoadingPageProps) {
	const containerClasses = fullScreen
		? "min-h-screen w-full flex items-center justify-center bg-gray-50"
		: "w-full flex items-center justify-center bg-gray-50 py-16";

	return (
		<div className={containerClasses}>
			<div className="text-center">
				<LoadingSpinner size="lg" className="mx-auto mb-4" />
				<p className="text-gray-600">{message}</p>
			</div>
		</div>
	);
}

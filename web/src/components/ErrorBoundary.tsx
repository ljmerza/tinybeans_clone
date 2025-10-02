import { Component, type ReactNode } from "react";

interface Props {
	children: ReactNode;
	fallback?: ReactNode;
}

interface State {
	hasError: boolean;
	error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { hasError: false };
	}

	static getDerivedStateFromError(error: Error): State {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
		console.error("ErrorBoundary caught an error:", error, errorInfo);
	}

	render() {
		if (this.state.hasError) {
			if (this.props.fallback) {
				return this.props.fallback;
			}

			return (
				<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
					<div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center">
						<h2 className="text-2xl font-semibold text-red-600 mb-4">
							Something went wrong
						</h2>
						<p className="text-gray-600 mb-4">
							{this.state.error?.message || "An unexpected error occurred"}
						</p>
						<button
							onClick={() => (window.location.href = "/")}
							className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
						>
							Go to Home
						</button>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}

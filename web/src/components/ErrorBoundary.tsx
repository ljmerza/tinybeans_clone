import { Component, type ReactNode } from "react";
import { withTranslation } from "react-i18next";
import type { WithTranslation } from "react-i18next";

interface Props extends WithTranslation {
	children: ReactNode;
	fallback?: ReactNode;
}

interface State {
	hasError: boolean;
	error?: Error;
}

class ErrorBoundaryComponent extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { hasError: false };
	}

	private handleGoHome = () => {
		window.location.assign("/");
	};

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

			const { t } = this.props;

			return (
				<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
					<div className="max-w-md w-full bg-white rounded-lg shadow-md p-6 text-center">
						<h2 className="text-2xl font-semibold text-red-600 mb-4">
							{t('pages.error.something_wrong')}
						</h2>
						<p className="text-gray-600 mb-4">
							{this.state.error?.message || t('pages.error.unexpected_error')}
						</p>
						<button
							type="button"
							onClick={this.handleGoHome}
							className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
						>
							{t('pages.error.go_home')}
						</button>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}

export const ErrorBoundary = withTranslation()(ErrorBoundaryComponent);

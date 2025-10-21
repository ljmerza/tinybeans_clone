import { Button } from "@/components/ui/button";
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
				<div className="min-h-screen flex items-center justify-center bg-background px-4 transition-colors">
					<div className="max-w-md w-full bg-card text-card-foreground rounded-lg shadow-md border border-border p-6 text-center transition-colors">
						<h2 className="text-2xl font-semibold text-destructive mb-4">
							{t("pages.error.something_wrong")}
						</h2>
						<p className="text-muted-foreground mb-4">
							{this.state.error?.message || t("pages.error.unexpected_error")}
						</p>
						<Button type="button" onClick={this.handleGoHome} variant="primary">
							{t("pages.error.go_home")}
						</Button>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}

export const ErrorBoundary = withTranslation()(ErrorBoundaryComponent);

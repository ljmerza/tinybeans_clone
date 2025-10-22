import { Button } from "@/components/ui/button";
import { Layout } from "@/components/Layout";
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
	}; // Uses standardized Layout.Error action

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
				<Layout.Error
					showHeader={false}
					title={t("pages.error.something_wrong")}
					message={this.state.error?.message || t("pages.error.unexpected_error")}
					actionLabel={t("pages.error.go_home")}
					onAction={this.handleGoHome}
				/>
			);
		}

		return this.props.children;
	}
}

export const ErrorBoundary = withTranslation()(ErrorBoundaryComponent);

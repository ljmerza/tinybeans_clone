import { useAuthSession } from "@/features/auth/context/AuthSessionProvider";
import type { ReactElement, ReactNode } from "react";
import { Header } from "./Header";
import { LoadingState } from "./LoadingState";
import { StandardError } from "./StandardError";

interface LayoutProps {
	children?: ReactNode;
	showHeader?: boolean;
}

/**
 * Main layout component with header navigation
 */
function LayoutBase({ children, showHeader = true }: LayoutProps) {
	const session = useAuthSession();

	// Don't show header until auth state is stable to prevent flash
	const shouldShowHeader = showHeader && session.isReady;

	return (
		<div className="min-h-screen bg-background text-foreground transition-colors">
			{/* Subtle loading bar when auth is being determined */}
			{showHeader && !session.isReady && (
				<div className="h-1 bg-muted animate-pulse" />
			)}
			
			{shouldShowHeader && <Header isAuthenticated={session.isAuthenticated} />}

			<main className={shouldShowHeader ? "container-page section-spacing" : ""}>
				{children}
			</main>
		</div>
	);
}

interface LayoutLoadingProps extends Omit<LayoutProps, "children"> {
	message?: ReactNode;
	description?: ReactNode;
	icon?: ReactNode;
	spinnerSize?: "sm" | "md" | "lg";
}

function LayoutLoading({
	showHeader,
	message,
	description,
	icon,
	spinnerSize,
}: LayoutLoadingProps) {
	return (
		<LayoutBase showHeader={showHeader}>
			<LoadingState
				layout="section"
				message={message}
				description={description}
				icon={icon}
				spinnerSize={spinnerSize}
			/>
		</LayoutBase>
	);
}

interface LayoutErrorProps extends Omit<LayoutProps, "children"> {
	title?: ReactNode;
	message?: ReactNode;
	description?: ReactNode;
	actionLabel?: string;
	onAction?: () => void;
	extraContent?: ReactNode;
	icon?: ReactNode;
}

function LayoutError({
	showHeader,
	title,
	message,
	description,
	actionLabel,
	onAction,
	extraContent,
	icon,
}: LayoutErrorProps) {
	return (
		<LayoutBase showHeader={showHeader}>
			<StandardError
				title={title}
				message={message}
				description={description}
				actionLabel={actionLabel}
				onAction={onAction}
				extraContent={extraContent}
				icon={icon}
			/>
		</LayoutBase>
	);
}

type LayoutComponent = ((props: LayoutProps) => ReactElement) & {
	Loading: (props: LayoutLoadingProps) => ReactElement;
	Error: (props: LayoutErrorProps) => ReactElement;
};

const LayoutFn = ((props: LayoutProps) => {
	return <LayoutBase {...props} />;
}) as LayoutComponent;

LayoutFn.Loading = LayoutLoading;
LayoutFn.Error = LayoutError;

export const Layout = LayoutFn;

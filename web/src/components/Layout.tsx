import { authStore } from "@/modules/login/store";
import { Link } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";
import type { ReactNode } from "react";
import { StandardError } from "./StandardError";
import { StandardLoading } from "./StandardLoading";

function AuthenticatedHeaderActions() {
    return (
        <>
            <Link to="/2fa/setup" className="btn-ghost">
                2FA Setup
            </Link>
            <Link to="/logout" className="btn-ghost">
                Logout
            </Link>
        </>
    );
}

function GuestHeaderActions() {
    return (
        <>
            <Link to="/login" className="btn-ghost">
                Login
            </Link>
            <Link to="/signup" className="btn-primary">
                Sign up
            </Link>
        </>
    );
}

interface LayoutProps {
    children?: ReactNode;
    showHeader?: boolean;
}

/**
 * Main layout component with header navigation
 */
function LayoutBase({ children, showHeader = true }: LayoutProps) {
    const { accessToken } = useStore(authStore);

    return (
        <div className="min-h-screen bg-gray-50">
            {showHeader && (
                <header className="bg-white shadow-sm">
                    <div className="container-page">
                        <div className="flex justify-between items-center h-16">
                            <div className="flex items-center">
                                <Link
                                    to="/"
                                    className="text-xl font-bold text-gray-900 hover:text-gray-700"
                                >
                                    Home
                                </Link>
                            </div>
                            <nav className="flex items-center gap-4">
                                {accessToken ? (
                                    <AuthenticatedHeaderActions />
                                ) : (
                                    <GuestHeaderActions />
                                )}
                            </nav>
                        </div>
                    </div>
                </header>
            )}

            <main className={showHeader ? "container-page section-spacing" : ""}>
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
            <StandardLoading
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

type LayoutComponent = ((props: LayoutProps) => JSX.Element) & {
    Loading: (props: LayoutLoadingProps) => JSX.Element;
    Error: (props: LayoutErrorProps) => JSX.Element;
};

const LayoutFn = ((props: LayoutProps) => {
    return <LayoutBase {...props} />;
}) as LayoutComponent;

LayoutFn.Loading = LayoutLoading;
LayoutFn.Error = LayoutError;

export const Layout = LayoutFn;

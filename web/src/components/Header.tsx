/**
 * @fileoverview Shared Header component for application navigation.
 * Displays site branding and navigation links based on authentication state.
 *
 * @module components/Header
 */

import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

interface HeaderProps {
	/** Whether the user is authenticated */
	isAuthenticated: boolean;
}

/**
 * Header actions for authenticated users
 */
function AuthenticatedHeaderActions() {
	const { t } = useTranslation();
	return (
		<>
			<Button asChild variant="ghost" size="sm">
				<Link to="/circles">{t("nav.circles")}</Link>
			</Button>
			<Button asChild variant="ghost" size="sm">
				<Link to="/profile/general">{t("nav.settings")}</Link>
			</Button>
			<Button asChild variant="ghost" size="sm">
				<Link to="/logout">{t("nav.logout")}</Link>
			</Button>
		</>
	);
}

/**
 * Header actions for guest users
 */
function GuestHeaderActions() {
	const { t } = useTranslation();
	return (
		<>
			<Button asChild variant="ghost" size="sm">
				<Link to="/login">{t("nav.login")}</Link>
			</Button>
			<Button asChild variant="primary" size="sm">
				<Link to="/signup">{t("nav.signup")}</Link>
			</Button>
		</>
	);
}

/**
 * Application header with navigation.
 *
 * Displays the site branding (Home link) and authentication-dependent navigation.
 * For authenticated users, shows 2FA Settings and Logout links.
 * For guest users, shows Login and Sign up links.
 *
 * @example
 * ```tsx
 * <Header isAuthenticated={session.isAuthenticated} />
 * ```
 */
export function Header({ isAuthenticated }: HeaderProps) {
	const { t } = useTranslation();
	return (
		<header className="bg-card text-card-foreground border-b border-border shadow-sm transition-colors">
			<div className="container-page">
				<div className="flex justify-between items-center h-16">
					<div className="flex items-center">
						<Link
							to="/"
							className="text-xl font-bold text-foreground hover:text-foreground/80 transition-colors"
						>
							{t("nav.home")}
						</Link>
					</div>
					<nav className="flex items-center gap-2">
						{isAuthenticated ? (
							<AuthenticatedHeaderActions />
						) : (
							<GuestHeaderActions />
						)}
					</nav>
				</div>
			</div>
		</header>
	);
}

/**
 * @fileoverview Shared Header component for application navigation.
 * Displays site branding and navigation links based on authentication state.
 *
 * @module components/Header
 */

import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

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
				<Link to="/calendar">{t("nav.calendar")}</Link>
			</Button>
			<Button asChild variant="ghost" size="sm">
				<Link to="/favorites">{t("nav.favorites")}</Link>
			</Button>
			<Button asChild variant="ghost" size="sm">
				<Link to="/albums">{t("nav.albums")}</Link>
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
				<Link to="/login" preload={false}>
					{t("nav.login")}
				</Link>
			</Button>
			<Button asChild variant="primary" size="sm">
				<Link to="/signup" preload={false}>
					{t("nav.signup")}
				</Link>
			</Button>
		</>
	);
}

/**
 * Application header with navigation.
 *
 * Displays the site branding (a "Circles" link home) and authentication-dependent navigation.
 * For authenticated users, shows Calendar, Favorites, Albums, Settings and
 * Logout links.
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
				<div className="flex justify-between items-center gap-4 h-16">
					<div className="flex shrink-0 items-center">
						<Link
							to="/"
							className="text-xl font-bold text-foreground hover:text-foreground/80 transition-colors"
						>
							{t("nav.brand")}
						</Link>
					</div>
					{/* Scrolls sideways when the links don't fit; py-1 keeps focus rings unclipped. */}
					<nav className="flex min-w-0 items-center gap-2 overflow-x-auto py-1 [scrollbar-width:thin] [&>*]:shrink-0">
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

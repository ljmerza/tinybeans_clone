/**
 * @fileoverview Shared Header component for application navigation.
 * Displays site branding and navigation links based on authentication state.
 *
 * @module components/Header
 */

import { Link } from "@tanstack/react-router";

interface HeaderProps {
	/** Whether the user is authenticated */
	isAuthenticated: boolean;
}

/**
 * Header actions for authenticated users
 */
function AuthenticatedHeaderActions() {
	return (
		<>
				<Link to="/2fa/settings" className="btn-ghost">
					2FA Settings
				</Link>
			<Link to="/logout" className="btn-ghost">
				Logout
			</Link>
		</>
	);
}

/**
 * Header actions for guest users
 */
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
	return (
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

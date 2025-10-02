import { authStore } from "@/modules/login/store";
import { Link } from "@tanstack/react-router";
import { useStore } from "@tanstack/react-store";
import type { ReactNode } from "react";

interface LayoutProps {
	children: ReactNode;
	showHeader?: boolean;
}

/**
 * Main layout component with header navigation
 */
export function Layout({ children, showHeader = true }: LayoutProps) {
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
									<>
										<Link to="/2fa/setup" className="btn-ghost">
											2FA Setup
										</Link>
										<Link to="/logout" className="btn-ghost">
											Logout
										</Link>
									</>
								) : (
									<>
										<Link to="/login" className="btn-ghost">
											Login
										</Link>
										<Link to="/signup" className="btn-primary">
											Sign up
										</Link>
									</>
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

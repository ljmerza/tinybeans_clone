import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { CirclesLogo } from "@/components/CirclesLogo";

interface AuthSplitLayoutProps {
	/** Brand panel content, shown beside the form on large screens. */
	aside: ReactNode;
	title: ReactNode;
	description?: ReactNode;
	/** Small label above the title, e.g. "Action required". */
	eyebrow?: ReactNode;
	/** Decorative icon above the title, usually an IconTile. */
	icon?: ReactNode;
	children: ReactNode;
}

function BrandLink() {
	const { t } = useTranslation();
	return (
		<Link
			to="/"
			aria-label={t("auth.signup.back_home")}
			className="inline-flex items-center gap-2 rounded-md text-xl font-bold text-foreground transition-colors hover:text-foreground/80"
		>
			<CirclesLogo className="size-8" />
			{t("nav.brand")}
		</Link>
	);
}

/**
 * Full-height two-column auth layout: a brand panel on the left and the form
 * on the right. Below `lg` the panel is dropped and the form gets a logo row.
 */
export function AuthSplitLayout({
	aside,
	title,
	description,
	eyebrow,
	icon,
	children,
}: AuthSplitLayoutProps) {
	return (
		<div className="grid min-h-screen bg-background text-foreground transition-colors lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
			<aside className="relative hidden overflow-hidden border-r border-border bg-muted/50 lg:flex lg:flex-col lg:justify-between lg:p-12">
				<div
					aria-hidden
					className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-gradient-to-br from-rose-400/20 via-amber-400/10 to-sky-400/20 blur-3xl"
				/>
				<BrandLink />
				<div className="relative">{aside}</div>
				<div />
			</aside>

			<main className="flex flex-col px-4 py-8 sm:px-6 lg:justify-center lg:px-12">
				<div className="mx-auto mb-8 w-full max-w-md lg:hidden">
					<BrandLink />
				</div>
				<div className="mx-auto w-full max-w-md space-y-6">
					<div className="space-y-2">
						{icon ? <div className="mb-4">{icon}</div> : null}
						{eyebrow ? (
							<p className="text-xs font-semibold uppercase tracking-wide text-primary">
								{eyebrow}
							</p>
						) : null}
						<h1 className="text-3xl font-bold tracking-tight text-foreground">
							{title}
						</h1>
						{description ? (
							<p className="text-muted-foreground">{description}</p>
						) : null}
					</div>
					{children}
				</div>
			</main>
		</div>
	);
}

import { Link } from "@tanstack/react-router";
import {
	Album,
	ArrowRight,
	CalendarDays,
	Camera,
	CirclePlus,
	Images,
	KeyRound,
	Lock,
	type LucideIcon,
	MessageCircle,
	Ruler,
	ShieldCheck,
	UserPlus,
	Users,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { CirclesLogo } from "@/components/CirclesLogo";
import { IconTile, type IconTileTone } from "@/components/IconTile";
import { Button } from "@/components/ui/button";

import { HeroArt } from "./HeroArt";

interface IconItem {
	key: string;
	icon: LucideIcon;
	tone: IconTileTone;
}

const features: IconItem[] = [
	{ key: "circles", icon: Users, tone: "sky" },
	{ key: "media", icon: Images, tone: "rose" },
	{ key: "calendar", icon: CalendarDays, tone: "amber" },
	{ key: "albums", icon: Album, tone: "sky" },
	{ key: "comments", icon: MessageCircle, tone: "rose" },
	{ key: "growth", icon: Ruler, tone: "amber" },
];

const steps: IconItem[] = [
	{ key: "create", icon: CirclePlus, tone: "rose" },
	{ key: "invite", icon: UserPlus, tone: "sky" },
	{ key: "share", icon: Camera, tone: "amber" },
];

const privacyPoints: IconItem[] = [
	{ key: "invite_only", icon: Lock, tone: "sky" },
	{ key: "two_factor", icon: KeyRound, tone: "amber" },
	{ key: "no_ads", icon: ShieldCheck, tone: "rose" },
];

/**
 * Marketing home page shown at "/" to signed-out visitors.
 */
export function LandingPage() {
	const { t } = useTranslation();

	return (
		<div className="space-y-20 sm:space-y-28">
			{/* Hero */}
			<section className="grid items-center gap-12 pt-6 lg:grid-cols-2 lg:pt-12">
				<div className="space-y-6 text-center lg:text-left">
					<span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-sm font-medium text-muted-foreground shadow-xs">
						<ShieldCheck aria-hidden className="size-4 text-sky-500" />
						{t("pages.landing.badge")}
					</span>
					<h1 className="text-4xl font-bold tracking-tight text-foreground text-balance sm:text-5xl lg:text-6xl">
						{t("pages.landing.title")}
					</h1>
					<p className="mx-auto max-w-xl text-lg text-muted-foreground text-pretty lg:mx-0">
						{t("pages.landing.subtitle")}
					</p>
					<div className="flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
						<Button asChild size="lg" iconPosition="right">
							<Link to="/signup">
								<ArrowRight aria-hidden />
								{t("pages.landing.cta_primary")}
							</Link>
						</Button>
						<Button asChild size="lg" variant="outline">
							<Link to="/login">{t("pages.landing.cta_secondary")}</Link>
						</Button>
					</div>
					<p className="flex items-center justify-center gap-2 text-sm text-muted-foreground lg:justify-start">
						<Lock aria-hidden className="size-4" />
						{t("pages.landing.trust_line")}
					</p>
				</div>
				<HeroArt className="max-w-sm lg:max-w-md" />
			</section>

			{/* Features */}
			<section aria-labelledby="landing-features" className="space-y-10">
				<div className="mx-auto max-w-2xl space-y-3 text-center">
					<h2
						id="landing-features"
						className="text-3xl font-bold tracking-tight text-foreground text-balance"
					>
						{t("pages.landing.features_title")}
					</h2>
					<p className="text-lg text-muted-foreground text-pretty">
						{t("pages.landing.features_subtitle")}
					</p>
				</div>
				<ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{features.map((feature) => (
						<li
							key={feature.key}
							className="rounded-xl border border-border bg-card p-6 shadow-xs transition-colors"
						>
							<IconTile icon={feature.icon} tone={feature.tone} />
							<h3 className="mt-4 text-lg font-semibold text-foreground">
								{t(`pages.landing.features.${feature.key}.title`)}
							</h3>
							<p className="mt-2 text-muted-foreground">
								{t(`pages.landing.features.${feature.key}.description`)}
							</p>
						</li>
					))}
				</ul>
			</section>

			{/* How it works */}
			<section aria-labelledby="landing-steps" className="space-y-10">
				<h2
					id="landing-steps"
					className="text-center text-3xl font-bold tracking-tight text-foreground"
				>
					{t("pages.landing.steps_title")}
				</h2>
				<ol className="grid gap-8 md:grid-cols-3">
					{steps.map((step, index) => (
						<li
							key={step.key}
							className="flex flex-col items-center text-center"
						>
							<div className="relative">
								<IconTile icon={step.icon} tone={step.tone} size="lg" />
								<span className="absolute -right-2 -top-2 flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
									{index + 1}
								</span>
							</div>
							<h3 className="mt-5 text-lg font-semibold text-foreground">
								{t(`pages.landing.steps.${step.key}.title`)}
							</h3>
							<p className="mt-2 max-w-xs text-muted-foreground">
								{t(`pages.landing.steps.${step.key}.description`)}
							</p>
						</li>
					))}
				</ol>
			</section>

			{/* Privacy */}
			<section
				aria-labelledby="landing-privacy"
				className="rounded-2xl border border-border bg-muted/50 px-6 py-12 sm:px-12"
			>
				<div className="grid gap-10 lg:grid-cols-[1fr_1.4fr] lg:items-center">
					<div className="space-y-3 text-center lg:text-left">
						<IconTile icon={ShieldCheck} tone="sky" size="lg" />
						<h2
							id="landing-privacy"
							className="text-3xl font-bold tracking-tight text-foreground"
						>
							{t("pages.landing.privacy_title")}
						</h2>
						<p className="text-lg text-muted-foreground text-pretty">
							{t("pages.landing.privacy_subtitle")}
						</p>
					</div>
					<ul className="space-y-6">
						{privacyPoints.map((point) => (
							<li key={point.key} className="flex gap-4">
								<IconTile icon={point.icon} tone={point.tone} />
								<div>
									<h3 className="font-semibold text-foreground">
										{t(`pages.landing.privacy.${point.key}.title`)}
									</h3>
									<p className="mt-1 text-muted-foreground">
										{t(`pages.landing.privacy.${point.key}.description`)}
									</p>
								</div>
							</li>
						))}
					</ul>
				</div>
			</section>

			{/* Closing call to action */}
			<section className="flex flex-col items-center gap-6 text-center">
				<CirclesLogo className="size-16" />
				<h2 className="text-3xl font-bold tracking-tight text-foreground text-balance">
					{t("pages.landing.final_title")}
				</h2>
				<p className="max-w-xl text-lg text-muted-foreground text-pretty">
					{t("pages.landing.final_subtitle")}
				</p>
				<Button asChild size="lg" iconPosition="right">
					<Link to="/signup">
						<ArrowRight aria-hidden />
						{t("pages.landing.cta_primary")}
					</Link>
				</Button>
			</section>

			<footer className="flex flex-col items-center justify-between gap-4 border-t border-border pt-8 text-sm text-muted-foreground sm:flex-row">
				<div className="flex items-center gap-2">
					<CirclesLogo className="size-5" />
					<span className="font-semibold text-foreground">
						{t("nav.brand")}
					</span>
					<span>· {t("pages.landing.footer_tagline")}</span>
				</div>
				<nav className="flex gap-4">
					<Link to="/login" className="hover:text-foreground transition-colors">
						{t("nav.login")}
					</Link>
					<Link
						to="/signup"
						className="hover:text-foreground transition-colors"
					>
						{t("nav.signup")}
					</Link>
				</nav>
			</footer>
		</div>
	);
}

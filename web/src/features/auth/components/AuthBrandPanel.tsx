import {
	Album,
	BellRing,
	CalendarDays,
	Images,
	KeyRound,
	Lock,
	type LucideIcon,
	ShieldCheck,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { IconTile, type IconTileTone } from "@/components/IconTile";
import { cn } from "@/lib/utils";

export interface BrandPoint {
	/** i18n key for the point's text. */
	key: string;
	icon: LucideIcon;
	tone: IconTileTone;
}

export const signupPoints: BrandPoint[] = [
	{ key: "auth.signup.panel_points.private", icon: Lock, tone: "sky" },
	{ key: "auth.signup.panel_points.media", icon: Images, tone: "rose" },
	{ key: "auth.signup.panel_points.notify", icon: BellRing, tone: "amber" },
];

const loginPoints: BrandPoint[] = [
	{ key: "auth.panels.login.points.media", icon: Images, tone: "rose" },
	{
		key: "auth.panels.login.points.calendar",
		icon: CalendarDays,
		tone: "amber",
	},
	{ key: "auth.panels.login.points.albums", icon: Album, tone: "sky" },
];

const securePoints: BrandPoint[] = [
	{ key: "auth.panels.secure.points.invite_only", icon: Lock, tone: "sky" },
	{
		key: "auth.panels.secure.points.two_factor",
		icon: KeyRound,
		tone: "amber",
	},
	{ key: "auth.panels.secure.points.no_ads", icon: ShieldCheck, tone: "rose" },
];

interface BrandPointListProps {
	points: BrandPoint[];
	/** "lg" for the brand panel, "sm" for the compact mobile list. */
	size?: "sm" | "lg";
	className?: string;
}

export function BrandPointList({
	points,
	size = "lg",
	className,
}: BrandPointListProps) {
	const { t } = useTranslation();
	return (
		<ul className={cn(size === "lg" ? "space-y-4" : "space-y-3", className)}>
			{points.map((point) => (
				<li
					key={point.key}
					className={cn(
						"flex items-center",
						size === "lg" ? "gap-4" : "gap-3 text-sm",
					)}
				>
					<IconTile
						icon={point.icon}
						tone={point.tone}
						size={size === "lg" ? "md" : "sm"}
					/>
					<span
						className={
							size === "lg" ? "text-foreground" : "text-muted-foreground"
						}
					>
						{t(point.key)}
					</span>
				</li>
			))}
		</ul>
	);
}

interface AuthBrandPanelProps {
	title: string;
	subtitle: string;
	points: BrandPoint[];
}

/**
 * Heading, subtitle and icon points for the AuthSplitLayout brand panel.
 */
export function AuthBrandPanel({
	title,
	subtitle,
	points,
}: AuthBrandPanelProps) {
	return (
		<div className="max-w-md space-y-8">
			<div className="space-y-3">
				<h2 className="text-3xl font-bold tracking-tight text-foreground text-balance">
					{title}
				</h2>
				<p className="text-lg text-muted-foreground text-pretty">{subtitle}</p>
			</div>
			<BrandPointList points={points} />
		</div>
	);
}

export function SignupBrandPanel() {
	const { t } = useTranslation();
	return (
		<AuthBrandPanel
			title={t("auth.signup.panel_title")}
			subtitle={t("auth.signup.panel_subtitle")}
			points={signupPoints}
		/>
	);
}

export function LoginBrandPanel() {
	const { t } = useTranslation();
	return (
		<AuthBrandPanel
			title={t("auth.panels.login.title")}
			subtitle={t("auth.panels.login.subtitle")}
			points={loginPoints}
		/>
	);
}

/** For the secondary auth screens: magic link, resets, 2FA, email checks. */
export function SecureBrandPanel() {
	const { t } = useTranslation();
	return (
		<AuthBrandPanel
			title={t("auth.panels.secure.title")}
			subtitle={t("auth.panels.secure.subtitle")}
			points={securePoints}
		/>
	);
}

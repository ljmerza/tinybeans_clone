import {
	BellRing,
	CalendarDays,
	Camera,
	Heart,
	type LucideIcon,
	MessageCircle,
	Star,
	Users,
} from "lucide-react";

import { CirclesLogo } from "@/components/CirclesLogo";
import { IconTile, type IconTileTone } from "@/components/IconTile";
import { cn } from "@/lib/utils";

interface FloatingTile {
	icon: LucideIcon;
	tone: IconTileTone;
	/** Position and tilt inside the square art area. */
	className: string;
}

const tiles: FloatingTile[] = [
	{ icon: Camera, tone: "rose", className: "left-[4%] top-[10%] -rotate-6" },
	{
		icon: CalendarDays,
		tone: "amber",
		className: "right-[6%] top-[4%] rotate-6",
	},
	{
		icon: MessageCircle,
		tone: "sky",
		className: "right-0 top-[46%] -rotate-3",
	},
	{ icon: Star, tone: "amber", className: "bottom-[4%] right-[18%] rotate-3" },
	{ icon: Users, tone: "sky", className: "bottom-[10%] left-[2%] rotate-6" },
	{ icon: Heart, tone: "rose", className: "left-[-2%] top-[50%] -rotate-12" },
	{ icon: BellRing, tone: "rose", className: "left-[44%] top-[-2%] rotate-3" },
];

/**
 * Decorative hero illustration: the logo rings ringed by feature icons.
 */
export function HeroArt({ className }: { className?: string }) {
	return (
		<div
			aria-hidden
			className={cn(
				"relative mx-auto aspect-square w-full max-w-md",
				className,
			)}
		>
			<div className="absolute inset-[12%] rounded-full bg-gradient-to-br from-rose-400/15 via-amber-400/10 to-sky-400/15 blur-2xl" />
			<div className="absolute inset-[16%] rounded-full border border-border/70 bg-card/60 shadow-sm" />
			<div className="absolute inset-[24%]">
				<CirclesLogo className="size-full" />
			</div>
			{tiles.map((tile) => (
				<div
					key={tile.className}
					className={cn(
						"absolute rounded-2xl border border-border bg-card p-1.5 shadow-md",
						tile.className,
					)}
				>
					<IconTile icon={tile.icon} tone={tile.tone} size="lg" />
				</div>
			))}
		</div>
	);
}

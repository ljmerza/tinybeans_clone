import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** The three logo ring colors. */
export type IconTileTone = "rose" | "sky" | "amber";

const toneClasses: Record<IconTileTone, string> = {
	rose: "bg-rose-400/15 text-rose-600 dark:bg-rose-400/20 dark:text-rose-300",
	sky: "bg-sky-400/15 text-sky-700 dark:bg-sky-400/20 dark:text-sky-300",
	amber:
		"bg-amber-400/20 text-amber-700 dark:bg-amber-400/20 dark:text-amber-300",
};

const sizeClasses = {
	sm: "size-9 rounded-lg [&>svg]:size-4",
	md: "size-11 rounded-xl [&>svg]:size-5",
	lg: "size-14 rounded-2xl [&>svg]:size-7",
};

interface IconTileProps {
	icon: LucideIcon;
	tone: IconTileTone;
	size?: keyof typeof sizeClasses;
	className?: string;
}

/**
 * A decorative icon on a soft square tinted with one of the logo colors.
 */
export function IconTile({
	icon: Icon,
	tone,
	size = "md",
	className,
}: IconTileProps) {
	return (
		<span
			aria-hidden
			className={cn(
				"inline-flex shrink-0 items-center justify-center",
				toneClasses[tone],
				sizeClasses[size],
				className,
			)}
		>
			<Icon />
		</span>
	);
}

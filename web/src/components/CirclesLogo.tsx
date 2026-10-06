import { cn } from "@/lib/utils";

interface CirclesLogoProps {
	className?: string;
	/** Accessible name; omit to mark the logo as decorative. */
	title?: string;
}

/**
 * The Circles mark: three overlapping rings, matching the PWA icon.
 */
export function CirclesLogo({ className, title }: CirclesLogoProps) {
	return (
		<svg
			viewBox="0 0 512 512"
			fill="none"
			strokeWidth={26}
			className={cn("size-8 shrink-0", className)}
			role={title ? "img" : undefined}
			aria-label={title}
			aria-hidden={title ? undefined : true}
		>
			<circle cx="255.5" cy="185" r="110" className="stroke-rose-400" />
			<circle cx="174" cy="326" r="110" className="stroke-sky-400" />
			<circle cx="337" cy="326" r="110" className="stroke-amber-400" />
		</svg>
	);
}

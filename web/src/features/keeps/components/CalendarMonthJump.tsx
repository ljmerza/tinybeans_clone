import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

/** Month keys are `YYYY-MM`. Returns the key `delta` months away. */
export function shiftMonthKey(monthKey: string, delta: number) {
	const [year, month] = monthKey.split("-").map(Number);
	const date = new Date(Date.UTC(year, month - 1 + delta, 1));
	return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

function monthKeyOf(year: number, monthIndex: number) {
	return `${year}-${String(monthIndex + 1).padStart(2, "0")}`;
}

function yearOf(monthKey: string) {
	return Number(monthKey.slice(0, 4));
}

interface CalendarMonthJumpProps {
	/** The month the calendar shows (`YYYY-MM`). */
	monthKey: string;
	/** Earliest month that can be picked. */
	minMonthKey: string;
	/** Latest month that can be picked; also the "Today" target. */
	maxMonthKey: string;
	onSelect: (monthKey: string) => void;
	className?: string;
}

/**
 * A button showing the calendar's month that opens a year + month picker, so
 * any month is a couple of taps away instead of a long scroll.
 */
export function CalendarMonthJump({
	monthKey,
	minMonthKey,
	maxMonthKey,
	onSelect,
	className,
}: CalendarMonthJumpProps) {
	const { t, i18n } = useTranslation();
	const locale = i18n.language;
	const [open, setOpen] = useState(false);
	const [viewYear, setViewYear] = useState(() => yearOf(monthKey));

	const { monthNames, formatMonth } = useMemo(() => {
		const short = new Intl.DateTimeFormat(locale, {
			month: "short",
			timeZone: "UTC",
		});
		const long = new Intl.DateTimeFormat(locale, {
			month: "long",
			year: "numeric",
			timeZone: "UTC",
		});
		return {
			monthNames: Array.from({ length: 12 }, (_, index) =>
				short.format(Date.UTC(2000, index, 1)),
			),
			formatMonth: (key: string) =>
				long.format(Date.UTC(yearOf(key), Number(key.slice(5, 7)) - 1, 1)),
		};
	}, [locale]);

	const minYear = yearOf(minMonthKey);
	const maxYear = yearOf(maxMonthKey);
	const monthLabel = formatMonth(monthKey);

	const choose = (nextMonthKey: string) => {
		setOpen(false);
		if (nextMonthKey !== monthKey) onSelect(nextMonthKey);
	};

	return (
		<Dialog
			open={open}
			onOpenChange={(nextOpen) => {
				// Open on the year being viewed, not wherever the picker was left.
				if (nextOpen) setViewYear(yearOf(monthKey));
				setOpen(nextOpen);
			}}
		>
			<DialogTrigger asChild>
				<Button
					variant="outline"
					size="sm"
					className={className}
					aria-label={t("pages.calendar.jump_to_month_current", {
						month: monthLabel,
					})}
				>
					<CalendarDays aria-hidden="true" />
					{monthLabel}
				</Button>
			</DialogTrigger>
			<DialogContent
				className="max-w-xs rounded-lg"
				closeButtonLabel={t("common.close")}
				aria-describedby={undefined}
			>
				<DialogTitle>{t("pages.calendar.jump_to_month")}</DialogTitle>
				<div className="flex items-center justify-between">
					<Button
						variant="ghost"
						size="icon"
						aria-label={t("pages.calendar.previous_year")}
						disabled={viewYear <= minYear}
						onClick={() => setViewYear((year) => year - 1)}
					>
						<ChevronLeft aria-hidden="true" />
					</Button>
					<span
						className="text-lg font-semibold tabular-nums"
						aria-live="polite"
					>
						{viewYear}
					</span>
					<Button
						variant="ghost"
						size="icon"
						aria-label={t("pages.calendar.next_year")}
						disabled={viewYear >= maxYear}
						onClick={() => setViewYear((year) => year + 1)}
					>
						<ChevronRight aria-hidden="true" />
					</Button>
				</div>
				<div className="grid grid-cols-3 gap-2">
					{monthNames.map((name, index) => {
						const key = monthKeyOf(viewYear, index);
						const isCurrent = key === monthKey;
						return (
							<Button
								key={key}
								variant={isCurrent ? "primary" : "outline"}
								size="sm"
								aria-label={formatMonth(key)}
								aria-pressed={isCurrent}
								disabled={key < minMonthKey || key > maxMonthKey}
								onClick={() => choose(key)}
								className="capitalize"
							>
								{name}
							</Button>
						);
					})}
				</div>
				<Button
					variant="secondary"
					size="sm"
					onClick={() => choose(maxMonthKey)}
				>
					{t("pages.calendar.jump_today")}
				</Button>
			</DialogContent>
		</Dialog>
	);
}

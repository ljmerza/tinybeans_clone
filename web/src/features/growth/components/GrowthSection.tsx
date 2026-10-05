import { LoadingState } from "@/components";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useDeleteMeasurement, useGrowthLog } from "../hooks/useGrowth";
import { useMeasurementUnits } from "../hooks/useMeasurementUnits";
import type { GrowthMeasurement } from "../types";
import { ageInMonths, dayToUtcMs, formatDay } from "../utils/dates";
import {
	type MeasurementUnits,
	cmToInches,
	formatChartValue,
	formatHeight,
	formatWeight,
	kgToPounds,
} from "../utils/units";
import { MeasurementFormDialog } from "./MeasurementFormDialog";
import { MeasurementUnitsToggle } from "./MeasurementUnitsToggle";
import { type ChartPoint, LineChart } from "./charts";

type Measure = "height" | "weight";

/** "5 mo" under two years, else "2.5 y". */
function useFormatAge() {
	const { t } = useTranslation();
	return (months: number) =>
		months < 24
			? t("pages.people.growth.age.months", {
					count: Math.max(0, Math.floor(months)),
				})
			: t("pages.people.growth.age.years", {
					count: Math.floor((months / 12) * 10) / 10,
				});
}

function chartPoints(
	measurements: GrowthMeasurement[],
	measure: Measure,
	units: MeasurementUnits,
	birthdate: string | null,
	describe: (measurement: GrowthMeasurement, value: string) => string,
	locale: string,
): ChartPoint[] {
	const points: ChartPoint[] = [];
	for (const measurement of measurements) {
		const raw =
			measure === "height" ? measurement.height_cm : measurement.weight_kg;
		if (raw === null) continue;
		const y =
			units === "metric"
				? raw
				: measure === "height"
					? cmToInches(raw)
					: kgToPounds(raw);
		const value =
			measure === "height"
				? formatHeight(raw, units, locale)
				: formatWeight(raw, units, locale);
		points.push({
			x: birthdate
				? ageInMonths(birthdate, measurement.measured_on)
				: dayToUtcMs(measurement.measured_on),
			y,
			label: describe(measurement, value),
		});
	}
	return points;
}

export interface GrowthSectionProps {
	personId: string;
	name: string;
}

/**
 * A child's height and weight: a chart of each (against age when the
 * birthdate is known, else the date), a units switch, and the measurements
 * with add/edit/delete for circle admins.
 */
export function GrowthSection({ personId, name }: GrowthSectionProps) {
	const { t, i18n } = useTranslation();
	const locale = i18n.resolvedLanguage ?? "en";
	const formatAge = useFormatAge();
	const { units } = useMeasurementUnits();
	const { data: log, isLoading, error, refetch } = useGrowthLog(personId);
	const remove = useDeleteMeasurement(personId);
	const [formOpen, setFormOpen] = useState(false);
	const [editing, setEditing] = useState<GrowthMeasurement | undefined>();
	const [deleting, setDeleting] = useState<GrowthMeasurement | null>(null);

	const birthdate = log?.birthdate ?? null;
	const measurements = log?.measurements ?? [];
	const canEdit = log?.can_edit ?? false;

	const ageAt = (day: string) =>
		birthdate ? formatAge(ageInMonths(birthdate, day)) : null;
	const describe = (measurement: GrowthMeasurement, value: string) => {
		const age = ageAt(measurement.measured_on);
		const date = formatDay(measurement.measured_on, locale);
		return `${age ? `${age} (${date})` : date}: ${value}`;
	};
	const formatX = (x: number) =>
		birthdate ? formatAge(x) : formatDay(x, locale);
	const chartUnit = {
		height: units === "metric" ? "cm" : "in",
		weight: units === "metric" ? "kg" : "lb",
	} as const;

	const openForm = (measurement?: GrowthMeasurement) => {
		setEditing(measurement);
		setFormOpen(true);
	};

	const confirmDelete = async () => {
		if (!deleting) return;
		try {
			await remove.mutateAsync(deleting.id);
			setDeleting(null);
		} catch {
			// The mutation's error toast explains it; keep the dialog open to retry.
		}
	};

	const chart = (measure: Measure) => (
		<LineChart
			points={chartPoints(
				measurements,
				measure,
				units,
				birthdate,
				describe,
				locale,
			)}
			formatX={formatX}
			formatY={(y) => formatChartValue(y, chartUnit[measure], locale)}
			ariaLabel={t(`pages.people.growth.chart_label_${measure}`, { name })}
			emptyMessage={t(`pages.people.growth.chart_empty_${measure}`)}
		/>
	);

	return (
		<section
			aria-labelledby={`growth-${personId}`}
			className="space-y-3 rounded-lg border border-border bg-card p-4 text-card-foreground"
		>
			<div className="flex flex-wrap items-center gap-2">
				<h2
					id={`growth-${personId}`}
					className="mr-auto text-base font-semibold"
				>
					{t("pages.people.growth.title")}
				</h2>
				<MeasurementUnitsToggle />
				{canEdit && (
					<Button size="sm" variant="outline" onClick={() => openForm()}>
						<Plus className="size-4" aria-hidden="true" />
						{t("pages.people.growth.add")}
					</Button>
				)}
			</div>

			{isLoading ? (
				<LoadingState
					layout="inline"
					spinnerSize="sm"
					className="justify-center py-6 text-sm text-muted-foreground"
					message={t("pages.people.growth.loading")}
				/>
			) : error || !log ? (
				<div className="space-y-3 py-4 text-center">
					<p className="text-sm text-muted-foreground">
						{t("pages.people.growth.error")}
					</p>
					<Button variant="outline" size="sm" onClick={() => refetch()}>
						{t("pages.feed.retry")}
					</Button>
				</div>
			) : (
				<>
					<Tabs defaultValue="weight">
						<TabsList>
							<TabsTrigger value="weight">
								{t("pages.people.growth.weight")}
							</TabsTrigger>
							<TabsTrigger value="height">
								{t("pages.people.growth.height")}
							</TabsTrigger>
						</TabsList>
						<TabsContent value="weight" className="pt-2">
							{chart("weight")}
						</TabsContent>
						<TabsContent value="height" className="pt-2">
							{chart("height")}
						</TabsContent>
					</Tabs>

					{measurements.length === 0 ? (
						<p className="text-center text-sm text-muted-foreground">
							{canEdit
								? t("pages.people.growth.empty_admin")
								: t("pages.people.growth.empty")}
						</p>
					) : (
						<ul
							aria-label={t("pages.people.growth.list_label")}
							className="divide-y divide-border text-sm"
						>
							{/* Newest first: the latest reading is usually the one wanted. */}
							{[...measurements].reverse().map((measurement) => {
								const date = formatDay(measurement.measured_on, locale);
								const age = ageAt(measurement.measured_on);
								return (
									<li
										key={measurement.id}
										className="flex items-center gap-3 py-2"
									>
										<div className="min-w-0 flex-1">
											<p className="font-medium">
												{date}
												{age && (
													<span className="font-normal text-muted-foreground">
														{" "}
														· {age}
													</span>
												)}
											</p>
											<p className="text-muted-foreground">
												{[
													measurement.height_cm !== null &&
														formatHeight(measurement.height_cm, units, locale),
													measurement.weight_kg !== null &&
														formatWeight(measurement.weight_kg, units, locale),
												]
													.filter(Boolean)
													.join(" · ")}
											</p>
											{measurement.note && (
												<p className="truncate text-xs text-muted-foreground">
													{measurement.note}
												</p>
											)}
										</div>
										{canEdit && (
											<div className="flex shrink-0 gap-1">
												<Button
													size="icon"
													variant="ghost"
													aria-label={t("pages.people.growth.edit", { date })}
													title={t("pages.people.growth.edit", { date })}
													onClick={() => openForm(measurement)}
												>
													<Pencil className="size-4" aria-hidden="true" />
												</Button>
												<Button
													size="icon"
													variant="ghost"
													aria-label={t("pages.people.growth.delete.action", {
														date,
													})}
													title={t("pages.people.growth.delete.action", {
														date,
													})}
													onClick={() => setDeleting(measurement)}
												>
													<Trash2 className="size-4" aria-hidden="true" />
												</Button>
											</div>
										)}
									</li>
								);
							})}
						</ul>
					)}
				</>
			)}

			{formOpen && (
				<MeasurementFormDialog
					personId={personId}
					units={units}
					open={formOpen}
					onOpenChange={setFormOpen}
					measurement={editing}
					birthdate={birthdate}
				/>
			)}
			<ConfirmDialog
				open={deleting !== null}
				onOpenChange={(open) => {
					if (!open) setDeleting(null);
				}}
				title={t("pages.people.growth.delete.title")}
				description={
					deleting
						? t("pages.people.growth.delete.description", {
								date: formatDay(deleting.measured_on, locale),
							})
						: undefined
				}
				confirmLabel={t("pages.people.growth.delete.confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={remove.isPending}
				onConfirm={confirmDelete}
			/>
		</section>
	);
}

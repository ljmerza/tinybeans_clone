import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateMeasurement, useUpdateMeasurement } from "../hooks/useGrowth";
import type { GrowthMeasurement, GrowthMeasurementInput } from "../types";
import { localToday } from "../utils/dates";
import {
	type MeasurementUnits,
	type QuantityFields,
	fieldsToHeightCm,
	fieldsToWeightKg,
	heightToFields,
	sameFields,
	weightToFields,
} from "../utils/units";

/** Matches the backend's `GrowthMeasurement.note` max_length. */
const NOTE_MAX_LENGTH = 200;

export interface MeasurementFormDialogProps {
	personId: string;
	units: MeasurementUnits;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	/** Edit this measurement; omit to add one. */
	measurement?: GrowthMeasurement;
	/** `YYYY-MM-DD`; dates before it can't be picked. */
	birthdate?: string | null;
}

interface QuantityInputProps {
	id: string;
	label: string;
	units: MeasurementUnits;
	/** Unit names: [imperial major, imperial minor, metric]. */
	unitLabels: [string, string, string];
	value: QuantityFields;
	onChange: (value: QuantityFields) => void;
}

/** ft + in / lb + oz in imperial, a single cm / kg field in metric. */
function QuantityInput({
	id,
	label,
	units,
	unitLabels,
	value,
	onChange,
}: QuantityInputProps) {
	const field = (part: keyof QuantityFields, unit: string, inputId: string) => (
		<div className="flex items-center gap-1.5">
			<Input
				id={inputId}
				inputMode="decimal"
				autoComplete="off"
				className="w-20"
				value={value[part]}
				aria-label={`${label} (${unit})`}
				onChange={(event) => onChange({ ...value, [part]: event.target.value })}
			/>
			<span className="text-sm text-muted-foreground">{unit}</span>
		</div>
	);

	return (
		<fieldset className="space-y-1.5">
			<legend className="text-sm font-medium">{label}</legend>
			<div className="flex flex-wrap items-center gap-3">
				{units === "imperial" ? (
					<>
						{field("major", unitLabels[0], id)}
						{field("minor", unitLabels[1], `${id}-minor`)}
					</>
				) : (
					field("major", unitLabels[2], id)
				)}
			</div>
		</fieldset>
	);
}

/**
 * Add a measurement, or change one. Entered in the viewer's units and sent in
 * cm/kg. When editing, a height or weight left as shown is not sent, so the
 * stored value isn't re-rounded through the display units.
 * Mount it only while open, so each opening starts fresh.
 */
export function MeasurementFormDialog({
	personId,
	units,
	open,
	onOpenChange,
	measurement,
	birthdate,
}: MeasurementFormDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const editing = measurement !== undefined;
	const create = useCreateMeasurement(personId);
	const update = useUpdateMeasurement(personId);
	const saving = create.isPending || update.isPending;

	const [initialHeight] = useState(() =>
		heightToFields(measurement?.height_cm ?? null, units),
	);
	const [initialWeight] = useState(() =>
		weightToFields(measurement?.weight_kg ?? null, units),
	);
	const [measuredOn, setMeasuredOn] = useState(
		measurement?.measured_on ?? localToday(),
	);
	const [height, setHeight] = useState(initialHeight);
	const [weight, setWeight] = useState(initialWeight);
	const [note, setNote] = useState(measurement?.note ?? "");
	const [error, setError] = useState<string | null>(null);

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		if (saving) return;
		const heightCm = fieldsToHeightCm(height, units);
		const weightKg = fieldsToWeightKg(weight, units);
		if (Number.isNaN(heightCm) || Number.isNaN(weightKg)) {
			setError(t("pages.people.growth.form.invalid_number"));
			return;
		}
		if (heightCm === null && weightKg === null) {
			setError(t("pages.people.growth.form.need_value"));
			return;
		}
		if (!measuredOn) {
			setError(t("pages.people.growth.form.need_date"));
			return;
		}
		setError(null);

		try {
			if (editing) {
				const input: Partial<GrowthMeasurementInput> = {};
				if (measuredOn !== measurement.measured_on) {
					input.measured_on = measuredOn;
				}
				if (!sameFields(height, initialHeight)) input.height_cm = heightCm;
				if (!sameFields(weight, initialWeight)) input.weight_kg = weightKg;
				if (note.trim() !== measurement.note) input.note = note.trim();
				if (Object.keys(input).length > 0) {
					await update.mutateAsync({ measurementId: measurement.id, input });
				}
			} else {
				await create.mutateAsync({
					measured_on: measuredOn,
					height_cm: heightCm,
					weight_kg: weightKg,
					note: note.trim(),
				});
			}
			onOpenChange(false);
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent
				className="max-w-md"
				aria-describedby={undefined}
				closeButtonLabel={t("common.close")}
			>
				<DialogHeader>
					<DialogTitle>
						{editing
							? t("pages.people.growth.form.edit_title")
							: t("pages.people.growth.form.add_title")}
					</DialogTitle>
				</DialogHeader>
				<form className="space-y-4" onSubmit={handleSubmit} noValidate>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-date`}>
							{t("pages.people.growth.form.date")}
						</Label>
						<Input
							id={`${ids}-date`}
							type="date"
							className="w-44"
							value={measuredOn}
							min={birthdate ?? undefined}
							max={localToday()}
							onChange={(event) => setMeasuredOn(event.target.value)}
						/>
					</div>
					<QuantityInput
						id={`${ids}-height`}
						label={t("pages.people.growth.form.height")}
						units={units}
						unitLabels={["ft", "in", "cm"]}
						value={height}
						onChange={setHeight}
					/>
					<QuantityInput
						id={`${ids}-weight`}
						label={t("pages.people.growth.form.weight")}
						units={units}
						unitLabels={["lb", "oz", "kg"]}
						value={weight}
						onChange={setWeight}
					/>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-note`}>
							{t("pages.people.growth.form.note")}
						</Label>
						<Input
							id={`${ids}-note`}
							value={note}
							maxLength={NOTE_MAX_LENGTH}
							placeholder={t("pages.people.growth.form.note_placeholder")}
							onChange={(event) => setNote(event.target.value)}
						/>
					</div>
					{error && (
						<p role="alert" className="text-sm text-destructive">
							{error}
						</p>
					)}
					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="ghost"
							onClick={() => onOpenChange(false)}
						>
							{t("common.cancel")}
						</Button>
						<Button type="submit" disabled={saving}>
							{saving
								? t("pages.people.growth.form.saving")
								: t("pages.people.growth.form.save")}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

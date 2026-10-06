import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApiMessages } from "@/i18n";
import { circleNameSchema } from "@/lib/validations/schemas/circle";
import type { ApiError } from "@/types";
import { useNavigate } from "@tanstack/react-router";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateCircleMutation } from "../hooks/useCircleOnboarding";

interface CreateCircleDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * Name and create another circle, for people who already belong to one.
 * Onboarding covers the first circle; this opens the new one when done.
 */
export function CreateCircleDialog({
	open,
	onOpenChange,
}: CreateCircleDialogProps) {
	const { t } = useTranslation();
	const { getGeneral } = useApiMessages();
	const navigate = useNavigate();
	const id = useId();
	const create = useCreateCircleMutation();
	const [name, setName] = useState("");
	const [error, setError] = useState<string | null>(null);

	const handleOpenChange = (next: boolean) => {
		if (create.isPending) return;
		if (!next) {
			setName("");
			setError(null);
		}
		onOpenChange(next);
	};

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		const parsed = circleNameSchema.safeParse(name);
		if (!parsed.success) {
			setError(t(parsed.error.issues[0]?.message ?? "errors.server_error"));
			return;
		}
		setError(null);
		try {
			const result = await create.mutateAsync({ name: parsed.data });
			const circleId = result.data?.circle?.id;
			onOpenChange(false);
			if (circleId) {
				navigate({
					to: "/circles/$circleId",
					params: { circleId: String(circleId) },
				});
			}
		} catch (caught) {
			const apiError = caught as ApiError;
			const messages = getGeneral(apiError.messages);
			setError(
				messages.length > 0
					? messages.join("\n")
					: (apiError.message ?? t("errors.server_error")),
			);
		}
	};

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogContent closeButtonLabel={t("common.close")}>
				<DialogHeader>
					<DialogTitle>
						{t("pages.circles.index.create_dialog_title")}
					</DialogTitle>
					<DialogDescription>
						{t("pages.circles.index.create_dialog_description")}
					</DialogDescription>
				</DialogHeader>
				<form className="space-y-4" onSubmit={handleSubmit}>
					<div className="space-y-1.5">
						<Label htmlFor={`${id}-name`}>
							{t("pages.circleOnboarding.circleNameLabel")}
						</Label>
						<Input
							id={`${id}-name`}
							value={name}
							onChange={(event) => setName(event.target.value)}
							placeholder={t("pages.circleOnboarding.circleNamePlaceholder")}
							maxLength={255}
							autoComplete="organization"
							aria-invalid={error ? true : undefined}
							aria-describedby={error ? `${id}-error` : undefined}
							disabled={create.isPending}
							required
						/>
						{error && (
							<p id={`${id}-error`} className="text-sm text-destructive">
								{error}
							</p>
						)}
					</div>
					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="ghost"
							onClick={() => handleOpenChange(false)}
							disabled={create.isPending}
						>
							{t("common.cancel")}
						</Button>
						<Button type="submit" isLoading={create.isPending}>
							{create.isPending
								? t("pages.circleOnboarding.creating")
								: t("pages.circleOnboarding.createButton")}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

import { StatusMessage } from "@/components";
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
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import {
	REAUTH_CODE_LENGTH,
	ReauthCodeStep,
	apiErrorMessage,
} from "@/features/auth/reauth";
import type { HttpError } from "@/lib/httpClient";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateApiToken } from "../hooks/useApiTokens";
import { ApiTokenReveal } from "./ApiTokenReveal";

/** Matches the backend's `CircleApiToken.name` max_length. */
const NAME_MAX_LENGTH = 100;
const DAY_MS = 86_400_000;

export type ExpiryChoice = "30" | "90" | "365" | "custom" | "never";
const EXPIRY_CHOICES: ExpiryChoice[] = ["30", "90", "365", "custom", "never"];

/** A day on the viewer's own calendar, as `YYYY-MM-DD`. */
function localDay(date: Date) {
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${date.getFullYear()}-${month}-${day}`;
}

/**
 * The `expires_at` to send: a number of days from now, the end of a chosen
 * day on the viewer's calendar, or null for never.
 */
export function expiresAt(
	choice: ExpiryChoice,
	customDay: string,
	now = new Date(),
): string | null {
	if (choice === "never") return null;
	if (choice === "custom") {
		return new Date(`${customDay}T23:59:59`).toISOString();
	}
	return new Date(now.getTime() + Number(choice) * DAY_MS).toISOString();
}

/** Whether the API refused the re-authentication code itself. */
function isCodeError(error: unknown) {
	return ((error as HttpError | null)?.messages ?? []).some(
		(message) => message.context?.field === "code",
	);
}

export interface CreateApiTokenDialogProps {
	circleId: number | string;
	onOpenChange: (open: boolean) => void;
}

/**
 * Create an API token: name, whether it may suggest milestones and when it
 * expires, then the emailed re-authentication code, then the one-time reveal.
 * Mount it only while open, so each opening starts fresh.
 */
export function CreateApiTokenDialog({
	circleId,
	onOpenChange,
}: CreateApiTokenDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const create = useCreateApiToken(circleId);

	const [step, setStep] = useState<"details" | "code">("details");
	const [name, setName] = useState("");
	const [canSuggest, setCanSuggest] = useState(false);
	const [expiry, setExpiry] = useState<ExpiryChoice>("90");
	const [customDay, setCustomDay] = useState("");
	const [code, setCode] = useState("");
	const [codeError, setCodeError] = useState<string>();
	const [error, setError] = useState<string>();

	if (create.data) {
		return (
			<ApiTokenReveal
				plaintext={create.data.plaintext}
				onDone={() => {
					// Drops the only copy of the plaintext before the dialog goes.
					create.reset();
					onOpenChange(false);
				}}
			/>
		);
	}

	const tomorrow = localDay(new Date(Date.now() + DAY_MS));
	const detailsReady =
		name.trim() !== "" && (expiry !== "custom" || customDay >= tomorrow);

	const submit = (value: string) => {
		if (create.isPending || value.length !== REAUTH_CODE_LENGTH) return;
		setCodeError(undefined);
		setError(undefined);
		create.mutate(
			{
				name: name.trim(),
				can_suggest: canSuggest,
				expires_at: expiresAt(expiry, customDay),
				code: value,
			},
			{
				onError: (failure) => {
					const message = apiErrorMessage(
						failure,
						t,
						"pages.circles.dashboard.api_tokens.create_failed",
					);
					if (isCodeError(failure)) {
						setCode("");
						setCodeError(message);
					} else {
						setError(message);
					}
				},
			},
		);
	};

	return (
		<Dialog
			open
			onOpenChange={(open) => {
				// Never close mid-request: the answer holds the only copy of the token.
				if (!create.isPending) onOpenChange(open);
			}}
		>
			<DialogContent className="max-w-md" closeButtonLabel={t("common.close")}>
				<DialogHeader>
					<DialogTitle>
						{t("pages.circles.dashboard.api_tokens.create.title")}
					</DialogTitle>
					<DialogDescription>
						{step === "details"
							? t("pages.circles.dashboard.api_tokens.create.description")
							: t("pages.circles.dashboard.api_tokens.create.code_description")}
					</DialogDescription>
				</DialogHeader>
				{step === "details" ? (
					<form
						className="space-y-4"
						onSubmit={(event) => {
							event.preventDefault();
							if (detailsReady) setStep("code");
						}}
					>
						<div className="space-y-1.5">
							<Label htmlFor={`${ids}-name`}>
								{t("pages.circles.dashboard.api_tokens.create.name")}
							</Label>
							<Input
								id={`${ids}-name`}
								value={name}
								maxLength={NAME_MAX_LENGTH}
								placeholder={t(
									"pages.circles.dashboard.api_tokens.create.name_placeholder",
								)}
								onChange={(event) => setName(event.target.value)}
								autoFocus
							/>
						</div>
						<label className="flex cursor-pointer items-start gap-3">
							<input
								type="checkbox"
								className="mt-0.5 size-4 shrink-0 accent-primary"
								checked={canSuggest}
								onChange={(event) => setCanSuggest(event.target.checked)}
							/>
							<span className="space-y-0.5">
								<span className="block text-sm font-medium">
									{t("pages.circles.dashboard.api_tokens.create.can_suggest")}
								</span>
								<span className="block text-sm text-muted-foreground">
									{t(
										"pages.circles.dashboard.api_tokens.create.can_suggest_hint",
									)}
								</span>
							</span>
						</label>
						<div className="space-y-1.5">
							<Label htmlFor={`${ids}-expiry`}>
								{t("pages.circles.dashboard.api_tokens.create.expiry")}
							</Label>
							<Select
								value={expiry}
								onValueChange={(value) => setExpiry(value as ExpiryChoice)}
							>
								<SelectTrigger id={`${ids}-expiry`} className="w-full">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{EXPIRY_CHOICES.map((choice) => (
										<SelectItem key={choice} value={choice}>
											{t(
												`pages.circles.dashboard.api_tokens.create.expiry_options.${choice}`,
											)}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
						{expiry === "custom" && (
							<div className="space-y-1.5">
								<Label htmlFor={`${ids}-custom-day`}>
									{t("pages.circles.dashboard.api_tokens.create.expiry_day")}
								</Label>
								<Input
									id={`${ids}-custom-day`}
									type="date"
									className="w-44"
									value={customDay}
									min={tomorrow}
									onChange={(event) => setCustomDay(event.target.value)}
								/>
							</div>
						)}
						<DialogFooter className="gap-2">
							<Button
								type="button"
								variant="ghost"
								onClick={() => onOpenChange(false)}
							>
								{t("common.cancel")}
							</Button>
							<Button type="submit" disabled={!detailsReady}>
								{t("pages.circles.dashboard.api_tokens.create.continue")}
							</Button>
						</DialogFooter>
					</form>
				) : (
					<form
						className="space-y-4"
						onSubmit={(event) => {
							event.preventDefault();
							submit(code);
						}}
					>
						<ReauthCodeStep
							value={code}
							onChange={(value) => {
								setCode(value);
								setCodeError(undefined);
							}}
							onComplete={submit}
							disabled={create.isPending}
							error={codeError}
						/>
						{error && <StatusMessage variant="error">{error}</StatusMessage>}
						<DialogFooter className="gap-2">
							<Button
								type="button"
								variant="ghost"
								disabled={create.isPending}
								onClick={() => {
									setStep("details");
									setCode("");
									setCodeError(undefined);
									setError(undefined);
								}}
							>
								{t("common.back")}
							</Button>
							<Button
								type="submit"
								disabled={
									create.isPending || code.length !== REAUTH_CODE_LENGTH
								}
								isLoading={create.isPending}
							>
								{t("pages.circles.dashboard.api_tokens.create.submit")}
							</Button>
						</DialogFooter>
					</form>
				)}
			</DialogContent>
		</Dialog>
	);
}

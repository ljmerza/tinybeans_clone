import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	FormActions,
	FormField,
} from "@/components";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { useCreateCircleInvitation } from "../hooks/useCircleInvitationAdmin";

const ROLE_OPTIONS = [
	{ value: "member", translationKey: "member" },
	{ value: "admin", translationKey: "admin" },
] as const;

const emailSchema = z
	.string()
	.trim()
	.min(1, "pages.circles.invites.validation.identifier_required")
	.max(255, "pages.circles.invites.validation.identifier_max")
	.email("pages.circles.invites.validation.email_invalid");

type InvitationFormValues = {
	email: string;
	role: (typeof ROLE_OPTIONS)[number]["value"];
};

interface CircleInvitationFormProps {
	circleId: number | string;
}

export function CircleInvitationForm({ circleId }: CircleInvitationFormProps) {
	const { t } = useTranslation();
	const { getFieldErrors, getGeneral } = useApiMessages();
	const createInvitation = useCreateCircleInvitation(circleId);

	const [emailError, setEmailError] = useState<string>("");
	const [generalError, setGeneralError] = useState<string>("");

	const form = useForm<InvitationFormValues>({
		defaultValues: {
			email: "",
			role: "member",
		},
		onSubmit: async ({ value, formApi }) => {
			setEmailError("");
			setGeneralError("");

			const payload = {
				email: value.email.trim(),
				role: value.role,
			};

			try {
				await createInvitation.mutateAsync(payload);
				formApi.reset();
			} catch (error) {
				const apiError = error as ApiError;
				const errors = getFieldErrors(apiError.messages);
				if (errors.email) {
					setEmailError(errors.email);
				}
				const general = getGeneral(apiError.messages);
				if (general.length) {
					setGeneralError(general.join(". "));
				} else if (apiError.message) {
					setGeneralError(apiError.message);
				}
			}
		},
	});

	const isSubmitting = createInvitation.isPending;

	return (
		<Card>
			<CardHeader className="space-y-2">
				<CardTitle>{t("pages.circles.invites.form.title")}</CardTitle>
				<CardDescription>
					{t("pages.circles.invites.form.description_email")}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				<form
					onSubmit={(event) => {
						event.preventDefault();
						event.stopPropagation();
						form.handleSubmit();
					}}
					className="space-y-6"
				>
					<form.Field
						name="email"
						validators={{
							onBlur: zodValidator(emailSchema),
						}}
					>
						{(field) => (
							<FormField
								field={field}
								label={t("pages.circles.invites.form.identifier_label_email")}
								error={emailError}
								helperText={t(
									"pages.circles.invites.form.identifier_help_email",
								)}
							>
								{({ id, field: fieldApi }) => (
									<Input
										id={id}
										type="email"
										value={fieldApi.state.value}
										onChange={(event) => {
											setEmailError("");
											fieldApi.handleChange(event.target.value);
										}}
										onBlur={(event) => {
											fieldApi.handleBlur(event);
										}}
										autoComplete="email"
										disabled={isSubmitting}
										required
									/>
								)}
							</FormField>
						)}
					</form.Field>

					<form.Field name="role">
						{(field) => (
							<FormField
								field={field}
								label={t("pages.circles.invites.form.role_label")}
							>
								{({ field: fieldApi }) => (
									<Select
										value={fieldApi.state.value}
										onValueChange={(value) =>
											fieldApi.handleChange(
												value as InvitationFormValues["role"],
											)
										}
										disabled={isSubmitting}
									>
										<SelectTrigger className="w-full">
											<SelectValue
												placeholder={t(
													"pages.circles.invites.form.role_placeholder",
												)}
											/>
										</SelectTrigger>
										<SelectContent>
											{ROLE_OPTIONS.map((option) => (
												<SelectItem key={option.value} value={option.value}>
													{t(
														`pages.circles.invites.roles.${option.translationKey}`,
													)}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								)}
							</FormField>
						)}
					</form.Field>

					<FormActions
						messages={
							generalError
								? [
										{
											id: "circle-invite-general-error",
											variant: "error" as const,
											content: generalError,
										},
									]
								: undefined
						}
					>
						<Button type="submit" disabled={isSubmitting}>
							{isSubmitting
								? t("pages.circles.invites.form.submitting")
								: t("pages.circles.invites.form.submit")}
						</Button>
					</FormActions>
				</form>
			</CardContent>
		</Card>
	);
}

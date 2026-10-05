import { FormActions, FormField, StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePasswordResetRequest } from "@/features/auth/hooks/authHooks";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import { passwordSchema } from "@/lib/validations/schemas/common";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { useChangePasswordMutation } from "../hooks/useChangePasswordMutation";
import { useUserProfileQuery } from "../hooks/useUserProfile";

type PasswordField = "current_password" | "password" | "password_confirm";

const currentPasswordSchema = z.string().min(1, "validation.password_required");

/**
 * Password section of the profile settings. Accounts that sign in only by
 * email link or Google have no password to confirm, so they get an emailed
 * set-password link instead of the change form.
 */
export function ProfilePasswordSettingsCard() {
	const { t } = useTranslation();
	const profile = useUserProfileQuery();
	const user = profile.data;

	if (!user) {
		return null;
	}

	const hasPassword = user.has_usable_password !== false;

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6">
			<div className="space-y-2">
				<h2 className="text-xl font-semibold">
					{hasPassword
						? t("profile.password.title")
						: t("profile.password.set_title")}
				</h2>
				<p className="text-sm text-muted-foreground">
					{hasPassword
						? t("profile.password.description")
						: t("profile.password.set_description")}
				</p>
			</div>

			{hasPassword ? (
				<ChangePasswordForm />
			) : (
				<SetPasswordByEmail email={user.email} />
			)}
		</div>
	);
}

function ChangePasswordForm() {
	const { t } = useTranslation();
	const changePassword = useChangePasswordMutation();
	const { getFieldErrors, getGeneral } = useApiMessages();
	const [fieldErrors, setFieldErrors] = useState<
		Partial<Record<PasswordField, string>>
	>({});
	const [generalError, setGeneralError] = useState("");

	const form = useForm({
		defaultValues: {
			current_password: "",
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			setFieldErrors({});
			setGeneralError("");

			try {
				await changePassword.mutateAsync(value);
				form.reset();
			} catch (error) {
				const apiError = error as ApiError;
				const fields = getFieldErrors(apiError.messages);
				setFieldErrors(fields);
				const generals = getGeneral(apiError.messages);
				if (generals.length > 0) {
					setGeneralError(generals.join(" "));
				} else if (Object.keys(fields).length === 0) {
					setGeneralError(t("profile.password.failed"));
				}
			}
		},
	});

	const matchesNewPassword = ({
		value,
	}: { value: string }): string | undefined => {
		if (!value) return "validation.password_required";
		return value === form.getFieldValue("password")
			? undefined
			: "validation.passwords_match";
	};

	const validatorsFor = (name: PasswordField) => {
		const validate: (props: { value: string }) => string | undefined =
			name === "password_confirm"
				? matchesNewPassword
				: zodValidator(
						name === "password" ? passwordSchema : currentPasswordSchema,
					);
		return { onBlur: validate, onSubmit: validate };
	};

	const renderPasswordInput = (
		name: PasswordField,
		label: string,
		autoComplete: string,
		helperText?: string,
	) => (
		<form.Field name={name} validators={validatorsFor(name)}>
			{(field) => (
				<FormField
					field={field}
					label={label}
					error={fieldErrors[name]}
					helperText={helperText}
				>
					{({ id, field: fieldApi }) => (
						<Input
							id={id}
							type="password"
							autoComplete={autoComplete}
							value={fieldApi.state.value}
							onChange={(event) => {
								fieldApi.handleChange(event.target.value);
								if (fieldErrors[name]) {
									setFieldErrors((previous) => ({
										...previous,
										[name]: undefined,
									}));
								}
							}}
							onBlur={fieldApi.handleBlur}
							disabled={changePassword.isPending}
							required
						/>
					)}
				</FormField>
			)}
		</form.Field>
	);

	return (
		<form
			noValidate
			onSubmit={(event) => {
				event.preventDefault();
				event.stopPropagation();
				form.handleSubmit();
			}}
			className="space-y-4"
		>
			{renderPasswordInput(
				"current_password",
				t("profile.password.current_password"),
				"current-password",
			)}
			{renderPasswordInput(
				"password",
				t("profile.password.new_password"),
				"new-password",
				t("profile.password.new_password_help"),
			)}
			{renderPasswordInput(
				"password_confirm",
				t("profile.password.confirm_password"),
				"new-password",
			)}

			<FormActions
				messages={[
					{
						id: "change-password-error",
						variant: "error" as const,
						content: generalError,
					},
				]}
			>
				<Button type="submit" disabled={changePassword.isPending}>
					{changePassword.isPending
						? t("profile.password.submitting")
						: t("profile.password.submit")}
				</Button>
			</FormActions>
		</form>
	);
}

function SetPasswordByEmail({ email }: { email: string }) {
	const { t } = useTranslation();
	const resetRequest = usePasswordResetRequest();
	const { translate } = useApiMessages();
	const [errorMessage, setErrorMessage] = useState("");

	const sendLink = async () => {
		setErrorMessage("");
		try {
			await resetRequest.mutateAsync({ email });
		} catch (error) {
			const messages = translate((error as ApiError).messages);
			setErrorMessage(
				messages.length > 0
					? messages.join(" ")
					: t("profile.password.link_failed"),
			);
		}
	};

	return (
		<div className="space-y-4">
			{resetRequest.isSuccess ? (
				<StatusMessage variant="success">
					{t("profile.password.link_sent", { email })}
				</StatusMessage>
			) : null}
			{errorMessage ? (
				<StatusMessage variant="error">{errorMessage}</StatusMessage>
			) : null}
			<Button
				type="button"
				onClick={sendLink}
				disabled={resetRequest.isPending}
			>
				{resetRequest.isPending
					? t("profile.password.sending_link")
					: t("profile.password.send_link")}
			</Button>
		</div>
	);
}

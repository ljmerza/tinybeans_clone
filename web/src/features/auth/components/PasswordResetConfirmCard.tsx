import { FormActions, FormField, StatusMessage } from "@/components";
import { IconTile } from "@/components/IconTile";
import { Button } from "@/components/ui/button";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import { passwordResetConfirmFieldSchemas } from "@/lib/validations/schemas/password-reset";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { KeyRound, Link2Off } from "lucide-react";
import { useState } from "react";

import { usePasswordResetConfirm } from "../hooks/authHooks";
import { SecureBrandPanel } from "./AuthBrandPanel";
import { AuthSplitLayout } from "./AuthSplitLayout";
import { PasswordInput } from "./PasswordInput";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

type PasswordResetConfirmCardProps = {
	token?: string;
};

export function PasswordResetConfirmCard({
	token,
}: PasswordResetConfirmCardProps) {
	const confirmReset = usePasswordResetConfirm();
	const navigate = useNavigate();
	const { getGeneral, getFieldErrors, translate } = useApiMessages();
	const [generalError, setGeneralError] = useState("");
	const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
	const [successMessage, setSuccessMessage] = useState("");

	const clearFieldError = (name: string) => {
		if (fieldErrors[name]) {
			setFieldErrors(({ [name]: _cleared, ...rest }) => rest);
		}
	};

	const form = useForm({
		defaultValues: {
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			if (!token) return;

			// Clear previous errors
			setGeneralError("");
			setFieldErrors({});
			setSuccessMessage("");

			try {
				const response = await confirmReset.mutateAsync({
					token,
					password: value.password,
					password_confirm: value.password_confirm,
				});

				// Show success message if provided
				if (response?.messages) {
					const messages = translate(response.messages);
					if (messages.length > 0) {
						setSuccessMessage(messages[0]);
					}
				}

				form.reset();

				// Navigate after a short delay so user sees success message
				setTimeout(() => {
					navigate({ to: "/login" });
				}, 1500);
			} catch (error) {
				const apiError = error as ApiError;
				console.error("Password reset confirm error:", apiError);

				// Extract field and general errors
				const fields = getFieldErrors(apiError.messages);
				const generals = getGeneral(apiError.messages);

				setFieldErrors(fields);
				if (generals.length > 0) {
					setGeneralError(generals[0]);
				}
			}
		},
	});

	if (!token) {
		return (
			<AuthSplitLayout
				aside={<SecureBrandPanel />}
				icon={<IconTile icon={Link2Off} tone="rose" size="lg" />}
				title="Invalid or expired link"
				description="We could not find a valid password reset token. Please request a new reset link."
			>
				<Link
					to="/password/reset/request"
					className="font-semibold text-primary hover:text-primary/80 transition-colors"
				>
					Request a new link
				</Link>
			</AuthSplitLayout>
		);
	}

	return (
		<AuthSplitLayout
			aside={<SecureBrandPanel />}
			icon={<IconTile icon={KeyRound} tone="amber" size="lg" />}
			title="Set a new password"
			description="Choose a new password for your account."
		>
			{/* Display general error */}
			{generalError && (
				<StatusMessage variant="error">{generalError}</StatusMessage>
			)}

			{/* Display success message */}
			{successMessage && (
				<StatusMessage variant="success">{successMessage}</StatusMessage>
			)}

			<form
				onSubmit={(event) => {
					event.preventDefault();
					event.stopPropagation();
					form.handleSubmit();
				}}
				className="space-y-4"
			>
				<form.Field
					name="password"
					validators={{
						onBlur: zodValidator(passwordResetConfirmFieldSchemas.password),
					}}
				>
					{(field) => (
						<FormField
							field={field}
							label="New password"
							error={fieldErrors.password}
						>
							{({ id, field: fieldApi }) => (
								<div className="space-y-2">
									<PasswordInput
										id={id}
										autoComplete="new-password"
										value={fieldApi.state.value}
										onChange={(event) => {
											fieldApi.handleChange(event.target.value);
											clearFieldError("password");
										}}
										onBlur={fieldApi.handleBlur}
										disabled={confirmReset.isPending}
										required
									/>
									<PasswordStrengthMeter password={fieldApi.state.value} />
								</div>
							)}
						</FormField>
					)}
				</form.Field>

				<form.Field
					name="password_confirm"
					validators={{
						onBlur: zodValidator(
							passwordResetConfirmFieldSchemas.password_confirm,
						),
					}}
				>
					{(field) => (
						<FormField
							field={field}
							label="Confirm password"
							error={fieldErrors.password_confirm}
						>
							{({ id, field: fieldApi }) => (
								<PasswordInput
									id={id}
									autoComplete="new-password"
									value={fieldApi.state.value}
									onChange={(event) => {
										fieldApi.handleChange(event.target.value);
										clearFieldError("password_confirm");
									}}
									onBlur={fieldApi.handleBlur}
									disabled={confirmReset.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<FormActions>
					<Button
						type="submit"
						size="lg"
						className="w-full"
						disabled={confirmReset.isPending}
					>
						{confirmReset.isPending ? "Updating…" : "Update password"}
					</Button>
				</FormActions>
			</form>

			<div className="border-t border-border pt-6 text-center text-sm">
				<Link
					to="/login"
					className="font-semibold text-primary hover:text-primary/80 transition-colors"
				>
					Return to login
				</Link>
			</div>
		</AuthSplitLayout>
	);
}

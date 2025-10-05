import type { ApiError, ApiResponseWithMessages } from "@/types";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { FieldError } from "@/components";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import {
	type PasswordResetRequestFormData,
	passwordResetRequestSchema,
} from "@/lib/validations/schemas/password-reset";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";

import { usePasswordResetRequest } from "../hooks/authHooks";

export function PasswordResetRequestCard() {
	const { t } = useTranslation();
	const resetRequest = usePasswordResetRequest();
	const { translate } = useApiMessages();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	const form = useForm<PasswordResetRequestFormData>({
		defaultValues: { identifier: "" },
		onSubmit: async ({ value }) => {
			setSuccessMessage(null);
			setErrorMessage(null);

			try {
				const response = await resetRequest.mutateAsync(value);

				// Translate and show success message
				if (response?.messages) {
					const messages = translate(response.messages);
					setSuccessMessage(
						messages.join(". ") || t("auth.password_reset.success_message"),
					);
				} else {
					setSuccessMessage(t("auth.password_reset.success_message"));
				}
			} catch (error) {
				const apiError = error as ApiError;
				console.error("Password reset request error:", apiError);

				// Translate and show error message
				if (apiError.messages) {
					const messages = translate(apiError.messages);
					setErrorMessage(messages.join(". "));
				} else {
					setErrorMessage(apiError.message ?? t("auth.password_reset.failed"));
				}
			}
		},
	});

	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
			<div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
				<div className="space-y-2 text-center">
					<h1 className="text-2xl font-semibold">
						{t("auth.password_reset.request_title")}
					</h1>
					<p className="text-sm text-muted-foreground">
						{t("auth.password_reset.request_description")}
					</p>
				</div>

				{successMessage && (
					<div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded p-3">
						{successMessage}
					</div>
				)}

				{errorMessage && (
					<div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded p-3">
						{errorMessage}
					</div>
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
						name="identifier"
						validators={{
							onBlur: zodValidator(passwordResetRequestSchema.shape.identifier),
						}}
					>
						{(field) => (
							<div className="form-group">
								<Label htmlFor={field.name}>
									{t("auth.password_reset.email_or_username")}
								</Label>
								<Input
									id={field.name}
									autoComplete="email"
									value={field.state.value}
									onChange={(event) => field.handleChange(event.target.value)}
									onBlur={field.handleBlur}
									disabled={resetRequest.isPending}
									required
								/>
								<FieldError field={field} />
							</div>
						)}
					</form.Field>

					<Button
						type="submit"
						className="w-full"
						disabled={resetRequest.isPending}
					>
						{resetRequest.isPending
							? t("auth.password_reset.sending")
							: t("auth.password_reset.send_reset_link")}
					</Button>
				</form>

				<div className="text-center text-sm">
					<Link
						to="/login"
						className="font-semibold text-blue-600 hover:text-blue-800"
					>
						{t("auth.password_reset.back_to_login")}
					</Link>
				</div>
			</div>
		</div>
	);
}

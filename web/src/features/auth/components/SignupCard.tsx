import { FormActions, FormField } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import { signupSchemaBase } from "@/lib/validations/schemas/signup";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useSignup } from "../hooks/authHooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

export function SignupCard() {
	const { t } = useTranslation();
	const signup = useSignup();
	const { getGeneral, getFieldErrors } = useApiMessages();
	const [generalError, setGeneralError] = useState("");
	const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

	const form = useForm({
		defaultValues: {
			username: "",
			email: "",
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			setGeneralError("");
			setFieldErrors({});

			const { password_confirm: _ignored, ...payload } = value;

			try {
				await signup.mutateAsync(payload);
			} catch (error) {
				const apiError = error as ApiError;
				console.error("Signup error:", apiError);

				// Extract field errors
				const errors = getFieldErrors(apiError.messages);
				setFieldErrors(errors);

				// Extract general errors
				const generalErrors = getGeneral(apiError.messages);
				if (generalErrors.length > 0) {
					setGeneralError(generalErrors.join(". "));
				} else if (!Object.keys(errors).length) {
					// Fallback if no structured errors
					const fallback =
						apiError.message && typeof apiError.message === "string"
							? t(apiError.message, {
									defaultValue: apiError.message,
								})
							: t("auth.signup.signup_failed");
					setGeneralError(fallback);
				}
			}
		},
	});

	return (
		<AuthCard
			title={t("auth.signup.title")}
			description={t("auth.signup.description")}
			footer={
				<div className="text-sm text-muted-foreground">
					{t("auth.signup.already_have_account")}{" "}
					<Link
						to="/login"
						className="font-semibold text-primary hover:text-primary/80 transition-colors"
					>
						{t("nav.login")}
					</Link>
				</div>
			}
		>
			<div className="space-y-4">
				<GoogleOAuthButton mode="signup" />

				<div className="relative">
					<div className="absolute inset-0 flex items-center">
						<div className="w-full border-t border-border/60 dark:border-border/40 transition-colors" />
					</div>
					<div className="relative flex justify-center text-sm">
						<span className="px-2 bg-card text-muted-foreground transition-colors">
							{t("common.or")}
						</span>
					</div>
				</div>
			</div>

			<form
				onSubmit={(event) => {
					event.preventDefault();
					event.stopPropagation();
					form.handleSubmit();
				}}
				className="space-y-4"
			>
				<form.Field
					name="username"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.username),
					}}
				>
					{(field) => (
						<FormField
							field={field}
							label={t("auth.signup.username")}
							error={fieldErrors.username}
						>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									value={fieldApi.state.value}
									onChange={(event) => fieldApi.handleChange(event.target.value)}
									onBlur={fieldApi.handleBlur}
									autoComplete="username"
									disabled={signup.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<form.Field
					name="email"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.email),
					}}
				>
					{(field) => (
						<FormField
							field={field}
							label={t("auth.signup.email")}
							error={fieldErrors.email}
						>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									type="email"
									value={fieldApi.state.value}
									onChange={(event) => fieldApi.handleChange(event.target.value)}
									onBlur={fieldApi.handleBlur}
									autoComplete="email"
									disabled={signup.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<form.Field
					name="password"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.password),
					}}
				>
					{(field) => (
						<FormField field={field} label={t("auth.signup.password")}>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									type="password"
									value={fieldApi.state.value}
									onChange={(event) => fieldApi.handleChange(event.target.value)}
									onBlur={fieldApi.handleBlur}
									autoComplete="new-password"
									disabled={signup.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<form.Field
					name="password_confirm"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.password_confirm),
					}}
				>
					{(field) => (
						<FormField
							field={field}
							label={t("auth.signup.confirm_password")}
						>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									type="password"
									value={fieldApi.state.value}
									onChange={(event) => fieldApi.handleChange(event.target.value)}
									onBlur={fieldApi.handleBlur}
									autoComplete="new-password"
									disabled={signup.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<FormActions
					messages={
						generalError
							? [
									{
										id: "signup-general-error",
										variant: "error" as const,
										content: generalError,
									},
								]
							: undefined
					}
				>
					<Button
						type="submit"
						className="w-full"
						disabled={signup.isPending}
					>
						{signup.isPending
							? t("auth.signup.creating_account")
							: t("auth.signup.create_account")}
					</Button>
				</FormActions>
			</form>
		</AuthCard>
	);
}

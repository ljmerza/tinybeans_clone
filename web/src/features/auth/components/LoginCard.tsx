import { FormActions, FormField } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import { loginSchema } from "@/lib/validations/schemas/login";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useLogin } from "../hooks/authHooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

interface LoginCardProps {
	redirect?: string;
}

/**
 * LoginCard Component
 *
 * Login form with:
 * - Centralized validation schema
 * - Explicit error handling with useApiMessages
 * - Field-level error display
 * - Context-aware error presentation
 */

export function LoginCard({ redirect }: LoginCardProps) {
	const { t } = useTranslation();
	const login = useLogin({ redirect });
	const { getGeneral } = useApiMessages();
	const [generalError, setGeneralError] = useState<string>("");

	const form = useForm({
		defaultValues: {
			username: "",
			password: "",
		},
		onSubmit: async ({ value }) => {
			setGeneralError("");

			try {
				await login.mutateAsync(value);
			} catch (error) {
				const apiError = error as ApiError;
				console.error("Login submission error:", apiError);

				// Extract general errors for display
				const generalErrors = getGeneral(apiError.messages);
				if (generalErrors.length > 0) {
					setGeneralError(generalErrors.join(". "));
				} else {
					// Fallback to translated error message or default
					const fallback =
						apiError.message && typeof apiError.message === "string"
							? t(apiError.message, {
									defaultValue: apiError.message,
								})
							: t("auth.login.login_failed");
					setGeneralError(fallback);
				}
			}
		},
	});

	return (
		<AuthCard
			title={t("auth.login.title")}
			footerClassName="space-y-4 text-center"
			footer={
				<>
					<div className="pt-4 border-t border-border transition-colors">
					<Link
						to="/magic-link-request"
						search={redirect ? { redirect } : undefined}
						className="text-sm font-medium text-primary hover:text-primary/80 hover:underline transition-colors"
					>
							{t("auth.login.with_magic_link")}
						</Link>
					</div>
					<div className="text-sm text-muted-foreground">
						{t("auth.login.no_account")}{" "}
					<Link
						to="/signup"
						search={redirect ? { redirect } : undefined}
						className="font-semibold text-primary hover:text-primary/80 transition-colors"
					>
							{t("nav.signup")}
						</Link>
					</div>
				</>
			}
		>
			<div className="space-y-4">
				<GoogleOAuthButton mode="login" redirect={redirect} />

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
						onBlur: zodValidator(loginSchema.shape.username),
					}}
				>
					{(field) => (
						<FormField field={field} label={t("auth.login.username")}>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									value={fieldApi.state.value}
									onChange={(event) =>
										fieldApi.handleChange(event.target.value)
									}
									onBlur={fieldApi.handleBlur}
									autoComplete="username"
									disabled={login.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<form.Field
					name="password"
					validators={{
						onBlur: zodValidator(loginSchema.shape.password),
					}}
				>
					{(field) => (
						<FormField field={field} label={t("auth.login.password")}>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									type="password"
									value={fieldApi.state.value}
									onChange={(event) =>
										fieldApi.handleChange(event.target.value)
									}
									onBlur={fieldApi.handleBlur}
									autoComplete="current-password"
									disabled={login.isPending}
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<FormActions
					secondary={
						<Link
							to="/password/reset/request"
							className="text-sm font-semibold text-primary hover:text-primary/80 transition-colors"
						>
							{t("auth.login.forgot_password")}
						</Link>
					}
					messages={
						generalError
							? [
									{
										id: "login-general-error",
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
						isLoading={login.isPending}
					>
						{login.isPending
							? t("auth.login.signing_in")
							: t("auth.login.sign_in")}
					</Button>
				</FormActions>
			</form>
		</AuthCard>
	);
}

/**
 * LoginCard Component
 *
 * Login form with:
 * - Centralized validation schema
 * - Explicit error handling with useApiMessages
 * - Field-level error display
 * - Context-aware error presentation
 */
import { StatusMessage, FieldError } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { zodValidator } from "@/lib/form/index.js";
import {
	loginSchema,
	type LoginFormData,
} from "@/lib/validations/schemas/login.js";
import { useApiMessages } from "@/i18n";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useLogin } from "../hooks/authHooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

export function LoginCard() {
	const { t } = useTranslation();
	const login = useLogin();
	const { getGeneral } = useApiMessages();
	const [generalError, setGeneralError] = useState<string>("");

	const form = useForm<LoginFormData>({
		defaultValues: {
			username: "",
			password: "",
		},
		onSubmit: async ({ value }) => {
			setGeneralError("");

			try {
				await login.mutateAsync(value);
			} catch (error: any) {
				console.error("Login submission error:", error);

				// Extract general errors for display
				const generalErrors = getGeneral(error.messages);
				if (generalErrors.length > 0) {
					setGeneralError(generalErrors.join(". "));
				} else {
					// Fallback to error message
					setGeneralError(error.message ?? t("auth.login.login_failed"));
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
					<div className="pt-4 border-t border-gray-200">
						<Link
							to="/magic-link-request"
							className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
						>
							{t("auth.login.with_magic_link")}
						</Link>
					</div>
					<div className="text-sm text-muted-foreground">
						{t("auth.login.no_account")}{" "}
						<Link
							to="/signup"
							className="font-semibold text-blue-600 hover:text-blue-800"
						>
							{t("nav.signup")}
						</Link>
					</div>
				</>
			}
		>
			<div className="space-y-4">
				<GoogleOAuthButton mode="login" />

				<div className="relative">
					<div className="absolute inset-0 flex items-center">
						<div className="w-full border-t border-gray-300" />
					</div>
					<div className="relative flex justify-center text-sm">
						<span className="px-2 bg-white text-gray-500">
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
						<div className="form-group">
							<Label htmlFor={field.name}>{t("auth.login.username")}</Label>
							<Input
								id={field.name}
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="username"
								disabled={login.isPending}
								required
							/>
							<FieldError field={field} />
						</div>
					)}
				</form.Field>

				<form.Field
					name="password"
					validators={{
						onBlur: zodValidator(loginSchema.shape.password),
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name}>{t("auth.login.password")}</Label>
							<Input
								id={field.name}
								type="password"
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="current-password"
								disabled={login.isPending}
								required
							/>
							<FieldError field={field} />
						</div>
					)}
				</form.Field>

				<div className="flex justify-end">
					<Link
						to="/password/reset/request"
						className="text-sm font-semibold text-blue-600 hover:text-blue-800"
					>
						{t("auth.login.forgot_password")}
					</Link>
				</div>

				<Button type="submit" className="w-full" disabled={login.isPending}>
					{login.isPending ? (
						<span className="flex items-center justify-center gap-2">
							<LoadingSpinner size="sm" />
							{t("auth.login.signing_in")}
						</span>
					) : (
						t("auth.login.sign_in")
					)}
				</Button>

				{/* Show general error message */}
				{generalError && (
					<StatusMessage variant="error">{generalError}</StatusMessage>
				)}
			</form>
		</AuthCard>
	);
}

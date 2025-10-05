import { FieldError, StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import {
	type SignupFormData,
	signupSchema,
	signupSchemaBase,
} from "@/lib/validations/schemas/signup";
import type { ApiError } from "@/types";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useSignup } from "../hooks/authHooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

export function SignupCard() {
	const { t } = useTranslation();
	const signup = useSignup();
	const navigate = useNavigate();
	const { getGeneral, getFieldErrors } = useApiMessages();
	const [generalError, setGeneralError] = useState("");
	const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

	const form = useForm<SignupFormData>({
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
				navigate({ to: "/" });
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
					setGeneralError(apiError.message ?? t("auth.signup.signup_failed"));
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
						className="font-semibold text-blue-600 hover:text-blue-800"
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
						onBlur: zodValidator(signupSchemaBase.shape.username),
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								{t("auth.signup.username")}
							</Label>
							<Input
								id={field.name}
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="username"
								disabled={signup.isPending}
								required
							/>
							<FieldError field={field} />
							{fieldErrors.username && (
								<p className="form-error">{fieldErrors.username}</p>
							)}
						</div>
					)}
				</form.Field>

				<form.Field
					name="email"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.email),
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								{t("auth.signup.email")}
							</Label>
							<Input
								id={field.name}
								type="email"
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="email"
								disabled={signup.isPending}
								required
							/>
							<FieldError field={field} />
							{fieldErrors.email && (
								<p className="form-error">{fieldErrors.email}</p>
							)}
						</div>
					)}
				</form.Field>

				<form.Field
					name="password"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.password),
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								{t("auth.signup.password")}
							</Label>
							<Input
								id={field.name}
								type="password"
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="new-password"
								disabled={signup.isPending}
								required
							/>
							<FieldError field={field} />
						</div>
					)}
				</form.Field>

				<form.Field
					name="password_confirm"
					validators={{
						onBlur: zodValidator(signupSchemaBase.shape.password_confirm),
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								{t("auth.signup.confirm_password")}
							</Label>
							<Input
								id={field.name}
								type="password"
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="new-password"
								disabled={signup.isPending}
								required
							/>
							<FieldError field={field} />
						</div>
					)}
				</form.Field>

				<Button type="submit" className="w-full" disabled={signup.isPending}>
					{signup.isPending
						? t("auth.signup.creating_account")
						: t("auth.signup.create_account")}
				</Button>

				{generalError && (
					<StatusMessage variant="error">{generalError}</StatusMessage>
				)}
			</form>
		</AuthCard>
	);
}

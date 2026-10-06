import { FormActions, FormField } from "@/components";
import { IconTile, type IconTileTone } from "@/components/IconTile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { getBrowserLanguage } from "@/i18n/browserLanguage";
import { zodValidator } from "@/lib/form/index";
import { signupSchemaBase } from "@/lib/validations/schemas/signup";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { BellRing, Images, Lock, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useSignup } from "../hooks/authHooks";
import { AppleOAuthButton } from "../oauth/AppleOAuthButton";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";
import { useOAuthProviders } from "../oauth/useOAuthProviders";
import { AuthSplitLayout } from "./AuthSplitLayout";
import { PasswordInput } from "./PasswordInput";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

const panelPoints: { key: string; icon: LucideIcon; tone: IconTileTone }[] = [
	{ key: "private", icon: Lock, tone: "sky" },
	{ key: "media", icon: Images, tone: "rose" },
	{ key: "notify", icon: BellRing, tone: "amber" },
];

function SignupBrandPanel() {
	const { t } = useTranslation();
	return (
		<div className="max-w-md space-y-8">
			<div className="space-y-3">
				<h2 className="text-3xl font-bold tracking-tight text-foreground text-balance">
					{t("auth.signup.panel_title")}
				</h2>
				<p className="text-lg text-muted-foreground text-pretty">
					{t("auth.signup.panel_subtitle")}
				</p>
			</div>
			<ul className="space-y-4">
				{panelPoints.map((point) => (
					<li key={point.key} className="flex items-center gap-4">
						<IconTile icon={point.icon} tone={point.tone} />
						<span className="text-foreground">
							{t(`auth.signup.panel_points.${point.key}`)}
						</span>
					</li>
				))}
			</ul>
		</div>
	);
}

interface SignupCardProps {
	redirect?: string;
	prefillEmail?: string;
}

export function SignupCard({ redirect, prefillEmail }: SignupCardProps) {
	const { t } = useTranslation();
	const { data: providers } = useOAuthProviders();
	// No social buttons, and no "or" divider, unless a provider is configured.
	const hasSocialLogin = Boolean(providers?.google || providers?.apple);
	const signup = useSignup({ redirect });
	const { getGeneral, getFieldErrors } = useApiMessages();
	const [generalError, setGeneralError] = useState("");
	const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

	const form = useForm({
		defaultValues: {
			first_name: "",
			last_name: "",
			email: prefillEmail ?? "",
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			setGeneralError("");
			setFieldErrors({});

			const { password_confirm: _ignored, ...payload } = value;

			try {
				await signup.mutateAsync({
					...payload,
					language: getBrowserLanguage(),
				});
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
		<AuthSplitLayout aside={<SignupBrandPanel />}>
			<div className="space-y-6">
				<div className="space-y-2">
					<h1 className="text-3xl font-bold tracking-tight text-foreground">
						{t("auth.signup.title")}
					</h1>
					<p className="text-muted-foreground">
						{t("auth.signup.description")}
					</p>
				</div>

				{hasSocialLogin && (
					<div className="space-y-4">
						<GoogleOAuthButton mode="signup" redirect={redirect} />
						<AppleOAuthButton mode="signup" redirect={redirect} />

						<div className="relative">
							<div className="absolute inset-0 flex items-center">
								<div className="w-full border-t border-border/60 dark:border-border/40 transition-colors" />
							</div>
							<div className="relative flex justify-center text-sm">
								<span className="px-2 bg-background text-muted-foreground transition-colors">
									{t("common.or")}
								</span>
							</div>
						</div>
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
					<div className="grid gap-4 sm:grid-cols-2">
						<form.Field
							name="first_name"
							validators={{
								onBlur: zodValidator(signupSchemaBase.shape.first_name),
							}}
						>
							{(field) => (
								<FormField
									field={field}
									label={t("auth.signup.first_name")}
									error={fieldErrors.first_name}
								>
									{({ id, field: fieldApi }) => (
										<Input
											id={id}
											value={fieldApi.state.value}
											onChange={(event) =>
												fieldApi.handleChange(event.target.value)
											}
											onBlur={fieldApi.handleBlur}
											autoComplete="given-name"
											disabled={signup.isPending}
											required
										/>
									)}
								</FormField>
							)}
						</form.Field>

						<form.Field
							name="last_name"
							validators={{
								onBlur: zodValidator(signupSchemaBase.shape.last_name),
							}}
						>
							{(field) => (
								<FormField
									field={field}
									label={t("auth.signup.last_name")}
									error={fieldErrors.last_name}
								>
									{({ id, field: fieldApi }) => (
										<Input
											id={id}
											value={fieldApi.state.value}
											onChange={(event) =>
												fieldApi.handleChange(event.target.value)
											}
											onBlur={fieldApi.handleBlur}
											autoComplete="family-name"
											disabled={signup.isPending}
											required
										/>
									)}
								</FormField>
							)}
						</form.Field>
					</div>

					{prefillEmail ? (
						<form.Field name="email">
							{(field) => (
								<>
									<input
										type="hidden"
										value={field.state.value}
										readOnly
										data-testid="prefilled-email"
									/>
									<div className="space-y-1">
										<div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
											{t("auth.signup.email")}
										</div>
										<div className="text-sm font-medium text-foreground break-all">
											{field.state.value}
										</div>
									</div>
								</>
							)}
						</form.Field>
					) : (
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
											onChange={(event) =>
												fieldApi.handleChange(event.target.value)
											}
											onBlur={fieldApi.handleBlur}
											autoComplete="email"
											disabled={signup.isPending}
											required
										/>
									)}
								</FormField>
							)}
						</form.Field>
					)}

					<form.Field
						name="password"
						validators={{
							onBlur: zodValidator(signupSchemaBase.shape.password),
						}}
					>
						{(field) => (
							<FormField
								field={field}
								label={t("auth.signup.password")}
								error={fieldErrors.password}
							>
								{({ id, field: fieldApi }) => (
									<div className="space-y-2">
										<PasswordInput
											id={id}
											value={fieldApi.state.value}
											onChange={(event) =>
												fieldApi.handleChange(event.target.value)
											}
											onBlur={fieldApi.handleBlur}
											autoComplete="new-password"
											disabled={signup.isPending}
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
							onBlur: zodValidator(signupSchemaBase.shape.password_confirm),
						}}
					>
						{(field) => (
							<FormField
								field={field}
								label={t("auth.signup.confirm_password")}
							>
								{({ id, field: fieldApi }) => (
									<PasswordInput
										id={id}
										value={fieldApi.state.value}
										onChange={(event) =>
											fieldApi.handleChange(event.target.value)
										}
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
							size="lg"
							className="w-full"
							isLoading={signup.isPending}
						>
							{signup.isPending
								? t("auth.signup.creating_account")
								: t("auth.signup.create_account")}
						</Button>
					</FormActions>
				</form>

				<p className="text-center text-sm text-muted-foreground">
					{t("auth.signup.already_have_account")}{" "}
					<Link
						to="/login"
						search={redirect ? { redirect } : undefined}
						className="font-semibold text-primary hover:text-primary/80 transition-colors"
					>
						{t("nav.login")}
					</Link>
				</p>

				{/* The brand panel is hidden on small screens; keep its points. */}
				<ul className="space-y-3 border-t border-border pt-6 lg:hidden">
					{panelPoints.map((point) => (
						<li key={point.key} className="flex items-center gap-3 text-sm">
							<IconTile icon={point.icon} tone={point.tone} size="sm" />
							<span className="text-muted-foreground">
								{t(`auth.signup.panel_points.${point.key}`)}
							</span>
						</li>
					))}
				</ul>
			</div>
		</AuthSplitLayout>
	);
}

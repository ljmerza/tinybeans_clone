/**
 * LoginCard Component (ADR-012 Compliant)
 * 
 * This component uses the modern notification strategy:
 * - Uses modernAuthClient instead of legacy api
 * - Uses useApiMessages for explicit error handling
 * - Shows field-level errors inline
 * - No auto-toast behavior
 */
import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { passwordSchema } from "@/lib/validations";
import { useApiMessages } from "@/i18n";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";

import { useLoginModern } from "../hooks/modernHooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

const schema = z.object({
	username: z.string().min(1, "Username is required"),
	password: passwordSchema,
});

type LoginFormValues = z.infer<typeof schema>;

export function LoginCard() {
	const login = useLoginModern();
	const { getGeneral } = useApiMessages();
	const [generalError, setGeneralError] = useState<string>("");

	const form = useForm({
		defaultValues: {
			username: "",
			password: "",
		} satisfies LoginFormValues,
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
					setGeneralError(error.message ?? "Login failed");
				}
			}
		},
	});

	return (
		<AuthCard
			title="Login"
			footerClassName="space-y-4 text-center"
			footer={
				<>
					<div className="pt-4 border-t border-gray-200">
						<Link
							to="/magic-link-request"
							className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
						>
							Login with Magic Link →
						</Link>
					</div>
					<div className="text-sm text-muted-foreground">
						Don't have an account?{" "}
						<Link
							to="/signup"
							className="font-semibold text-blue-600 hover:text-blue-800"
						>
							Sign up
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
						<span className="px-2 bg-white text-gray-500">OR</span>
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
						onBlur: ({ value }) => {
							const result = schema.shape.username.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name}>Username</Label>
							<Input
								id={field.name}
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="username"
								disabled={login.isPending}
								required
							/>
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<form.Field
					name="password"
					validators={{
						onBlur: ({ value }) => {
							const result = schema.shape.password.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name}>Password</Label>
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
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<div className="flex justify-end">
					<Link
						to="/password/reset/request"
						className="text-sm font-semibold text-blue-600 hover:text-blue-800"
					>
						Forgot password?
					</Link>
				</div>

				<Button type="submit" className="w-full" disabled={login.isPending}>
					{login.isPending ? (
						<span className="flex items-center justify-center gap-2">
							<LoadingSpinner size="sm" />
							Signing in…
						</span>
					) : (
						"Sign in"
					)}
				</Button>

				{/* Show general error message */}
				{generalError && (
					<StatusMessage variant="error">
						{generalError}
					</StatusMessage>
				)}
			</form>
		</AuthCard>
	);
}

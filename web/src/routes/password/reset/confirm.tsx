import { PublicOnlyRoute } from "@/components";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePasswordResetConfirm } from "@/modules/login/hooks";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";

const passwordSchema = z.string().min(8, "Password must be at least 8 characters");
const confirmPasswordSchema = z.string().min(8, "Confirm password");

const schema = z
	.object({
		password: passwordSchema,
		password_confirm: confirmPasswordSchema,
	})
	.superRefine((values, ctx) => {
		if (values.password !== values.password_confirm) {
			ctx.addIssue({
				code: z.ZodIssueCode.custom,
				message: "Passwords do not match",
				path: ["password_confirm"],
			});
		}
	});

type FormValues = z.infer<typeof schema>;

export const Route = createFileRoute("/password/reset/confirm")({
	validateSearch: (search) => z.object({ token: z.string().optional() }).parse(search),
	component: () => (
		<PublicOnlyRoute redirectTo="/">
			<PasswordResetConfirmPage />
		</PublicOnlyRoute>
	),
});

function PasswordResetConfirmPage() {
	const { token } = useSearch({ from: "/password/reset/confirm" });
	const confirmReset = usePasswordResetConfirm();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const navigate = useNavigate();

	const form = useForm<FormValues>({
		defaultValues: { password: "", password_confirm: "" },
		onSubmit: async ({ value }) => {
			if (!token) {
				return;
			}
			setSuccessMessage(null);
			try {
				const response = await confirmReset.mutateAsync({
					token,
					password: value.password,
					password_confirm: value.password_confirm,
				});
				setSuccessMessage(response.detail ?? "Password updated. You can now log in.");
				form.reset();
			} catch (error) {
				// Inline error state handled below
			}
		},
	});

	useEffect(() => {
		if (!successMessage) {
			return;
		}
		const timeout = window.setTimeout(() => {
			navigate({ to: "/login" });
		}, 2500);
		return () => window.clearTimeout(timeout);
	}, [successMessage, navigate]);

	const errorMessage = confirmReset.error instanceof Error ? confirmReset.error.message : null;

	if (!token) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
				<div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
					<h1 className="text-2xl font-semibold text-center">Invalid or expired link</h1>
					<p className="text-sm text-muted-foreground text-center">
						We could not find a valid password reset token. Please request a new reset link.
					</p>
					<div className="text-center">
						<Link
							to="/password/reset/request"
							className="font-semibold text-blue-600 hover:text-blue-800"
						>
							Request a new link
						</Link>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
			<div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
				<div className="space-y-2 text-center">
					<h1 className="text-2xl font-semibold">Set a new password</h1>
					<p className="text-sm text-muted-foreground">
						Choose a new password for your account.
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
						name="password"
						validators={{
								onBlur: ({ value }) => {
									const result = passwordSchema.safeParse(value);
									if (!result.success) {
										return result.error.errors[0].message;
									}
									return undefined;
								},
						}}
					>
						{(field) => (
							<div className="form-group">
								<Label htmlFor={field.name}>New password</Label>
								<Input
									id={field.name}
									type="password"
									autoComplete="new-password"
									value={field.state.value}
									onChange={(event) => field.handleChange(event.target.value)}
									onBlur={field.handleBlur}
									disabled={confirmReset.isPending}
									required
								/>
								{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
									<p className="form-error">{field.state.meta.errors[0]}</p>
								)}
							</div>
						)}
					</form.Field>

					<form.Field
						name="password_confirm"
						validators={{
							onBlur: ({ value, fieldApi }) => {
								if (value.length < 8) {
									return "Confirm password";
								}
								const password = fieldApi.form.getFieldValue("password");
								if (value !== password) {
									return "Passwords do not match";
								}
								return undefined;
							},
						}}
					>
						{(field) => (
							<div className="form-group">
								<Label htmlFor={field.name}>Confirm password</Label>
								<Input
									id={field.name}
									type="password"
									autoComplete="new-password"
									value={field.state.value}
									onChange={(event) => field.handleChange(event.target.value)}
									onBlur={field.handleBlur}
									disabled={confirmReset.isPending}
									required
								/>
								{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
									<p className="form-error">{field.state.meta.errors[0]}</p>
								)}
							</div>
						)}
					</form.Field>

					<Button type="submit" className="w-full" disabled={confirmReset.isPending}>
						{confirmReset.isPending ? (
							<span className="flex items-center justify-center gap-2">
								<LoadingSpinner size="sm" />
								Updating…
							</span>
						) : (
							"Update password"
						)}
					</Button>
				</form>

				<div className="text-center text-sm">
					<Link
						to="/login"
						className="font-semibold text-blue-600 hover:text-blue-800"
					>
						Return to login
					</Link>
				</div>
			</div>
		</div>
	);
}

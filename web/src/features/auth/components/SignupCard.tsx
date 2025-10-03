import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmPasswordSchema, passwordSchema } from "@/lib/validations";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { useSignup } from "../hooks";
import { GoogleOAuthButton } from "../oauth/GoogleOAuthButton";

const baseSchema = z.object({
	username: z.string().min(1, "Username is required"),
	email: z.string().email("Valid email required"),
	password: passwordSchema,
	password_confirm: confirmPasswordSchema,
});

type SignupFormValues = z.infer<typeof baseSchema>;

export function SignupCard() {
	const signup = useSignup();
	const navigate = useNavigate();

	const form = useForm({
		defaultValues: {
			username: "",
			email: "",
			password: "",
			password_confirm: "",
		} satisfies SignupFormValues,
		onSubmit: async ({ value }) => {
			const { password_confirm: _ignored, ...payload } = value;
			await signup.mutateAsync(payload);
			navigate({ to: "/" });
		},
	});

	return (
		<AuthCard
			title="Create your account"
			description="Join the community by filling out the details below. All fields are required."
			footer={
				<div className="text-sm text-muted-foreground">
					Already have an account?{" "}
					<Link
						to="/login"
						className="font-semibold text-blue-600 hover:text-blue-800"
					>
						Log in
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
							const result = baseSchema.shape.username.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								Username
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
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<form.Field
					name="email"
					validators={{
						onBlur: ({ value }) => {
							const result = baseSchema.shape.email.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								Email
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
							const result = baseSchema.shape.password.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								Password
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
							if (value.length < 8) return "Confirm password";
							const password = fieldApi.form.getFieldValue("password");
							if (value !== password) return "Passwords do not match";
							return undefined;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name} className="form-label">
								Confirm password
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
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<Button type="submit" className="w-full" disabled={signup.isPending}>
					{signup.isPending ? "Creating account…" : "Create account"}
				</Button>

				{signup.error && (
					<StatusMessage variant="error">
						{signup.error.message ?? "Signup failed"}
					</StatusMessage>
				)}
			</form>
		</AuthCard>
	);
}

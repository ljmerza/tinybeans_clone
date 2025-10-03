import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmPasswordSchema, passwordSchema } from "@/lib/validations";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, createRoute, useNavigate } from "@tanstack/react-router";
import type { AnyRoute } from "@tanstack/react-router";
import { z } from "zod";
import { useSignup } from "./hooks";

const baseSchema = z.object({
	username: z.string().min(1, "Username is required"),
	email: z.string().email("Valid email required"),
	password: passwordSchema,
	password_confirm: confirmPasswordSchema,
});

type SignupFormValues = z.infer<typeof baseSchema>;

function SignupPage() {
	const signup = useSignup();
	const navigate = useNavigate();

	const form = useForm<SignupFormValues>({
		defaultValues: {
			username: "",
			email: "",
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			const { password_confirm: _ignored, ...payload } = value;
			await signup.mutateAsync(payload);
			navigate({ to: "/" });
		},
	});

	return (
		<div className="container-sm section-spacing">
			<h1 className="heading-3 mb-4">Create your account</h1>
			<form
				onSubmit={(e) => {
					e.preventDefault();
					e.stopPropagation();
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
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
							const password = fieldApi.form.getFieldValue("password");
							if (value.length < 8) return "Confirm password";
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
								required
							/>
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<Button type="submit" className="w-full" disabled={signup.isPending}>
					{signup.isPending ? "Creating…" : "Create account"}
				</Button>

				{signup.error && (
					<p className="form-error">
						{signup.error.message ?? "Signup failed"}
					</p>
				)}

				<div className="text-center text-sm">
					Already have an account?{" "}
					<Link
						to="/login"
						className="font-semibold text-blue-600 hover:text-blue-800"
					>
						Log in
					</Link>
				</div>
			</form>
		</div>
	);
}

export default (parentRoute: AnyRoute) =>
	createRoute({
		path: "/signup",
		component: SignupPage,
		getParentRoute: () => parentRoute,
	});

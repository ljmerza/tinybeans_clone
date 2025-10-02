import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSignup } from "@/modules/login/hooks";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

const baseSchema = z.object({
	username: z.string().min(1, "Username is required"),
	email: z.string().email("Valid email required"),
	password: z.string().min(8, "Password must be at least 8 characters"),
	password_confirm: z.string().min(8, "Confirm password"),
});

function SignupPage() {
	const signup = useSignup();
	const navigate = useNavigate();

	const form = useForm({
		defaultValues: {
			username: "",
			email: "",
			password: "",
			password_confirm: "",
		},
		onSubmit: async ({ value }) => {
			const { password_confirm, ...payload } = value as any;
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
						{(signup.error as any)?.message ?? "Signup failed"}
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

export const Route = createFileRoute("/signup")({
	component: SignupPage,
});

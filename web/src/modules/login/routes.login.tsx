import { Link, createRoute, useNavigate } from "@tanstack/react-router";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { z } from "zod";
import { useLogin } from "./hooks";

const schema = z.object({
	username: z.string().min(1, "Username is required"),
	password: z.string().min(8, "Password must be at least 8 characters"),
});

function LoginPage() {
	const login = useLogin();
	const navigate = useNavigate();
	const search = {} as any as { redirect?: string };

	const form = useForm({
		defaultValues: { username: "", password: "" },
		onSubmit: async ({ value }) => {
			await login.mutateAsync(value as any);
			navigate({ to: search?.redirect || "/" });
		},
	});

	return (
		<div className="mx-auto max-w-sm p-6">
			<h1 className="mb-4 text-2xl font-semibold">Login</h1>
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
								autoComplete="username"
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
								onChange={(e) => field.handleChange(e.target.value)}
								onBlur={field.handleBlur}
								autoComplete="current-password"
								required
							/>
							{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
								<p className="form-error">{field.state.meta.errors[0]}</p>
							)}
						</div>
					)}
				</form.Field>

				<Button type="submit" className="w-full" disabled={login.isPending}>
					{login.isPending ? "Signing in…" : "Sign in"}
				</Button>
				{login.error && (
					<p className="text-sm text-red-600">
						{(login.error as any)?.message ?? "Login failed"}
					</p>
				)}

				<div className="text-center text-sm">
					Don't have an account?{" "}
					<Link
						to="/signup"
						className="font-semibold text-blue-600 hover:text-blue-800"
					>
						Sign up
					</Link>
				</div>
			</form>
		</div>
	);
}

export default (parentRoute: any) =>
	createRoute({
		path: "/login",
		component: LoginPage,
		getParentRoute: () => parentRoute,
	});

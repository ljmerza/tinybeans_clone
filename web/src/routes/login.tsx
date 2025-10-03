import { PublicOnlyRoute, StatusMessage } from "@/components";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { passwordSchema } from "@/lib/validations";
import { useLogin } from "@/modules/login/hooks";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

const schema = z.object({
	username: z.string().min(1, "Username is required"),
	password: passwordSchema,
});

type LoginFormValues = z.infer<typeof schema>;

function LoginPage() {
	const login = useLogin();

	const form = useForm<LoginFormValues>({
		defaultValues: { username: "", password: "" },
		onSubmit: async ({ value }) => {
			try {
				await login.mutateAsync(value);
			} catch (error) {
				// Error is already handled by the mutation
				console.error("Login submission error:", error);
			}
		},
	});

	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
			<div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6">
				<h1 className="mb-6 text-2xl font-semibold text-center">Login</h1>
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
									onChange={(e) => field.handleChange(e.target.value)}
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

					{login.error && (
						<div className="bg-red-50 border border-red-200 rounded p-3">
							<StatusMessage variant="error" align="center">
								{login.error.message || "Login failed. Please try again."}
							</StatusMessage>
						</div>
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
		</div>
	);
}

export const Route = createFileRoute("/login")({
	component: () => (
		<PublicOnlyRoute redirectTo="/">
			<LoginPage />
		</PublicOnlyRoute>
	),
});

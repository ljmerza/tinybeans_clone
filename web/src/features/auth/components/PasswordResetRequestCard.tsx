import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { z } from "zod";

import { usePasswordResetRequestModern } from "../hooks/modernHooks";

const schema = z.object({
	identifier: z.string().min(1, "Email or username is required"),
});

type PasswordResetRequestValues = z.infer<typeof schema>;

export function PasswordResetRequestCard() {
	const resetRequest = usePasswordResetRequestModern();
	const { translate } = useApiMessages();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	const form = useForm({
		defaultValues: { identifier: "" } satisfies PasswordResetRequestValues,
		onSubmit: async ({ value }) => {
			setSuccessMessage(null);
			setErrorMessage(null);
			
			try {
				const response = await resetRequest.mutateAsync(value);
				
				// Translate and show success message
				if (response?.messages) {
					const messages = translate(response.messages);
					setSuccessMessage(
						messages.join(". ") ||
						"If an account exists for that identifier, we'll send password reset instructions."
					);
				} else {
					setSuccessMessage(
						"If an account exists for that identifier, we'll send password reset instructions."
					);
				}
			} catch (error: any) {
				console.error("Password reset request error:", error);
				
				// Translate and show error message
				if (error.messages) {
					const messages = translate(error.messages);
					setErrorMessage(messages.join(". "));
				} else {
					setErrorMessage(error.message ?? "Failed to send reset email");
				}
			}
		},
	});

	return (
		<div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
			<div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
				<div className="space-y-2 text-center">
					<h1 className="text-2xl font-semibold">Forgot password</h1>
					<p className="text-sm text-muted-foreground">
						Enter your email address or username and we'll send you a reset
						link.
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
						name="identifier"
						validators={{
							onBlur: ({ value }) => {
								const result = schema.shape.identifier.safeParse(value);
								return result.success
									? undefined
									: result.error.errors[0].message;
							},
						}}
					>
						{(field) => (
							<div className="form-group">
								<Label htmlFor={field.name}>Email or username</Label>
								<Input
									id={field.name}
									autoComplete="email"
									value={field.state.value}
									onChange={(event) => field.handleChange(event.target.value)}
									onBlur={field.handleBlur}
									disabled={resetRequest.isPending}
									required
								/>
								{field.state.meta.isTouched && field.state.meta.errors?.[0] && (
									<p className="form-error">{field.state.meta.errors[0]}</p>
								)}
							</div>
						)}
					</form.Field>

					<Button
						type="submit"
						className="w-full"
						disabled={resetRequest.isPending}
					>
						{resetRequest.isPending ? "Sending…" : "Send reset link"}
					</Button>
				</form>

				<div className="text-center text-sm">
					Remembered your password?{" "}
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

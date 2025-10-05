import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";

import { useMagicLinkRequestWithMessages } from "../hooks/explicitHooks";

const schema = z.object({
	email: z.string().email("Please enter a valid email address"),
});

type MagicLinkFormValues = z.infer<typeof schema>;

export function MagicLinkRequestCard() {
	const magicLoginRequest = useMagicLinkRequestWithMessages();
	const { getGeneral, translate } = useApiMessages();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	const form = useForm({
		defaultValues: { email: "" } satisfies MagicLinkFormValues,
		onSubmit: async ({ value }) => {
			// Clear previous messages
			setSuccessMessage(null);
			setErrorMessage(null);
			
			try {
				const response = await magicLoginRequest.mutateAsync(value);
				
				// Show success message from server or default
				if (response?.messages) {
					const messages = translate(response.messages);
					if (messages.length > 0) {
						setSuccessMessage(messages[0]);
					}
				} else {
					setSuccessMessage(
						"If an account with that email exists, a magic login link has been sent. Check your email!"
					);
				}
			} catch (error: any) {
				console.error("Magic link request error:", error);
				
				// Extract general error messages
				const generals = getGeneral(error.messages);
				if (generals.length > 0) {
					setErrorMessage(generals[0]);
				} else {
					setErrorMessage("Failed to send magic link. Please try again.");
				}
			}
		},
	});

	return (
		<AuthCard
			title="Magic Link Login"
			description="Enter your email address and we'll send you a magic link to log in instantly—no password required."
			footerClassName="space-y-3 text-center text-sm text-muted-foreground"
			footer={
				<>
					<div>
						<Link
							to="/login"
							className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
						>
							Back to traditional login
						</Link>
					</div>
					<div>
						Don't have an account?{" "}
						<Link
							to="/signup"
							className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
						>
							Sign up
						</Link>
					</div>
				</>
			}
		>
			<form
				onSubmit={(event) => {
					event.preventDefault();
					event.stopPropagation();
					form.handleSubmit();
				}}
				className="space-y-4"
			>
				<form.Field
					name="email"
					validators={{
						onBlur: ({ value }) => {
							const result = schema.shape.email.safeParse(value);
							return result.success
								? undefined
								: result.error.errors[0].message;
						},
					}}
				>
					{(field) => (
						<div className="form-group">
							<Label htmlFor={field.name}>Email Address</Label>
							<Input
								id={field.name}
								type="email"
								placeholder="your@email.com"
								value={field.state.value}
								onChange={(event) => field.handleChange(event.target.value)}
								onBlur={field.handleBlur}
								autoComplete="email"
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
					disabled={magicLoginRequest.isPending}
				>
					{magicLoginRequest.isPending
						? "Sending Magic Link…"
						: "Send Magic Link"}
				</Button>

				{successMessage && (
					<StatusMessage variant="success">{successMessage}</StatusMessage>
				)}
				{errorMessage && (
					<StatusMessage variant="error">{errorMessage}</StatusMessage>
				)}
			</form>

			<div className="pt-4 border-t text-xs text-muted-foreground space-y-2">
				<p className="font-semibold">How it works:</p>
				<ol className="list-decimal list-inside space-y-1 text-gray-600">
					<li>Enter your email address</li>
					<li>Click the link we send you</li>
					<li>You're logged in automatically</li>
				</ol>
				<p className="text-gray-500 italic">
					The magic link expires in 15 minutes and can only be used once.
				</p>
			</div>
		</AuthCard>
	);
}

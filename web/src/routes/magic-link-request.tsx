import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMagicLoginRequest } from "@/modules/login/hooks";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";

const schema = z.object({
	email: z.string().email("Please enter a valid email address"),
});

type FormValues = z.infer<typeof schema>;

function MagicLinkRequestPage() {
	const magicLoginRequest = useMagicLoginRequest();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);

	const form = useForm<FormValues>({
		defaultValues: { email: "" },
		onSubmit: async ({ value }) => {
			setSuccessMessage(null);
			try {
				const response = await magicLoginRequest.mutateAsync(value);
				setSuccessMessage(
					response.message ??
						"If an account with that email exists, a magic login link has been sent. Check your email!",
				);
			} catch (error) {
				// Inline error state handled below
			}
		},
	});

	const errorMessage =
		magicLoginRequest.error instanceof Error
			? magicLoginRequest.error.message
			: null;

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
				onSubmit={(e) => {
					e.preventDefault();
					e.stopPropagation();
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
									onChange={(e) => field.handleChange(e.target.value)}
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

export const Route = createFileRoute("/magic-link-request")({
	component: MagicLinkRequestPage,
});

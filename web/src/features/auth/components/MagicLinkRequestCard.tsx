import { StatusMessage } from "@/components";
import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiMessages } from "@/i18n";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { useMagicLinkRequest } from "../hooks/authHooks";

const createSchema = (t: (key: string) => string) => z.object({
	email: z.string().email(t('validation.email_valid')),
});

type MagicLinkFormValues = {
	email: string;
};

export function MagicLinkRequestCard() {
	const { t } = useTranslation();
	const magicLoginRequest = useMagicLinkRequest();
	const { getGeneral, translate } = useApiMessages();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);
	const schema = createSchema(t);

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
					setSuccessMessage(t('auth.magic_link.success_message'));
				}
			} catch (error: any) {
				console.error("Magic link request error:", error);
				
				// Extract general error messages
				const generals = getGeneral(error.messages);
				if (generals.length > 0) {
					setErrorMessage(generals[0]);
				} else {
					setErrorMessage(t('auth.magic_link.failed'));
				}
			}
		},
	});

	return (
		<AuthCard
			title={t('auth.magic_link.request_title')}
			description={t('auth.magic_link.request_description')}
			footerClassName="space-y-3 text-center text-sm text-muted-foreground"
			footer={
				<>
					<div>
						<Link
							to="/login"
							className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
						>
							{t('auth.magic_link.back_to_login')}
						</Link>
					</div>
					<div>
						{t('auth.login.no_account')}{" "}
						<Link
							to="/signup"
							className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
						>
							{t('nav.signup')}
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
							<Label htmlFor={field.name}>{t('auth.magic_link.email')}</Label>
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
						? t('auth.magic_link.sending')
						: t('auth.magic_link.send_magic_link')}
				</Button>

				{successMessage && (
					<StatusMessage variant="success">{successMessage}</StatusMessage>
				)}
				{errorMessage && (
					<StatusMessage variant="error">{errorMessage}</StatusMessage>
				)}
			</form>
		</AuthCard>
	);
}

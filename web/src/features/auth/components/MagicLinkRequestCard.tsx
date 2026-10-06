import { FormActions, FormField } from "@/components";
import { IconTile } from "@/components/IconTile";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import { useApiMessages } from "@/i18n";
import { zodValidator } from "@/lib/form/index";
import { magicLinkRequestSchema } from "@/lib/validations/schemas/magic-link";
import type { ApiError } from "@/types";
import { useForm } from "@tanstack/react-form";
import { Link } from "@tanstack/react-router";
import { Mail } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useMagicLinkRequest } from "../hooks/authHooks";
import { SecureBrandPanel } from "./AuthBrandPanel";
import { AuthSplitLayout } from "./AuthSplitLayout";

interface MagicLinkRequestCardProps {
	redirect?: string;
}

export function MagicLinkRequestCard({ redirect }: MagicLinkRequestCardProps) {
	const { t } = useTranslation();
	const magicLoginRequest = useMagicLinkRequest();
	const { getGeneral, translate } = useApiMessages();
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	useEffect(() => {
		if (redirect) {
			rememberInviteRedirect(redirect);
		}
	}, [redirect]);

	const form = useForm({
		defaultValues: { email: "" },
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
					setSuccessMessage(t("auth.magic_link.success_message"));
				}
			} catch (error) {
				const apiError = error as ApiError;
				const generals = getGeneral(apiError.messages);
				if (generals.length > 0) {
					setErrorMessage(generals[0]);
				} else {
					setErrorMessage(t("auth.magic_link.failed"));
				}
			}
		},
	});

	return (
		<AuthSplitLayout
			aside={<SecureBrandPanel />}
			icon={<IconTile icon={Mail} tone="sky" size="lg" />}
			title={t("auth.magic_link.request_title")}
			description={t("auth.magic_link.request_description")}
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
						onBlur: zodValidator(magicLinkRequestSchema.shape.email),
					}}
				>
					{(field) => (
						<FormField field={field} label={t("auth.magic_link.email")}>
							{({ id, field: fieldApi }) => (
								<Input
									id={id}
									type="email"
									placeholder="your@email.com"
									value={fieldApi.state.value}
									onChange={(event) =>
										fieldApi.handleChange(event.target.value)
									}
									onBlur={fieldApi.handleBlur}
									autoComplete="email"
									required
								/>
							)}
						</FormField>
					)}
				</form.Field>

				<FormActions
					messages={[
						successMessage
							? {
									id: "magic-link-success",
									variant: "success" as const,
									content: successMessage,
								}
							: null,
						errorMessage
							? {
									id: "magic-link-error",
									variant: "error" as const,
									content: errorMessage,
								}
							: null,
					].filter(
						(message): message is NonNullable<typeof message> => !!message,
					)}
				>
					<Button
						type="submit"
						size="lg"
						className="w-full"
						disabled={magicLoginRequest.isPending}
					>
						{magicLoginRequest.isPending
							? t("auth.magic_link.sending")
							: t("auth.magic_link.send_magic_link")}
					</Button>
				</FormActions>
			</form>

			<div className="space-y-3 border-t border-border pt-6 text-center text-sm text-muted-foreground">
				<div>
					<Link
						to="/login"
						search={{ redirect }}
						className="font-medium text-primary hover:text-primary/80 hover:underline transition-colors"
					>
						{t("auth.magic_link.back_to_login")}
					</Link>
				</div>
				<div>
					{t("auth.login.no_account")}{" "}
					<Link
						to="/signup"
						search={{ redirect }}
						className="font-semibold text-primary hover:text-primary/80 transition-colors"
					>
						{t("nav.signup")}
					</Link>
				</div>
			</div>
		</AuthSplitLayout>
	);
}

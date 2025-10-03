import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { useMagicLoginVerify } from "@/modules/login/hooks";

function MagicLoginPage() {
	const navigate = useNavigate();
	const { token } = Route.useSearch();
	const magicLoginVerify = useMagicLoginVerify();
	const [status, setStatus] = useState<"verifying" | "success" | "error">(
		"verifying",
	);

	useEffect(() => {
		if (!token) {
			setStatus("error");
			return;
		}

		// Verify the magic login token
		magicLoginVerify
			.mutateAsync({ token })
			.then(() => {
				setStatus("success");
				// Navigation is handled by the hook on success
			})
			.catch(() => {
				setStatus("error");
			});
	}, [token, magicLoginVerify]);

	return (
		<div className="mx-auto max-w-sm p-6">
			<h1 className="mb-4 text-2xl font-semibold">Magic Login</h1>

			{status === "verifying" && (
				<div className="space-y-4">
					<StatusMessage variant="info">
						Verifying your magic login link...
					</StatusMessage>
					<div className="flex justify-center">
						<div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
					</div>
				</div>
			)}

			{status === "success" && (
				<div className="space-y-4">
					<StatusMessage variant="success">
						Successfully logged in! Redirecting...
					</StatusMessage>
				</div>
			)}

			{status === "error" && (
				<div className="space-y-4">
					<StatusMessage variant="error">
						{magicLoginVerify.error?.message ??
							"Invalid or expired magic login link. Please request a new one."}
					</StatusMessage>
					<Button
						onClick={() => navigate({ to: "/login" })}
						className="w-full"
					>
						Return to Login
					</Button>
				</div>
			)}
		</div>
	);
}

export const Route = createFileRoute("/magic-login")({
	component: MagicLoginPage,
	validateSearch: (search: Record<string, unknown>) => {
		return {
			token: (search.token as string) || undefined,
		};
	},
});

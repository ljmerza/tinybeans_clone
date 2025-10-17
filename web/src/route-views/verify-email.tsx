import { EmailVerificationHandler } from "@/features/auth";
import { useSearch } from "@tanstack/react-router";

export default function VerifyEmailRoute() {
	const { token } = useSearch({ from: "/verify-email" as const });
	return <EmailVerificationHandler token={token} />;
}

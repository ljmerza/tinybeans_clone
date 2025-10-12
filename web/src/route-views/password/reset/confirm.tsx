import { PasswordResetConfirmCard } from "@/features/auth";
import { useSearch } from "@tanstack/react-router";

export default function PasswordResetConfirmRoute() {
	const { token } = useSearch({
		from: "/password/reset/confirm" as const,
	});

	return <PasswordResetConfirmCard token={token} />;
}

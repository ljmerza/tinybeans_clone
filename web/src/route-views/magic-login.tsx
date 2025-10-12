import { MagicLoginHandler } from "@/features/auth";
import { useSearch } from "@tanstack/react-router";

export default function MagicLoginRoute() {
	const { token } = useSearch({ from: "/magic-login" as const });
	return <MagicLoginHandler token={token} />;
}

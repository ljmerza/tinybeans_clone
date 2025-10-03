import { createFileRoute } from "@tanstack/react-router";

import { LoginCard } from "@/features/auth";

export const Route = createFileRoute("/login")({
	component: LoginCard,
});

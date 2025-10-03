import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { LoginCard } from "@/features/auth";

export const Route = createFileRoute("/login")({
	beforeLoad: requireGuest,
	component: LoginCard,
});

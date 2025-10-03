import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { PasswordResetRequestCard } from "@/features/auth";

export const Route = createFileRoute("/password/reset/request")({
	beforeLoad: requireGuest,
	component: PasswordResetRequestCard,
});

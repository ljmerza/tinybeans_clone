import { requireAuth } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { LogoutHandler } from "@/features/auth";

export const Route = createFileRoute("/logout")({
	beforeLoad: requireAuth,
	component: LogoutHandler,
});

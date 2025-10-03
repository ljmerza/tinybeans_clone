import { createFileRoute } from "@tanstack/react-router";

import { LogoutHandler } from "@/features/auth";

export const Route = createFileRoute("/logout")({
	component: LogoutHandler,
});

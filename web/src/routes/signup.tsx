import { createFileRoute } from "@tanstack/react-router";

import { SignupCard } from "@/features/auth";

export const Route = createFileRoute("/signup")({
	component: SignupCard,
});

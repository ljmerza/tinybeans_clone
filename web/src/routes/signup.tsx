import { requireGuest } from "@/features/auth";
import { createFileRoute } from "@tanstack/react-router";

import { SignupCard } from "@/features/auth";

export const Route = createFileRoute("/signup")({
	beforeLoad: requireGuest,
	component: SignupCard,
});

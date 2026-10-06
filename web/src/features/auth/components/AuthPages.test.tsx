import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const navigate = vi.fn();
const location = {
	state: { twoFactor: { partialToken: "partial", method: "totp" } },
};

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({
		children,
		to,
		...rest
	}: { children?: React.ReactNode; to?: string; "aria-label"?: string }) => (
		<a href={to} aria-label={rest["aria-label"]}>
			{children}
		</a>
	),
	Navigate: () => null,
	useNavigate: () => navigate,
	useLocation: () => location,
}));

// Importing a route file otherwise loads the route tree mid-evaluation.
vi.mock("@/router", () => ({ router: {} }));

const session = {
	isReady: true,
	isAuthenticated: true,
	user: { email: "ada@example.com", email_verified: false },
	refetchUser: vi.fn(),
};

// EmailVerificationHandler reaches useAuthSession through the barrel while the
// barrel is still loading, so mock the hook at its source too.
vi.mock(
	"@/features/auth/context/AuthSessionProvider",
	async (importOriginal) => ({
		...(await importOriginal<
			typeof import("@/features/auth/context/AuthSessionProvider")
		>()),
		useAuthSession: () => session,
	}),
);

vi.mock("@/features/auth", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/features/auth")>()),
	useAuthSession: () => session,
	useResendVerificationMutation: () => ({ mutate: vi.fn(), isPending: false }),
}));

import VerifyEmailRequiredRoute from "@/route-views/verify-email-required";
import { Route as TwoFactorVerifyRoute } from "@/routes/profile/2fa/verify";
import { EmailVerificationHandler } from "./EmailVerificationHandler";
import { MagicLinkRequestCard } from "./MagicLinkRequestCard";
import { MagicLoginHandler } from "./MagicLoginHandler";
import { PasswordResetConfirmCard } from "./PasswordResetConfirmCard";
import { PasswordResetRequestCard } from "./PasswordResetRequestCard";

const TwoFactorVerifyPage = TwoFactorVerifyRoute.options
	.component as React.ComponentType;

function expectSplitLayout(title: string) {
	expect(
		screen.getByRole("heading", { level: 1, name: title }),
	).toBeInTheDocument();
	expect(
		screen.getByRole("heading", {
			level: 2,
			name: "Your circle stays private",
		}),
	).toBeInTheDocument();
	for (const link of screen.getAllByRole("link", { name: "Circles home" })) {
		expect(link).toHaveAttribute("href", "/");
	}
}

describe("secondary auth pages use the split layout", () => {
	it("magic link request", () => {
		renderWithQueryClient(<MagicLinkRequestCard />);
		expectSplitLayout("Login with Magic Link");
		expect(
			screen.getByRole("link", { name: "← Back to login" }),
		).toHaveAttribute("href", "/login");
	});

	it("password reset request", () => {
		renderWithQueryClient(<PasswordResetRequestCard />);
		expectSplitLayout("Reset Password");
		expect(
			screen.getByRole("button", { name: "Send reset link" }),
		).toBeInTheDocument();
	});

	it("password reset confirm, with a strength meter", () => {
		renderWithQueryClient(<PasswordResetConfirmCard token="reset-token" />);
		expectSplitLayout("Set a new password");
		expect(screen.getByLabelText("New password")).toHaveAttribute(
			"type",
			"password",
		);
		expect(
			screen.getAllByRole("button", { name: "Show password" }),
		).toHaveLength(2);
	});

	it("password reset confirm without a token", () => {
		renderWithQueryClient(<PasswordResetConfirmCard />);
		expectSplitLayout("Invalid or expired link");
		expect(
			screen.getByRole("link", { name: "Request a new link" }),
		).toHaveAttribute("href", "/password/reset/request");
	});

	it("email verification without a token", async () => {
		renderWithQueryClient(<EmailVerificationHandler />);
		expectSplitLayout("Verify your email");
		expect(
			await screen.findByText("Invalid verification link."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Close this tab" }),
		).toBeInTheDocument();
	});

	it("magic login without a token", async () => {
		renderWithQueryClient(<MagicLoginHandler />);
		expectSplitLayout("Login with Magic Link");
		expect(await screen.findByText("Invalid magic link")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "← Back to login" }),
		).toBeInTheDocument();
	});

	it("two-factor verification", () => {
		renderWithQueryClient(<TwoFactorVerifyPage />);
		expectSplitLayout("Two-Factor Authentication Required");
		expect(
			screen.getByRole("button", { name: "← Back to login" }),
		).toBeInTheDocument();
	});

	it("verify email required", () => {
		renderWithQueryClient(<VerifyEmailRequiredRoute />);
		expectSplitLayout("Verify your email");
		expect(screen.getByText("Action required")).toBeInTheDocument();
		expect(screen.getByText("ada@example.com")).toBeInTheDocument();
	});
});

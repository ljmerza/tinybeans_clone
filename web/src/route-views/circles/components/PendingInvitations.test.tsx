import "@/i18n/config";
import { circleServices } from "@/features/circles";
import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const navigate = vi.fn();

vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	useNavigate: () => navigate,
}));

import { PendingInvitations } from "./PendingInvitations";

const invitation = {
	id: "inv-1",
	role: "member",
	created_at: "2026-10-01T00:00:00Z",
	circle: { id: 9, name: "The Smiths", slug: "the-smiths", member_count: 4 },
	invited_by: { id: 1, email: "grandma@example.com", display_name: "Grandma" },
};

beforeEach(() => {
	vi.spyOn(circleServices, "listPendingInvitations").mockResolvedValue({
		data: { invitations: [invitation] },
	});
});

afterEach(() => {
	vi.restoreAllMocks();
	navigate.mockReset();
});

describe("PendingInvitations", () => {
	it("joins the circle and opens it on accept", async () => {
		const respond = vi
			.spyOn(circleServices, "respondToInvitation")
			.mockResolvedValue({ data: { circle: invitation.circle } });
		renderWithQueryClient(<PendingInvitations enabled />);

		expect(await screen.findByText("The Smiths")).toBeInTheDocument();
		expect(screen.getByText("Invited by Grandma")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: "Accept invitation" }));

		await waitFor(() =>
			expect(navigate).toHaveBeenCalledWith({
				to: "/circles/$circleId",
				params: { circleId: "9" },
			}),
		);
		expect(respond).toHaveBeenCalledWith("inv-1", "accept");
	});

	it("stays on onboarding after a decline", async () => {
		const respond = vi
			.spyOn(circleServices, "respondToInvitation")
			.mockResolvedValue({ data: { circle: invitation.circle } });
		renderWithQueryClient(<PendingInvitations enabled />);

		fireEvent.click(await screen.findByRole("button", { name: "Decline" }));

		await waitFor(() =>
			expect(respond).toHaveBeenCalledWith("inv-1", "decline"),
		);
		expect(navigate).not.toHaveBeenCalled();
	});

	it("doesn't ask before the email is verified", () => {
		renderWithQueryClient(<PendingInvitations enabled={false} />);

		expect(circleServices.listPendingInvitations).not.toHaveBeenCalled();
		expect(screen.queryByRole("heading")).toBeNull();
	});
});

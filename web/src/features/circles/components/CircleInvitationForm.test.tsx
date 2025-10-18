import "@/i18n/config";

import { renderWithQueryClient } from "@/test-utils";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CircleInvitationForm } from "./CircleInvitationForm";

const mockUseCreateCircleInvitation = vi.fn();

vi.mock("../hooks/useCircleInvitationAdmin", () => ({
	useCreateCircleInvitation: (...args: unknown[]) =>
		mockUseCreateCircleInvitation(...args),
}));

describe("CircleInvitationForm", () => {
	const createSpy = vi.fn().mockResolvedValue({});

	beforeEach(() => {
		createSpy.mockClear();
		mockUseCreateCircleInvitation.mockReturnValue({
			mutateAsync: createSpy,
			isPending: false,
		});
	});

	it("submits email invitations", async () => {
		renderWithQueryClient(<CircleInvitationForm circleId="12" />);

		const emailInput = screen.getByLabelText("Email");
		fireEvent.change(emailInput, { target: { value: "alex@example.com" } });

		fireEvent.click(screen.getByRole("button", { name: "Send invitation" }));

		await waitFor(() => {
			expect(createSpy).toHaveBeenCalledWith(
				expect.objectContaining({ email: "alex@example.com", role: "member" }),
			);
		});
	});
});

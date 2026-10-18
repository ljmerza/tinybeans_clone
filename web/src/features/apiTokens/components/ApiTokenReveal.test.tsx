import "@/i18n/config";
import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { openChange } = vi.hoisted(() => ({ openChange: vi.fn() }));

// The real dialog, but listening to the close requests it would make: an
// Escape or outside click the reveal fails to block shows up as
// onOpenChange(false).
vi.mock("@/components/ui/dialog", async (importOriginal) => {
	const actual =
		await importOriginal<typeof import("@/components/ui/dialog")>();
	return {
		...actual,
		Dialog: (props: ComponentProps<typeof actual.Dialog>) => (
			<actual.Dialog {...props} onOpenChange={openChange} />
		),
	};
});

import { ApiTokenReveal } from "./ApiTokenReveal";

const PLAINTEXT = `circ_${"x".repeat(43)}`;

afterEach(() => {
	openChange.mockReset();
});

describe("ApiTokenReveal", () => {
	it("blocks Escape and outside clicks", async () => {
		render(<ApiTokenReveal plaintext={PLAINTEXT} onDone={vi.fn()} />);
		const dialog = screen.getByRole("dialog", { name: "Your new API token" });
		// Radix starts listening for outside clicks on the next tick.
		await act(() => new Promise((resolve) => setTimeout(resolve, 0)));

		fireEvent.keyDown(dialog, { key: "Escape" });
		fireEvent.pointerDown(document.body);
		fireEvent.focusIn(document.body);

		expect(openChange).not.toHaveBeenCalled();
		expect(screen.getByText(PLAINTEXT)).toBeInTheDocument();
	});

	it('has no close button; only "I\'ve copied it" closes it', () => {
		const onDone = vi.fn();
		render(<ApiTokenReveal plaintext={PLAINTEXT} onDone={onDone} />);

		expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
		fireEvent.click(screen.getByRole("button", { name: "I've copied it" }));

		expect(onDone).toHaveBeenCalledTimes(1);
	});
});

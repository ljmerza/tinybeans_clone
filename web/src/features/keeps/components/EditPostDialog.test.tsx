import "@/i18n/config";
import { createTestQueryClient } from "@/lib/query/queryClient";
import { renderWithQueryClient } from "@/test-utils";
import type { InfiniteData } from "@tanstack/react-query";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Names link to the person page; outside a router a plain anchor will do.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({
		children,
		to,
		params,
	}: {
		children?: ReactNode;
		to: string;
		params?: { personId: string };
	}) => (
		<a href={to.replace("$personId", params?.personId ?? "")}>{children}</a>
	),
}));

import { circleServices } from "@/features/circles";
import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import { useFeedKeep } from "../hooks/useKeepFeed";
import type { CirclePerson, FeedKeep, FeedPage } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

const sophia: CirclePerson = {
	id: "p-sophia",
	name: "Sophia M",
	kind: "child",
};
const leo: CirclePerson = { id: "p-leo", name: "Leo", kind: "member" };
const jo: CirclePerson = { id: "p-jo", name: "Grandma Jo", kind: "other" };

const makeKeep = (overrides: Partial<FeedKeep> = {}): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "First time in the ocean",
	date_of_memory: "2026-07-04T15:30:00Z",
	created_at: "2026-07-05T10:00:00Z",
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: true,
	recent_comments: [],
	people: [{ id: sophia.id, name: sophia.name }],
	...overrides,
});

const feedPage = (results: FeedKeep[]): InfiniteData<FeedPage> => ({
	pages: [{ next: null, previous: null, results }],
	pageParams: [undefined],
});

/** The post as the feed shows it: read from the cache, so saved edits show up. */
function CachedPost({ keepId }: { keepId: string }) {
	const { data } = useFeedKeep(keepId);
	return data ? <KeepFeedPost keep={data} /> : null;
}

/** Seed the home and day feeds and a calendar month, then show the post. */
async function renderInFeeds(keep: FeedKeep) {
	// Kept around without observers, like caches from other pages.
	const queryClient = createTestQueryClient({
		defaultOptions: { queries: { gcTime: Number.POSITIVE_INFINITY } },
	});
	queryClient.setQueryData(keepKeys.feed(), feedPage([keep]));
	queryClient.setQueryData(keepKeys.feedDay("2026-07-04"), feedPage([keep]));
	queryClient.setQueryData(keepKeys.calendarMonth("2026-07"), { days: [] });
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(keep);
	renderWithQueryClient(<CachedPost keepId={keep.id} />, { queryClient });
	await screen.findByRole("article");
	return queryClient;
}

async function openEditor() {
	fireEvent.click(screen.getByRole("button", { name: "Edit post" }));
	const dialog = await screen.findByRole("dialog", { name: "Edit post" });
	// The circle's people have loaded once the picker lists them.
	await within(dialog).findByRole("button", { name: "Leo" });
	return dialog;
}

const save = (dialog: HTMLElement) =>
	act(async () =>
		fireEvent.click(within(dialog).getByRole("button", { name: "Save" })),
	);

const cachedTitle = (
	queryClient: ReturnType<typeof createTestQueryClient>,
	queryKey: readonly unknown[],
) =>
	queryClient.getQueryData<InfiniteData<FeedPage>>(queryKey)?.pages[0]
		.results[0].title;

beforeEach(() => {
	vi.spyOn(circleServices, "listMemberships").mockResolvedValue({
		data: { circles: [] },
	});
	vi.spyOn(keepServices, "getCirclePeople").mockResolvedValue([
		jo,
		leo,
		sophia,
	]);
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("EditPostDialog", () => {
	it("is offered only to viewers who may change the post", async () => {
		await renderInFeeds(makeKeep({ can_delete: false }));

		expect(screen.queryByRole("button", { name: "Edit post" })).toBeNull();
	});

	it("starts from the post and saves its title, caption, date and people", async () => {
		const keep = makeKeep();
		const updateKeep = vi.spyOn(keepServices, "updateKeep").mockResolvedValue({
			id: keep.id,
			title: "Lake day",
			description: "Cold water",
			date_of_memory: "2026-06-15T15:30:00Z",
		});
		const success = vi.spyOn(toast, "success");
		const queryClient = await renderInFeeds(keep);

		const dialog = await openEditor();
		const title = within(dialog).getByLabelText("Title");
		const caption = within(dialog).getByLabelText("Caption");
		const date = within(dialog).getByLabelText("Date");
		expect(title).toHaveValue("Beach day");
		expect(caption).toHaveValue("First time in the ocean");
		// The memory's UTC day, like the calendar.
		expect(date).toHaveValue("2026-07-04");
		expect(
			within(dialog).getByRole("button", { name: "Sophia M" }),
		).toHaveAttribute("aria-pressed", "true");

		fireEvent.change(title, { target: { value: "  Lake day " } });
		fireEvent.change(caption, { target: { value: "Cold water" } });
		fireEvent.change(date, { target: { value: "2026-06-15" } });
		fireEvent.click(within(dialog).getByRole("button", { name: "Sophia M" }));
		fireEvent.click(within(dialog).getByRole("button", { name: "Leo" }));
		await save(dialog);

		expect(updateKeep).toHaveBeenCalledWith(keep.id, {
			title: "Lake day",
			description: "Cold water",
			// The new day keeps the memory's time of day.
			date_of_memory: "2026-06-15T15:30:00.000Z",
			people: ["p-leo"],
		});
		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		expect(success).toHaveBeenCalledWith("Post updated.", expect.anything());
		expect(screen.getByText("Lake day")).toBeInTheDocument();
		expect(screen.getByText("Cold water")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "Leo" })).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "Sophia M" })).toBeNull();
		expect(cachedTitle(queryClient, keepKeys.feed())).toBe("Lake day");
		// It moved days, so the feeds and the calendar fetch it again.
		expect(
			queryClient.getQueryState(keepKeys.feedDay("2026-07-04"))?.isInvalidated,
		).toBe(true);
		expect(
			queryClient.getQueryState(keepKeys.calendarMonth("2026-07"))
				?.isInvalidated,
		).toBe(true);
	});

	it("leaves the date out when the day didn't change", async () => {
		const keep = makeKeep();
		const updateKeep = vi.spyOn(keepServices, "updateKeep").mockResolvedValue({
			id: keep.id,
			title: "Beach day!",
			description: keep.description,
			date_of_memory: keep.date_of_memory,
		});
		const queryClient = await renderInFeeds(keep);

		const dialog = await openEditor();
		fireEvent.change(within(dialog).getByLabelText("Title"), {
			target: { value: "Beach day!" },
		});
		await save(dialog);

		expect(updateKeep).toHaveBeenCalledWith(keep.id, {
			title: "Beach day!",
			description: "First time in the ocean",
			people: ["p-sophia"],
		});
		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		expect(cachedTitle(queryClient, keepKeys.feedDay("2026-07-04"))).toBe(
			"Beach day!",
		);
		// Patched in place: same day, so nothing needs refetching.
		expect(
			queryClient.getQueryState(keepKeys.feedDay("2026-07-04"))?.isInvalidated,
		).toBe(false);
		expect(
			queryClient.getQueryState(keepKeys.calendarMonth("2026-07"))
				?.isInvalidated,
		).toBe(false);
	});

	it("needs a date to save", async () => {
		await renderInFeeds(makeKeep());

		const dialog = await openEditor();
		fireEvent.change(within(dialog).getByLabelText("Date"), {
			target: { value: "" },
		});

		expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
	});

	it("keeps the dialog open and says so when saving fails", async () => {
		vi.spyOn(keepServices, "updateKeep").mockRejectedValue(
			Object.assign(new Error("Forbidden"), { status: 403 }),
		);
		const error = vi.spyOn(toast, "error");
		const queryClient = await renderInFeeds(makeKeep());

		const dialog = await openEditor();
		fireEvent.change(within(dialog).getByLabelText("Title"), {
			target: { value: "Lake day" },
		});
		await save(dialog);

		await waitFor(() =>
			expect(error).toHaveBeenCalledWith(
				"Couldn't save your changes. Please try again.",
				expect.anything(),
			),
		);
		expect(
			screen.getByRole("dialog", { name: "Edit post" }),
		).toBeInTheDocument();
		expect(cachedTitle(queryClient, keepKeys.feed())).toBe("Beach day");
	});
});

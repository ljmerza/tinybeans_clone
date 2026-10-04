import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import {
	act,
	fireEvent,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import type { ReactNode } from "react";
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
import type { CirclePerson, FeedKeep } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

const sophia: CirclePerson = {
	id: "p-sophia",
	name: "Sophia M",
	kind: "child",
};
const leo: CirclePerson = { id: "p-leo", name: "Leo", kind: "member" };
const jo: CirclePerson = { id: "p-jo", name: "Grandma Jo", kind: "other" };

const makeKeep = (people?: FeedKeep["people"]): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Beach day",
	description: "",
	date_of_memory: "2026-07-04T00:00:00Z",
	created_at: "2026-07-05T10:00:00Z",
	media: [],
	reaction_count: 0,
	comment_count: 0,
	viewer_reaction: null,
	favorited: false,
	can_delete: false,
	recent_comments: [],
	...(people && { people }),
});

/** The post as the feed shows it: read from the cache, so saved tags show up. */
function CachedPost({ keepId }: { keepId: string }) {
	const { data } = useFeedKeep(keepId);
	return data ? <KeepFeedPost keep={data} /> : null;
}

function renderCachedPost(keep: FeedKeep) {
	vi.spyOn(keepServices, "getFeedKeep").mockResolvedValue(keep);
	const result = renderWithQueryClient(<CachedPost keepId={keep.id} />);
	result.queryClient.setQueryData(keepKeys.feedKeep(keep.id), keep);
	return result;
}

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

describe("KeepFeedPost people", () => {
	it("links each tagged name to their page", () => {
		renderWithQueryClient(<KeepFeedPost keep={makeKeep([sophia, jo])} />);

		expect(screen.getByText(/^With/)).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "Sophia M" })).toHaveAttribute(
			"href",
			"/people/p-sophia",
		);
		expect(screen.getByRole("link", { name: "Grandma Jo" })).toHaveAttribute(
			"href",
			"/people/p-jo",
		);
	});

	it("shows no people line when no one is tagged", () => {
		renderWithQueryClient(<KeepFeedPost keep={makeKeep()} />);

		expect(screen.queryByText(/^With/)).toBeNull();
		expect(screen.queryByRole("link")).toBeNull();
	});

	it("tags people from the Tag action and shows the saved names", async () => {
		const setKeepPeople = vi
			.spyOn(keepServices, "setKeepPeople")
			.mockResolvedValue({ people: [jo, leo] });
		renderCachedPost(makeKeep([sophia]));

		fireEvent.click(await screen.findByRole("button", { name: "Tag people" }));
		const dialog = await screen.findByRole("dialog", {
			name: "Who's in this post?",
		});
		const chip = (name: string) =>
			within(dialog).findByRole("button", { name });
		expect(await chip("Sophia M")).toHaveAttribute("aria-pressed", "true");
		expect(await chip("Leo")).toHaveAttribute("aria-pressed", "false");
		fireEvent.click(await chip("Sophia M"));
		fireEvent.click(await chip("Grandma Jo"));
		fireEvent.click(await chip("Leo"));
		await act(async () =>
			fireEvent.click(within(dialog).getByRole("button", { name: "Save" })),
		);

		expect(setKeepPeople).toHaveBeenCalledWith(makeKeep().id, [
			"p-jo",
			"p-leo",
		]);
		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		expect(
			screen.getByRole("link", { name: "Grandma Jo" }),
		).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "Sophia M" })).toBeNull();
	});

	it("adds someone new by name and picks them", async () => {
		const ana: CirclePerson = { id: "p-ana", name: "Aunt Ana", kind: "other" };
		const createPerson = vi
			.spyOn(keepServices, "createPerson")
			.mockResolvedValue(ana);
		const setKeepPeople = vi
			.spyOn(keepServices, "setKeepPeople")
			.mockResolvedValue({ people: [ana] });
		renderCachedPost(makeKeep());

		fireEvent.click(await screen.findByRole("button", { name: "Tag people" }));
		const dialog = await screen.findByRole("dialog");
		await within(dialog).findByRole("button", { name: "Leo" });
		const input = within(dialog).getByLabelText("Add someone");
		fireEvent.change(input, { target: { value: "  Aunt Ana " } });
		await act(async () =>
			fireEvent.click(within(dialog).getByRole("button", { name: "Add" })),
		);

		expect(createPerson).toHaveBeenCalledWith(1, "Aunt Ana");
		expect(
			await within(dialog).findByRole("button", { name: "Aunt Ana" }),
		).toHaveAttribute("aria-pressed", "true");
		expect(input).toHaveValue("");
		await act(async () =>
			fireEvent.click(within(dialog).getByRole("button", { name: "Save" })),
		);
		expect(setKeepPeople).toHaveBeenCalledWith(makeKeep().id, ["p-ana"]);
	});

	it("picks the existing person when their name is typed again", async () => {
		const createPerson = vi.spyOn(keepServices, "createPerson");
		renderCachedPost(makeKeep());

		fireEvent.click(await screen.findByRole("button", { name: "Tag people" }));
		const dialog = await screen.findByRole("dialog");
		await within(dialog).findByRole("button", { name: "Grandma Jo" });
		const input = within(dialog).getByLabelText("Add someone");
		fireEvent.change(input, { target: { value: "grandma jo" } });
		fireEvent.keyDown(input, { key: "Enter" });

		expect(
			within(dialog).getByRole("button", { name: "Grandma Jo" }),
		).toHaveAttribute("aria-pressed", "true");
		expect(createPerson).not.toHaveBeenCalled();
	});
});

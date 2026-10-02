import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

// The badge links to the milestones view; render that as a plain anchor.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
	...(await importOriginal<typeof import("@tanstack/react-router")>()),
	Link: ({
		children,
		to,
		search,
		...props
	}: {
		children?: ReactNode;
		to: string;
		search?: Record<string, string>;
	}) => (
		<a href={`${to}?${new URLSearchParams(search)}`} {...props}>
			{children}
		</a>
	),
}));

import type { FeedKeep } from "../types";
import { KeepFeedPost } from "./KeepFeedPost";

const makeKeep = (overrides: Partial<FeedKeep> = {}): FeedKeep => ({
	id: "11111111-1111-1111-1111-111111111111",
	circle: { id: 1, name: "Merza Family", slug: "merza-family" },
	created_by: 7,
	created_by_display_name: "Leo",
	title: "Look at her go",
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
	...overrides,
});

describe("milestone badge on a post", () => {
	it("shows the milestone, child and age, linking to the child's milestones", () => {
		renderWithQueryClient(
			<KeepFeedPost
				keep={makeKeep({
					milestone: {
						milestone_type: "first_steps",
						child: {
							id: "22222222-2222-2222-2222-222222222222",
							display_name: "Emma",
						},
						child_age: { years: 1, months: 2, days: 3 },
						age_at_milestone: "",
					},
				})}
			/>,
		);

		const badge = screen.getByRole("link", {
			name: "First steps · Emma, 1 yr 2 mo. See milestones",
		});
		expect(badge).toHaveTextContent("👣First steps · Emma, 1 yr 2 mo");
		expect(badge).toHaveAttribute(
			"href",
			"/milestones?child=22222222-2222-2222-2222-222222222222",
		);
	});

	it("links to every milestone when there's no child", () => {
		renderWithQueryClient(
			<KeepFeedPost
				keep={makeKeep({
					milestone: {
						milestone_type: "birthday",
						child: null,
						child_age: null,
						age_at_milestone: "",
					},
				})}
			/>,
		);

		expect(
			screen.getByRole("link", { name: "Birthday. See milestones" }),
		).toHaveAttribute("href", "/milestones?");
	});

	it("isn't shown on other posts", () => {
		renderWithQueryClient(
			<KeepFeedPost keep={makeKeep({ milestone: null })} />,
		);
		renderWithQueryClient(
			<KeepFeedPost keep={makeKeep({ id: "older-cache-entry" })} />,
		);

		expect(screen.queryByRole("link", { name: /See milestones/ })).toBeNull();
	});
});

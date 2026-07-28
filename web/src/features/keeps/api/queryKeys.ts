import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const keepKeysFactory = createQueryKeyFactory(["keeps"] as const);

export const keepKeys = {
	all: () => keepKeysFactory.root(),
	calendar: () => keepKeysFactory.tag("calendar"),
	calendarMonth: (month: string, circleSlug?: string) =>
		keepKeysFactory.tag("calendar", circleSlug ?? "all", month),
};

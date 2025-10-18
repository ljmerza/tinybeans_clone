import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const circleKeysFactory = createQueryKeyFactory(["circles"] as const);

export const circleKeys = {
	all: () => circleKeysFactory.root(),
	onboarding: () => circleKeysFactory.tag("onboarding"),
	list: () => circleKeysFactory.tag("list"),
	detail: (circleId: string | number) =>
		circleKeysFactory.tag("detail", circleId),
};

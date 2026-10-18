import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const aiAssistKeysFactory = createQueryKeyFactory(["aiAssist"] as const);

export const aiAssistKeys = {
	all: () => aiAssistKeysFactory.root(),
	settings: (circleId: number | string) =>
		aiAssistKeysFactory.tag("settings", String(circleId)),
};

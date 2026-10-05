import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const growthKeysFactory = createQueryKeyFactory(["growth"] as const);

export const growthKeys = {
	all: () => growthKeysFactory.root(),
	log: (personId: string) => growthKeysFactory.tag("log", personId),
	stats: (personId: string) => growthKeysFactory.tag("stats", personId),
};

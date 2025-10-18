import { createQueryKeyFactory } from "@/lib/query/queryKeys";

const circleKeysFactory = createQueryKeyFactory(["circles"] as const);

export const circleKeys = {
	all: () => circleKeysFactory.root(),
	onboarding: () => circleKeysFactory.tag("onboarding"),
	list: () => circleKeysFactory.tag("list"),
	detail: (circleId: string | number) =>
		circleKeysFactory.tag("detail", circleId),
	members: (circleId: string | number) =>
		circleKeysFactory.tag("members", circleId),
	invitations: (circleId: string | number) =>
		circleKeysFactory.tag("invitations", circleId),
	invitation: (circleId: string | number, invitationId: string) =>
		circleKeysFactory.tag("invitation", circleId, invitationId),
};

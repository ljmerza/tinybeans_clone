import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import type { CirclePerson } from "../types";

/** Case- and space-insensitive form of a name, for matching typed names. */
export function personNameKey(name: string) {
	return name.trim().toLocaleLowerCase();
}

/** In name order, like the server sorts them. */
function byName(a: CirclePerson, b: CirclePerson) {
	return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

/**
 * Everyone who can be tagged on a circle's posts: its children, members and
 * pets, and anyone members added by name. Fetched only once `circleId` is set.
 */
export function useCirclePeople(circleId: number | null) {
	return useQuery({
		queryKey: keepKeys.circlePeople(circleId ?? 0),
		queryFn: () => keepServices.getCirclePeople(circleId as number),
		enabled: circleId !== null,
	});
}

/**
 * Add someone without a profile (e.g. "Grandma Jo") to a circle, so they can
 * be tagged. They join the circle's cached people list straight away.
 */
export function useCreatePerson() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: ({ circleId, name }: { circleId: number; name: string }) =>
			keepServices.createPerson(circleId, name),
		meta: {
			toast: { error: { key: "pages.people.picker.add_failed" } },
		},
		onSuccess: (person, { circleId }) => {
			queryClient.setQueryData<CirclePerson[]>(
				keepKeys.circlePeople(circleId),
				(people) => (people ? [...people, person].sort(byName) : people),
			);
		},
	});
}

/** One person and their circle, for the person page. */
export function usePerson(personId: string) {
	return useQuery({
		queryKey: keepKeys.person(personId),
		queryFn: () => keepServices.getPerson(personId),
	});
}

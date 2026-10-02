import {
	type CircleMembershipSummary,
	useCircleMemberships,
} from "@/features/circles";
import { useMemo } from "react";

/** The circles the user is an admin of; only admins create and change albums. */
export function useAdminCircleIds(): ReadonlySet<number> {
	const { data } = useCircleMemberships();
	return useMemo(
		() =>
			new Set(
				((data ?? []) as CircleMembershipSummary[])
					.filter((membership) => membership.role === "admin")
					.map((membership) => membership.circle.id),
			),
		[data],
	);
}

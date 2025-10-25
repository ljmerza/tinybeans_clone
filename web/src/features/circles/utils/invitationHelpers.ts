import type { CircleInvitationSummary, CircleMemberSummary } from "../types";

export function normalizeString(
	value: string | null | undefined,
): string | null {
	return value?.trim().toLowerCase() ?? null;
}

export function normalizeId(
	value: number | string | null | undefined,
): string | null {
	if (value === null || value === undefined) return null;
	const stringValue = String(value).trim();
	return stringValue.length ? stringValue : null;
}

export function describeTimestamp(
	value: string | null,
	locale: string,
): string | null {
	if (!value) return null;
	try {
		const date = new Date(value);
		return new Intl.DateTimeFormat(locale, {
			dateStyle: "medium",
			timeStyle: "short",
		}).format(date);
	} catch {
		return value;
	}
}

export function sortInvitations(
	invitations: CircleInvitationSummary[] | undefined,
): CircleInvitationSummary[] {
	if (!invitations?.length) return [];
	return [...invitations].sort((a, b) => {
		const aTime = new Date(a.created_at).getTime();
		const bTime = new Date(b.created_at).getTime();
		return bTime - aTime;
	});
}

export function findMemberId(
	invitation: CircleInvitationSummary,
	members: CircleMemberSummary[] | undefined,
): string | null {
	const invitedId =
		normalizeId(invitation.invited_user?.id) ??
		normalizeId(invitation.invited_user_id);

	if (invitedId) {
		return invitedId;
	}

	if (!members?.length) return null;
	const targetEmail = normalizeString(invitation.email);

	for (const member of members) {
		const memberId = normalizeId(member.user.id);
		if (memberId && invitedId && memberId === invitedId) {
			return memberId;
		}
		const memberEmail = normalizeString(member.user.email);
		if (targetEmail && memberEmail === targetEmail) {
			return memberId ?? null;
		}
	}

	return null;
}

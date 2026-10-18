import type { ApiToken } from "./types";

/** A token as the API lists it, for tests. */
export function makeApiToken(overrides: Partial<ApiToken> = {}): ApiToken {
	return {
		id: "11111111-0000-0000-0000-000000000001",
		name: "Claude Code",
		display_prefix: "circ_abc1234",
		can_suggest: false,
		status: "active",
		created_by: { id: 1, display_name: "Leo" },
		created_at: "2026-10-01T12:00:00Z",
		expires_at: null,
		last_used_at: null,
		last_used_ip: null,
		revoked_at: null,
		revoked_reason: "",
		...overrides,
	};
}

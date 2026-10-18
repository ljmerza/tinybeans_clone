/**
 * API tokens feature types: per-circle bearer tokens for the agent API.
 */

export type ApiTokenStatus = "active" | "expired" | "revoked";

/** Why a token was revoked; empty while it isn't. */
export type ApiTokenRevokeReason =
	| ""
	| "manual"
	| "creator_not_admin"
	| "creator_removed"
	| "creator_inactive"
	| "creator_unverified"
	| "password_changed";

/** A token as admins see it: never its hash or plaintext. */
export interface ApiToken {
	id: string;
	name: string;
	/** The token's first 12 characters ("circ_" + 7), safe to show. */
	display_prefix: string;
	/** May propose milestones; fixed when created. */
	can_suggest: boolean;
	status: ApiTokenStatus;
	created_by: { id: number; display_name: string };
	created_at: string;
	/** Null means it never expires. */
	expires_at: string | null;
	last_used_at: string | null;
	last_used_ip: string | null;
	revoked_at: string | null;
	revoked_reason: ApiTokenRevokeReason;
}

/** GET /users/circles/<id>/api-tokens/ */
export interface ApiTokenList {
	/** False while the server operator has the agent API turned off. */
	agent_api_enabled: boolean;
	/** Newest first, including revoked and expired ones. */
	tokens: ApiToken[];
}

/** POST /users/circles/<id>/api-tokens/ */
export interface CreateApiTokenInput {
	name: string;
	can_suggest: boolean;
	/** ISO time at least an hour away, or null for no expiry. */
	expires_at: string | null;
	/** The emailed re-authentication code. */
	code: string;
}

/** The create response: the only time the plaintext is ever shown. */
export interface CreatedApiToken {
	token: ApiToken;
	plaintext: string;
}

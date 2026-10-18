/**
 * In-app AI feature types. The operator's provider URL, key and model are
 * never sent to the browser.
 */

/** Fixed codes from a scan or a connection test. */
export type AiStatusCode =
	| "ok"
	| "timeout"
	| "unreachable"
	| "auth_failed"
	| "model_missing"
	| "http_error"
	| "bad_response"
	| "provider_unavailable"
	| "pending_cap"
	| "time_limit"
	| "disabled";

/** GET /users/circles/<id>/ai-settings/ while the operator has AI set up. */
export interface AvailableAiSettings {
	available: true;
	enabled: boolean;
	acknowledged_at: string | null;
	last_run_at: string | null;
	last_success_at: string | null;
	/** Empty after a clean run; otherwise an `AiStatusCode`. */
	last_error: string;
	/** Suggestions waiting for an admin's review. */
	pending_count: number;
}

/** `{available: false}` (and nothing else) while the operator hasn't set AI up. */
export type AiSettings = { available: false } | AvailableAiSettings;

/** PUT /users/circles/<id>/ai-settings/ */
export interface UpdateAiSettingsInput {
	enabled: boolean;
	/** Required to turn it on: captions go to the operator's AI service. */
	acknowledge_data_sharing?: boolean;
}

/** POST /users/circles/<id>/ai-settings/test/ */
export interface AiConnectionTest {
	ok: boolean;
	code: string;
	latency_ms: number;
}

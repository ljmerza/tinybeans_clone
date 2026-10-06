export type PasswordStrength =
	| "too_short"
	| "weak"
	| "fair"
	| "good"
	| "strong";

/** Matches the 8-character minimum in passwordSchema and the signup API. */
const MIN_LENGTH = 8;

/**
 * Rough, advisory strength rating for the signup meter. It never blocks a
 * submit; passwordSchema and the API decide what is accepted.
 */
export function getPasswordStrength(password: string): PasswordStrength {
	if (password.length < MIN_LENGTH) return "too_short";

	const variety = [/[a-z]/, /[A-Z]/, /\d/, /[^a-zA-Z\d]/].filter((pattern) =>
		pattern.test(password),
	).length;

	const points =
		Number(password.length >= 12) +
		Number(password.length >= 16) +
		Number(variety >= 2) +
		Number(variety >= 3) +
		Number(variety >= 4);

	if (points >= 4) return "strong";
	if (points === 3) return "good";
	if (points === 2) return "fair";
	return "weak";
}

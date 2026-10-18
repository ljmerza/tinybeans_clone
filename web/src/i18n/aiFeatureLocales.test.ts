import { describe, expect, it } from "vitest";

import en from "./locales/en.json";
import es from "./locales/es.json";
import it_ from "./locales/it.json";

/** The namespaces added for API tokens, re-auth and AI milestone suggestions. */
const NAMESPACES = [
	"auth.reauth",
	"ai",
	"pages.circles.milestone_suggestions",
	"pages.circles.dashboard.milestone_review",
	"pages.circles.dashboard.ai_assist",
	"pages.circles.dashboard.api_tokens",
];
const ERROR_KEYS = [
	"errors.api_token_limit",
	"errors.reauth_invalid_code",
	"errors.reauth_rate_limited",
];

type Tree = { [key: string]: Tree | string };

function at(tree: Tree, path: string): Tree | string | undefined {
	return path
		.split(".")
		.reduce<Tree | string | undefined>(
			(node, part) => (typeof node === "object" ? node[part] : undefined),
			tree,
		);
}

function leafPaths(node: Tree | string, prefix: string): string[] {
	if (typeof node === "string") return [prefix];
	return Object.entries(node).flatMap(([key, child]) =>
		leafPaths(child, `${prefix}.${key}`),
	);
}

describe("AI feature locale keys", () => {
	const locales = { es, it: it_ } as Record<string, unknown>;

	it.each(NAMESPACES)("%s exists in English", (namespace) => {
		expect(typeof at(en as unknown as Tree, namespace)).toBe("object");
	});

	it.each(Object.keys(locales))(
		"%s has every English key, translated",
		(locale) => {
			const tree = locales[locale] as Tree;
			for (const path of [
				...NAMESPACES.flatMap((namespace) =>
					leafPaths(at(en as unknown as Tree, namespace) as Tree, namespace),
				),
				...ERROR_KEYS,
			]) {
				const value = at(tree, path);
				expect(typeof value, `${locale}: ${path}`).toBe("string");
				expect((value as string).trim(), `${locale}: ${path}`).not.toBe("");
			}
		},
	);

	it("English has the API error keys", () => {
		for (const path of ERROR_KEYS) {
			expect(typeof at(en as unknown as Tree, path)).toBe("string");
		}
	});
});

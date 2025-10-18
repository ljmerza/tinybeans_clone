/**
 * Testing utility for React Query hooks and components.
 */

import { createTestQueryClient } from "@/lib/query/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { type RenderOptions, render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

interface RenderWithQueryClientOptions extends RenderOptions {
	queryClient?: QueryClient;
	wrapper?: (children: ReactNode) => ReactNode;
}

export interface RenderWithQueryClientResult {
	queryClient: QueryClient;
}

export function renderWithQueryClient(
	ui: ReactElement,
	{
		queryClient: providedClient,
		wrapper,
		...options
	}: RenderWithQueryClientOptions = {},
) {
	const queryClient = providedClient ?? createTestQueryClient();

	const Providers = ({ children }: { children: ReactNode }) => {
		const content = wrapper ? wrapper(children) : children;
		return (
			<QueryClientProvider client={queryClient}>{content}</QueryClientProvider>
		);
	};

	const result = render(ui, { wrapper: Providers, ...options });

	return {
		...result,
		queryClient,
	} satisfies RenderWithQueryClientResult & typeof result;
}

import { RouterProvider, createRouter } from "@tanstack/react-router";
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "sonner";
import { ensureCsrfToken } from "./lib/csrf.ts";
import { refreshAccessToken } from "./modules/login/client.ts";

import * as TanStackQueryProvider from "./integrations/tanstack-query/root-provider.tsx";

import "./styles.css";
import "sonner/dist/styles.css";
import reportWebVitals from "./reportWebVitals.ts";

// Import the generated route tree
import { routeTree } from "./routeTree.gen";

const TanStackQueryProviderContext = TanStackQueryProvider.getContext();
const router = createRouter({
	routeTree,
	context: {
		...TanStackQueryProviderContext,
	},
	defaultPreload: "intent",
	scrollRestoration: true,
	defaultStructuralSharing: true,
	defaultPreloadStaleTime: 0,
});

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}

const rootElement = document.getElementById("app");
if (rootElement && !rootElement.innerHTML) {
	const root = ReactDOM.createRoot(rootElement);

	// Initialize app: fetch CSRF token first, then try to restore session
	ensureCsrfToken()
		.then(() => {
			return refreshAccessToken();
		})
		.then(() => {
			root.render(
				<StrictMode>
					<TanStackQueryProvider.Provider {...TanStackQueryProviderContext}>
						<RouterProvider router={router} />
						<Toaster richColors position="top-right" />
					</TanStackQueryProvider.Provider>
				</StrictMode>,
			);
		});
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

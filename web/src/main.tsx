import { QueryClient } from "@tanstack/react-query";
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { AppBootstrap } from "./components/AppBootstrap";
import { AppProviders } from "./components/AppProviders";

import "./styles.css";
import "sonner/dist/styles.css";
import "./i18n/config"; // Initialize i18n
import reportWebVitals from "./reportWebVitals.ts";

// Create QueryClient instance
const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 1000 * 60 * 5, // 5 minutes
			retry: false,
		},
	},
});

// Expose queryClient for TanStack Devtools
if (typeof window !== "undefined") {
	(
		window as Window & { __TANSTACK_QUERY_CLIENT__?: QueryClient }
	).__TANSTACK_QUERY_CLIENT__ = queryClient;
}

const rootElement = document.getElementById("app");
if (rootElement && !rootElement.innerHTML) {
	const root = ReactDOM.createRoot(rootElement);

	root.render(
		<StrictMode>
			<AppBootstrap>
				<AppProviders queryClient={queryClient} />
			</AppBootstrap>
		</StrictMode>,
	);
}

reportWebVitals();

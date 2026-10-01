import { createQueryClient } from "@/lib/query/queryClient";
import type { QueryClient } from "@tanstack/react-query";
import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { AppBootstrap } from "./components/AppBootstrap";

import "./styles.css";
import "sonner/dist/styles.css";
import { i18nReady } from "./i18n/config"; // Initialize i18n
import reportWebVitals from "./reportWebVitals.ts";

// Create QueryClient instance
const queryClient = createQueryClient();

// Expose queryClient for TanStack Devtools
if (typeof window !== "undefined") {
	(
		window as Window & { __TANSTACK_QUERY_CLIENT__?: QueryClient }
	).__TANSTACK_QUERY_CLIENT__ = queryClient;
}

const rootElement = document.getElementById("app");
if (rootElement && !rootElement.innerHTML) {
	const root = ReactDOM.createRoot(rootElement);

	// Hold the first render until the startup language is loaded so Spanish or
	// Italian users never see an English first paint. English is bundled, so
	// for English users this resolves without any request.
	void i18nReady.then(() => {
		root.render(
			<StrictMode>
				<AppBootstrap queryClient={queryClient} />
			</StrictMode>,
		);
	});
}

reportWebVitals();

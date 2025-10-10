import {
	type ReactNode,
	createContext,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useState,
} from "react";

type ThemePreference = "light" | "dark" | "system";
type ThemeValue = "light" | "dark";

interface ThemeContextValue {
	preference: ThemePreference;
	resolvedTheme: ThemeValue;
	setPreference: (preference: ThemePreference) => void;
}

const STORAGE_KEY = "tinybeans.themePreference";

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const isBrowser = () =>
	typeof window !== "undefined" && typeof document !== "undefined";

const readStoredPreference = (): ThemePreference => {
	if (!isBrowser()) return "system";

	const stored = window.localStorage.getItem(STORAGE_KEY);
	if (stored === "light" || stored === "dark" || stored === "system") {
		return stored;
	}

	return "system";
};

const getSystemTheme = (): ThemeValue => {
	if (!isBrowser()) return "light";
	return window.matchMedia("(prefers-color-scheme: dark)").matches
		? "dark"
		: "light";
};

const applyThemeClass = (theme: ThemeValue) => {
	if (!isBrowser()) return;

	const root = document.documentElement;
	root.classList.toggle("dark", theme === "dark");
	root.style.colorScheme = theme;
};

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [preference, setPreferenceState] = useState<ThemePreference>(() =>
		readStoredPreference(),
	);
	const [resolvedTheme, setResolvedTheme] = useState<ThemeValue>(() => {
		const stored = readStoredPreference();
		const initialTheme = stored === "system" ? getSystemTheme() : stored;
		applyThemeClass(initialTheme);
		return initialTheme;
	});

	useEffect(() => {
		if (!isBrowser()) return;

		window.localStorage.setItem(STORAGE_KEY, preference);
	}, [preference]);

	useEffect(() => {
		if (!isBrowser()) return;

		const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

		const computeTheme = (): ThemeValue =>
			preference === "system"
				? mediaQuery.matches
					? "dark"
					: "light"
				: preference;

		const updateTheme = () => {
			const nextTheme = computeTheme();
			setResolvedTheme(nextTheme);
			applyThemeClass(nextTheme);
		};

		updateTheme();

		if (preference === "system") {
			const mediaListener = () => updateTheme();
			mediaQuery.addEventListener("change", mediaListener);
			return () => mediaQuery.removeEventListener("change", mediaListener);
		}

		return undefined;
	}, [preference]);

	const setPreference = useCallback((nextPreference: ThemePreference) => {
		setPreferenceState(nextPreference);
	}, []);

	const value = useMemo(
		() => ({
			preference,
			resolvedTheme,
			setPreference,
		}),
		[preference, resolvedTheme, setPreference],
	);

	return (
		<ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
	);
}

export const useTheme = () => {
	const context = useContext(ThemeContext);
	if (context === undefined) {
		throw new Error("useTheme must be used within a ThemeProvider");
	}

	return context;
};

export type { ThemePreference, ThemeValue, ThemeContextValue };

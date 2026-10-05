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

/** Color palettes; must match `ColorTheme` on the Django user model. */
const COLOR_THEMES = [
	"default",
	"rose",
	"peach",
	"sage",
	"sky",
	"lavender",
	"midnight",
] as const;
type ColorTheme = (typeof COLOR_THEMES)[number];

interface ThemeContextValue {
	preference: ThemePreference;
	resolvedTheme: ThemeValue;
	setPreference: (preference: ThemePreference) => void;
	colorTheme: ColorTheme;
	setColorTheme: (colorTheme: ColorTheme) => void;
}

// index.html reads these keys before first paint; keep the two in sync.
const STORAGE_KEY = "circles.themePreference";
const COLOR_THEME_STORAGE_KEY = "circles.colorTheme";

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

const isColorTheme = (value: unknown): value is ColorTheme =>
	typeof value === "string" &&
	(COLOR_THEMES as readonly string[]).includes(value);

const readStoredColorTheme = (): ColorTheme => {
	if (!isBrowser()) return "default";

	const stored = window.localStorage.getItem(COLOR_THEME_STORAGE_KEY);
	return isColorTheme(stored) ? stored : "default";
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

const applyColorTheme = (colorTheme: ColorTheme) => {
	if (!isBrowser()) return;

	const root = document.documentElement;
	if (colorTheme === "default") {
		root.removeAttribute("data-color-theme");
	} else {
		root.setAttribute("data-color-theme", colorTheme);
	}
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
	const [colorTheme, setColorThemeState] = useState<ColorTheme>(() =>
		readStoredColorTheme(),
	);

	useEffect(() => {
		if (!isBrowser()) return;

		window.localStorage.setItem(COLOR_THEME_STORAGE_KEY, colorTheme);
		applyColorTheme(colorTheme);
	}, [colorTheme]);

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

	const setColorTheme = useCallback((nextColorTheme: ColorTheme) => {
		setColorThemeState(nextColorTheme);
	}, []);

	const value = useMemo(
		() => ({
			preference,
			resolvedTheme,
			setPreference,
			colorTheme,
			setColorTheme,
		}),
		[preference, resolvedTheme, setPreference, colorTheme, setColorTheme],
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

export { COLOR_THEMES, isColorTheme };
export type { ColorTheme, ThemePreference, ThemeValue, ThemeContextValue };

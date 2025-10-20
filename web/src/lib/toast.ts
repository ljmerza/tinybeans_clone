import { toast } from "sonner";

export type ToastLevel = "success" | "info" | "warning" | "error";

type ToastPayload = {
	message: string;
	level?: ToastLevel;
	id?: string | number;
};

const levelAlias: Record<string, ToastLevel> = {
	success: "success",
	info: "info",
	information: "info",
	warn: "warning",
	warning: "warning",
	error: "error",
	fail: "error",
	failure: "error",
};

export function showToast({ message, level = "info", id }: ToastPayload) {
	const normalizedLevel = levelAlias[level] ?? level;
	const toastId = id ?? message;
	const baseOptions = {
		id: toastId,
		duration: 3000,
		dismissible: true,
		onClick: () => toast.dismiss(toastId),
	};

	switch (normalizedLevel) {
		case "success":
			toast.success(message, baseOptions);
			break;
		case "warning":
			toast.warning(message, baseOptions);
			break;
		case "error":
			toast.error(message, baseOptions);
			break;
		default:
			toast(message, baseOptions);
	}
}

export function extractMessage(data: unknown): string | undefined {
	if (!data) return undefined;

	if (typeof data === "string") {
		return data;
	}

	if (Array.isArray(data)) {
		for (const entry of data) {
			const message = extractMessage(entry);
			if (message) return message;
		}
		return undefined;
	}

	if (typeof data === "object") {
		const record = data as Record<string, unknown>;
		const knownKeys = ["message", "detail", "error", "toast_message"] as const;
		for (const key of knownKeys) {
			const value = record[key];
			if (typeof value === "string" && value.trim().length) {
				return value;
			}
		}
		for (const value of Object.values(record)) {
			const message = extractMessage(value);
			if (message) return message;
		}
	}

	return undefined;
}

export function extractLevel(data: unknown): ToastLevel | undefined {
	if (!data || typeof data !== "object") return undefined;
	const record = data as Record<string, unknown>;
	const keys = [
		"toast_level",
		"message_level",
		"status",
		"toast_type",
		"level",
	];
	for (const key of keys) {
		const value = record[key];
		if (typeof value === "string") {
			const normalized = value.toLowerCase();
			if (normalized in levelAlias) {
				return levelAlias[normalized];
			}
		}
	}
	return undefined;
}

export function mapStatusToLevel(status: number): ToastLevel {
	if (status >= 500) return "error";
	if (status >= 400) return "error";
	if (status >= 300) return "info";
	if (status >= 200) return "success";
	return "info";
}

export function showApiToast(
	data: unknown,
	status: number,
	options: { fallbackMessage?: string; toastId?: string } = {},
) {
	const message = extractMessage(data) ?? options.fallbackMessage;
	if (!message) return;
	const explicitLevel = extractLevel(data);
	const level = explicitLevel ?? mapStatusToLevel(status);
	showToast({ message, level, id: options.toastId });
}

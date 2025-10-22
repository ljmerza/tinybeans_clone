import i18n from "@/i18n/config";
import {
	combineMessages,
	inferSeverity,
	translateMessages,
} from "@/i18n/notificationUtils";
import { showToast, type ToastLevel } from "@/lib/toast";
import type { ApiMessage } from "@/types";
import type { Mutation } from "@tanstack/react-query";
import { MutationCache } from "@tanstack/react-query";

interface ToastDescriptor {
	key?: string;
	message?: string;
	params?: Record<string, unknown>;
	level?: ToastLevel;
	status?: number;
	suppress?: boolean;
}

interface ToastMeta {
	useResponseMessages?: boolean;
	success?: ToastDescriptor;
	error?: ToastDescriptor;
}

interface MutationAnalyticsMeta {
	analyticsEvent?: string;
	toast?: ToastMeta;
}

interface HttpErrorLike extends Error {
	status?: number;
	messages?: ApiMessage[];
	data?: unknown;
}

const translate = (key?: string, params?: Record<string, unknown>) => {
	if (!key) return undefined;
	return i18n.t(key, { defaultValue: key, ...(params ?? {}) });
};

const resolveLevel = (
	descriptor: ToastDescriptor | undefined,
	defaultStatus: number,
): ToastLevel => {
	if (descriptor?.level) return descriptor.level;
	return inferSeverity(descriptor?.status ?? defaultStatus);
};

const extractMessages = (value: unknown): ApiMessage[] | undefined => {
	if (!value || typeof value !== "object") return undefined;

	const record = value as Record<string, unknown>;

	if (Array.isArray(record.messages)) {
		return record.messages as ApiMessage[];
	}

	if (record.data && typeof record.data === "object") {
		const nested = record.data as Record<string, unknown>;
		if (Array.isArray(nested.messages)) {
			return nested.messages as ApiMessage[];
		}
	}

	return undefined;
};

const showMessages = (
	messages: ApiMessage[] | undefined,
	status: number,
): boolean => {
	if (!messages || messages.length === 0) return false;

	const translated = translateMessages(messages, i18n.t.bind(i18n));
	const message = combineMessages(translated);
	if (!message) return false;

	showToast({ message, level: inferSeverity(status) });
	return true;
};

const showDescriptor = (descriptor: ToastDescriptor | undefined) => {
	if (!descriptor || descriptor.suppress) return false;

	const message =
		descriptor.message ?? translate(descriptor.key, descriptor.params);

	if (!message) return false;

	const status = descriptor.status ?? 200;
	const level = resolveLevel(descriptor, status);

	showToast({ message, level });
	return true;
};

const handleSuccessToast = (
	mutation: Mutation<unknown, unknown, unknown>,
	data: unknown,
) => {
	const meta = (mutation.meta ?? {}) as MutationAnalyticsMeta;
	const toastMeta = meta.toast;
	if (!toastMeta) return;

	const descriptor = toastMeta.success;
	if (descriptor?.suppress) return;

	const usedResponseMessages =
		toastMeta.useResponseMessages &&
		showMessages(extractMessages(data), descriptor?.status ?? 200);

	if (!usedResponseMessages) {
		void showDescriptor(descriptor);
	}
};

const handleErrorToast = (
	mutation: Mutation<unknown, unknown, unknown>,
	error: unknown,
) => {
	const meta = (mutation.meta ?? {}) as MutationAnalyticsMeta;
	const toastMeta = meta.toast;
	if (!toastMeta) return;

	const descriptor = toastMeta.error;
	if (descriptor?.suppress) return;

	const httpError = error as HttpErrorLike;

	const usedResponseMessages =
		toastMeta.useResponseMessages &&
		showMessages(
			httpError?.messages ?? extractMessages(httpError?.data),
			descriptor?.status ?? (httpError?.status ?? 400),
		);

	if (usedResponseMessages) return;

	if (descriptor?.message || descriptor?.key) {
		void showDescriptor({
			...descriptor,
			status: descriptor.status ?? httpError?.status ?? 400,
		});
		return;
	}

	if (httpError?.message) {
		showToast({
			message: httpError.message,
			level: resolveLevel(descriptor, httpError.status ?? 400),
		});
	}
};

type MutationCacheOptions = ConstructorParameters<typeof MutationCache>[0];

export function createMutationCache(
	config: MutationCacheOptions = {},
): MutationCache {
	return new MutationCache({
		...config,
		onSuccess: (data, variables, context, mutation) => {
			config.onSuccess?.(data, variables, context, mutation);
			handleSuccessToast(mutation, data);
		},
		onError: (error, variables, context, mutation) => {
			config.onError?.(error, variables, context, mutation);
			handleErrorToast(mutation, error);
		},
	});
}

export type { MutationAnalyticsMeta };

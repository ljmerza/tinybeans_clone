import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDropzone, type FileRejection } from "react-dropzone";
import {
	useMutation,
	useQueries,
	useQueryClient,
	type UseQueryResult,
} from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { showToast } from "@/lib/toast";
import { keepsServices } from "../api/services";
import { keepsKeys } from "../api/queryKeys";
import type {
	MediaUploadRecord,
	MediaUploadState,
	MediaUploadStatusRecord,
	MediaUrls,
} from "../types";

interface UploadItem {
	clientId: string;
	file: File;
	uploadId?: string;
	status: MediaUploadState;
	progress: number;
	error?: string;
	urls?: MediaUrls | null;
	lastNotifiedStatus?: MediaUploadState;
	keepId?: string;
}

interface CircleMediaUploaderProps {
	keepId?: string;
	circleId: number | string;
	disabled?: boolean;
	onUploadComplete?: (upload: MediaUploadStatusRecord) => void;
	onUploadFailed?: (upload: MediaUploadStatusRecord) => void;
}

const ACCEPTED_IMAGE_TYPES = {
	"image/jpeg": [],
	"image/png": [],
	"image/gif": [],
	"image/webp": [],
};

function formatBytes(bytes: number): string {
	const units = ["B", "KB", "MB", "GB"];
	let value = bytes;
	let unitIndex = 0;

	while (value >= 1024 && unitIndex < units.length - 1) {
		value /= 1024;
		unitIndex += 1;
	}

	return `${value.toFixed(value < 10 && unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`;
}

function mapStatusToProgress(status: MediaUploadState | undefined) {
	switch (status) {
		case "pending":
			return 0;
		case "validating":
			return 25;
		case "processing":
			return 60;
		case "completed":
			return 100;
		case "failed":
			return 0;
		default:
			return 0;
	}
}

export function CircleMediaUploader({
	keepId,
	circleId,
	disabled = false,
	onUploadComplete,
	onUploadFailed,
}: CircleMediaUploaderProps) {
	const { t } = useTranslation();
	const queryClient = useQueryClient();

	const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);

	const uploadMutation = useMutation({
		mutationFn: async ({
			clientId,
			file,
		}: {
			clientId: string;
			file: File;
		}) => {
			const response = await keepsServices.uploadMedia({
				keepId: keepId as string,
				file,
				mediaType: "photo",
			});
			return { response, clientId };
		},
		onSuccess: ({ response, clientId }) => {
			const upload = response.data;
			setUploadItems((current) =>
				current.map((item) => {
					if (item.clientId !== clientId) {
						return item;
					}
					const nextStatus = upload?.status ?? item.status;
					return {
						...item,
						uploadId: upload?.id ?? item.uploadId,
						status: nextStatus,
						progress:
							upload?.status === "completed"
								? 100
								: upload?.status
									? mapStatusToProgress(upload.status)
									: item.progress,
						error: "",
						keepId: upload?.keep ?? item.keepId ?? keepId,
					};
				}),
			);
		},
		onError: (error, { clientId }) => {
			const message =
				error instanceof Error ? error.message : t("errors.upload_failed");
			setUploadItems((current) =>
				current.map((item) =>
					item.clientId === clientId
						? { ...item, status: "failed", error: message }
						: item,
				),
			);
			showToast({ message, level: "error" });
		},
	});

	const queueUpload = useCallback(
		(file: File) => {
		const clientId = `${createClientId()}-${file.name}`;
			setUploadItems((current) => [
				...current,
				{
					clientId,
					file,
					status: "pending",
					progress: 0,
					keepId,
				},
			]);
			uploadMutation.mutate({ clientId, file });
		},
		[keepId, uploadMutation],
	);

	const onDropAccepted = useCallback(
		(files: File[]) => {
			files.forEach((file) => queueUpload(file));
		},
		[queueUpload],
	);

	const onDropRejected = useCallback(
		(fileRejections: FileRejection[]) => {
			fileRejections.forEach((rejection) => {
				const firstError = rejection.errors[0];
				showToast({
					message:
						firstError?.message ??
						t("errors.invalid_file_type", {
							allowedTypes: "image/jpeg, image/png, image/gif, image/webp",
						}),
					level: "error",
				});
			});
		},
		[t],
	);

	const {
		getRootProps,
		getInputProps,
		isDragActive,
		open: openFileBrowser,
	} = useDropzone({
		onDropAccepted,
		onDropRejected,
		multiple: true,
		accept: ACCEPTED_IMAGE_TYPES,
		disabled: disabled || !keepId || uploadMutation.isPending,
		noKeyboard: true,
		noClick: true,
	});

	const activeUploadIds = useMemo(
		() =>
			uploadItems
				.filter(
					(item) =>
						item.uploadId &&
						item.status !== "completed" &&
						item.status !== "failed",
				)
				.map((item) => item.uploadId as string),
		[uploadItems],
	);

	const statusQueries = useQueries({
		queries: activeUploadIds.map((uploadId) => ({
			queryKey: keepsKeys.uploadStatus(uploadId),
			queryFn: () => keepsServices.getUploadStatus(uploadId),
			refetchInterval: 2_000,
			select: (response: ReturnType<typeof keepsServices.getUploadStatus>) =>
				response,
		})),
	});

	useEffect(() => {
		const notifications: Array<{
			type: "completed" | "failed";
			upload: MediaUploadStatusRecord;
			item: UploadItem;
		}> = [];

		statusQueries.forEach(
			(query: UseQueryResult<Awaited<ReturnType<typeof keepsServices.getUploadStatus>>, unknown>) => {
				const payload = query.data?.data;
				if (!payload) {
					return;
				}

				setUploadItems((current) =>
					current.map((item) => {
						if (item.uploadId !== payload.id) {
							return item;
						}
						const statusChanged =
							payload.status && item.status !== payload.status;
						const nextProgress =
							payload.progress_percentage ?? mapStatusToProgress(payload.status);
						const nextItem: UploadItem = {
							...item,
							status: payload.status ?? item.status,
							progress: nextProgress ?? item.progress,
							error: payload.error_message ?? "",
							urls: payload.media_urls,
							keepId: payload.keep ?? item.keepId,
							lastNotifiedStatus: statusChanged
								? (payload.status as MediaUploadState)
								: item.lastNotifiedStatus,
						};

						if (statusChanged && payload.status) {
							if (payload.status === "completed") {
								notifications.push({
									type: "completed",
									upload: payload,
									item: nextItem,
								});
							} else if (payload.status === "failed") {
								notifications.push({
									type: "failed",
									upload: payload,
									item: nextItem,
								});
							}
						}

						return nextItem;
					}),
				);
			},
		);

		notifications.forEach(({ type, upload, item }) => {
			if (type === "completed") {
				showToast({
					message: t("pages.circles.dashboard.media.toasts.completed", {
						filename: item.file.name,
					}),
					level: "success",
				});
				if (upload.keep) {
					queryClient.invalidateQueries({
						queryKey: keepsKeys.detail(upload.keep),
					}).catch(() => {});
				}
				onUploadComplete?.(upload);
			} else if (type === "failed") {
				showToast({
					message: t("pages.circles.dashboard.media.toasts.failed", {
						filename: item.file.name,
					}),
					level: "error",
				});
				onUploadFailed?.(upload);
			}
		});
	}, [statusQueries, t, queryClient, onUploadComplete, onUploadFailed]);

	const handleRemoveItem = useCallback((clientId: string) => {
		setUploadItems((current) =>
			current.filter((item) => item.clientId !== clientId),
		);
	}, []);

	const uploadIsDisabled = disabled || !keepId;

	return (
		<div className="space-y-4">
			<div
				{...getRootProps({
					className:
						"border-dashed border-2 rounded-lg p-6 flex flex-col items-center justify-center text-center transition-colors cursor-pointer bg-muted/20 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
					"data-disabled": uploadIsDisabled ? "" : undefined,
				})}
			>
				<input {...getInputProps()} aria-label={t("pages.circles.dashboard.media.uploader.input_label")} />
				<div className="flex flex-col items-center gap-3">
					<p className="text-sm font-medium text-foreground">
						{uploadIsDisabled
							? t("pages.circles.dashboard.media.uploader.disabled")
							: isDragActive
								? t("pages.circles.dashboard.media.uploader.drop_active")
								: t("pages.circles.dashboard.media.uploader.prompt")}
					</p>
					{!uploadIsDisabled && (
						<Button
							type="button"
							variant="secondary"
							size="sm"
							onClick={(event) => {
								event.preventDefault();
								openFileBrowser();
							}}
						>
							{t("pages.circles.dashboard.media.uploader.browse")}
						</Button>
					)}
					<p className="text-xs text-muted-foreground">
						{t("pages.circles.dashboard.media.uploader.helper")}
					</p>
				</div>
			</div>

			{uploadItems.length > 0 && (
				<div className="space-y-3">
					<h4 className="text-sm font-semibold text-foreground">
						{t("pages.circles.dashboard.media.uploader.queue_title")}
					</h4>
					<ul className="space-y-2">
						{uploadItems.map((item) => (
							<li
								key={item.clientId}
								className="border border-border rounded-md p-3 bg-background shadow-xs"
							>
								<div className="flex flex-wrap items-center justify-between gap-3">
									<div>
										<p className="text-sm font-medium text-foreground">
											{item.file.name}
										</p>
										<p className="text-xs text-muted-foreground">
											{formatBytes(item.file.size)} ·{" "}
											{t(
												`pages.circles.dashboard.media.status.${item.status}`,
											)}
										</p>
									</div>
									<div className="flex items-center gap-2">
										<Badge variant="outline">
											{t(
												`pages.circles.dashboard.media.status.${item.status}`,
											)}
										</Badge>
										<Button
											variant="ghost"
											size="sm"
											onClick={() => handleRemoveItem(item.clientId)}
										>
											{t("common.remove")}
										</Button>
									</div>
								</div>
								<div className="mt-3 h-2 w-full rounded-full bg-muted">
									<div
										className="h-full rounded-full bg-primary transition-all"
										style={{
											width: `${Math.min(Math.max(item.progress, 0), 100)}%`,
										}}
									/>
								</div>
								{item.error && (
									<p className="mt-2 text-xs text-destructive">{item.error}</p>
								)}
							</li>
						))}
					</ul>
				</div>
			)}
		</div>
	);
}
function createClientId() {
	if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
		return crypto.randomUUID();
	}
	return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

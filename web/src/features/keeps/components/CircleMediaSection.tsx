import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/Card";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Layout } from "@/components";
import { showToast } from "@/lib/toast";
import { keepsKeys } from "../api/queryKeys";
import { keepsServices } from "../api/services";
import { useCircleKeeps } from "../hooks/useCircleKeeps";
import { useKeepDetail } from "../hooks/useKeepDetail";
import { CircleMediaUploader } from "./CircleMediaUploader";
import { MediaGallery } from "./MediaGallery";

interface CircleMediaSectionProps {
	circleId: number | string;
	isAdmin: boolean;
}

export function CircleMediaSection({
	circleId,
	isAdmin,
}: CircleMediaSectionProps) {
	const { t } = useTranslation();
	const queryClient = useQueryClient();

	const keepsQuery = useCircleKeeps(circleId);
	const keeps = keepsQuery.data ?? [];

	const [selectedKeepId, setSelectedKeepId] = useState<string | undefined>();

	useEffect(() => {
		if (!keeps.length) {
			setSelectedKeepId(undefined);
			return;
		}
		if (!selectedKeepId || !keeps.some((keep) => keep.id === selectedKeepId)) {
			setSelectedKeepId(keeps[0]?.id);
		}
	}, [keeps, selectedKeepId]);

	const keepDetailQuery = useKeepDetail(selectedKeepId);
	const mediaFiles = keepDetailQuery.data?.media_files ?? [];
	const isGalleryLoading = keepDetailQuery.isLoading || keepDetailQuery.isFetching;

	const circlePk = useMemo(() => {
		const parsed = Number(circleId);
		return Number.isNaN(parsed) ? null : parsed;
	}, [circleId]);

	const createKeepMutation = useMutation({
		mutationFn: async () => {
			const title = t("pages.circles.dashboard.media.new_keep_title", {
				date: new Date().toLocaleDateString(),
			});
			return keepsServices.createKeep({
				circle: circlePk ?? String(circleId),
				keep_type: "media",
				title,
				description: t(
					"pages.circles.dashboard.media.new_keep_description",
				),
				is_public: true,
			});
		},
		onSuccess: (keep) => {
			showToast({
				message: t("pages.circles.dashboard.media.toasts.keep_created", {
					title: keep.title,
				}),
				level: "success",
			});
			queryClient
				.invalidateQueries({
					queryKey: keepsKeys.circleMedia(circleId),
				})
				.catch(() => {});
			setSelectedKeepId(keep.id);
		},
		onError: () => {
			showToast({
				message: t("errors.upload_failed"),
				level: "error",
			});
		},
	});

	const [deletingId, setDeletingId] = useState<number | null>(null);

	const deleteMediaMutation = useMutation({
		mutationFn: (mediaId: number) => keepsServices.deleteMedia(mediaId),
		onMutate: (mediaId) => {
			setDeletingId(mediaId);
		},
		onSuccess: () => {
			showToast({
				message: t("pages.circles.dashboard.media.toasts.media_deleted"),
				level: "success",
			});
			keepDetailQuery.refetch().catch(() => {});
		},
		onError: () => {
			showToast({
				message: t("errors.upload_failed"),
				level: "error",
			});
		},
		onSettled: () => {
			setDeletingId(null);
		},
	});

	if (!isAdmin) {
		return null;
	}

	return (
		<section className="space-y-6">
			<Card>
				<CardHeader className="space-y-2">
					<CardTitle className="text-lg">
						{t("pages.circles.dashboard.media.title")}
					</CardTitle>
					<CardDescription>
						{t("pages.circles.dashboard.media.description")}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					<div className="flex flex-wrap items-center gap-3">
						<div className="space-y-1">
							<label className="text-sm font-medium text-foreground">
								{t("pages.circles.dashboard.media.select_keep_label")}
							</label>
							<div className="flex items-center gap-2">
								<Select
									value={selectedKeepId}
									onValueChange={setSelectedKeepId}
									disabled={
										keepsQuery.isLoading ||
										keeps.length === 0 ||
										createKeepMutation.isPending
									}
								>
									<SelectTrigger className="min-w-[220px]">
										<SelectValue
											placeholder={t(
												"pages.circles.dashboard.media.select_keep_placeholder",
											)}
										/>
									</SelectTrigger>
									<SelectContent>
										{keeps.map((keep) => (
											<SelectItem key={keep.id} value={keep.id}>
												{keep.title || keep.id}
											</SelectItem>
										))}
									</SelectContent>
								</Select>
								<Button
									type="button"
									variant="outline"
									size="sm"
									onClick={() => createKeepMutation.mutate()}
									disabled={createKeepMutation.isPending || circlePk == null}
								>
									{createKeepMutation.isPending
										? t("pages.circles.dashboard.media.creating_keep")
										: t("pages.circles.dashboard.media.create_keep")}
								</Button>
							</div>
							{keepsQuery.isLoading ? (
								<Layout.Loading
									showHeader={false}
									layout="inline"
									spinnerSize="xs"
									message={t("common.loading")}
								/>
							) : null}
						</div>
					</div>

					<CircleMediaUploader
						keepId={selectedKeepId}
						circleId={circleId}
						disabled={keeps.length === 0 || createKeepMutation.isPending}
						onUploadComplete={() => keepDetailQuery.refetch().catch(() => {})}
					/>
				</CardContent>
			</Card>

			<MediaGallery
				mediaFiles={mediaFiles}
				isLoading={isGalleryLoading}
				onRefresh={() => keepDetailQuery.refetch()}
				onDelete={
					mediaFiles.length > 0
						? (mediaId) => deleteMediaMutation.mutate(mediaId)
						: undefined
				}
				deletingIds={
					deletingId != null ? new Set<number>([deletingId]) : undefined
				}
			/>
		</section>
	);
}

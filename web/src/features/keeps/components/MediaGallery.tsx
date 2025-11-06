import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "@/components/Card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Layout } from "@/components";
import type { KeepMediaFile } from "../types";

interface MediaGalleryProps {
	mediaFiles: KeepMediaFile[];
	isLoading?: boolean;
	onRefresh?: () => void;
	onDelete?: (mediaId: number) => void;
	deletingIds?: Set<number>;
}

function resolveImageUrl(media: KeepMediaFile) {
	return (
		media.urls?.thumbnail ??
		media.urls?.gallery ??
		media.urls?.original ??
		""
	);
}

export function MediaGallery({
	mediaFiles,
	isLoading = false,
	onRefresh,
	onDelete,
	deletingIds,
}: MediaGalleryProps) {
	const { t } = useTranslation();

	const hasMedia = mediaFiles.length > 0;

	return (
		<Card>
			<CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
				<CardTitle className="text-base font-semibold">
					{t("pages.circles.dashboard.media.gallery.title")}
				</CardTitle>
				<div className="flex items-center gap-2">
					{onRefresh ? (
						<Button
							variant="secondary"
							size="sm"
							onClick={() => onRefresh()}
							disabled={isLoading}
						>
							{t("pages.circles.dashboard.media.gallery.refresh")}
						</Button>
					) : null}
				</div>
			</CardHeader>
			<CardContent>
				{isLoading ? (
					<Layout.Loading
						showHeader={false}
						layout="inline"
						spinnerSize="sm"
						message={t("common.loading")}
					/>
				) : !hasMedia ? (
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.media.gallery.empty")}
					</p>
				) : (
					<ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
						{mediaFiles.map((media) => {
							const src = resolveImageUrl(media);
							const isDeleting =
								deletingIds?.has(media.id) ?? false;
							return (
								<li
									key={media.id}
									className="border border-border rounded-lg overflow-hidden shadow-xs flex flex-col"
								>
									<div className="relative aspect-[4/3] bg-muted">
										{src ? (
											<img
												src={src}
												alt={media.caption || media.original_filename}
												className="h-full w-full object-cover"
												loading="lazy"
											/>
										) : (
											<div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
												{media.original_filename}
											</div>
										)}
										{onDelete ? (
											<Button
												type="button"
												variant="ghost"
												size="icon"
												className={cn(
													"absolute right-2 top-2 h-8 w-8 rounded-full bg-background/80 hover:bg-background",
													isDeleting && "pointer-events-none opacity-50",
												)}
												onClick={() => onDelete(media.id)}
												disabled={isDeleting}
											>
												<Trash2 className="h-4 w-4" />
												<span className="sr-only">
													{t(
														"pages.circles.dashboard.media.gallery.delete",
													)}
												</span>
											</Button>
										) : null}
									</div>
									<div className="p-3 space-y-1">
										<p className="text-sm font-medium text-foreground line-clamp-1">
											{media.caption || media.original_filename}
										</p>
										<p className="text-xs text-muted-foreground">
											{media.created_at
												? new Date(media.created_at).toLocaleString()
												: ""}
										</p>
									</div>
								</li>
							);
						})}
					</ul>
				)}
			</CardContent>
		</Card>
	);
}

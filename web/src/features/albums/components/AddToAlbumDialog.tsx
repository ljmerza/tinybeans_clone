import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { FeedKeep } from "@/features/keeps/types";
import { Images } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	useCreateAlbum,
	useKeepAlbums,
	useSetKeepInAlbum,
} from "../hooks/useAlbums";

/** Matches the backend's `Album.name` max_length. */
const NAME_MAX_LENGTH = 120;

export interface AddToAlbumDialogProps {
	keep: Pick<FeedKeep, "id" | "circle">;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * Check or uncheck the albums of a post's circle to add the post to them or
 * take it out, or start a new album with it. Each tick saves straight away.
 * Mount it only while open, so the album list is fetched on demand.
 */
export function AddToAlbumDialog({
	keep,
	open,
	onOpenChange,
}: AddToAlbumDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const albums = useKeepAlbums(keep.id);
	const setInAlbum = useSetKeepInAlbum();
	const create = useCreateAlbum();
	const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
	const [newName, setNewName] = useState("");

	const toggle = async (albumId: string, inAlbum: boolean) => {
		setPending((current) => new Set(current).add(albumId));
		try {
			await setInAlbum.mutateAsync({ albumId, keepId: keep.id, inAlbum });
		} catch {
			// The mutation rolls the box back and explains it in a toast.
		} finally {
			setPending((current) => {
				const next = new Set(current);
				next.delete(albumId);
				return next;
			});
		}
	};

	const createAlbum = async (event: React.FormEvent) => {
		event.preventDefault();
		const name = newName.trim();
		if (!name || create.isPending) return;
		try {
			await create.mutateAsync({ circle: keep.circle.id, name, keep: keep.id });
			setNewName("");
		} catch {
			// The mutation's error toast explains it; the name stays to retry.
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-sm" closeButtonLabel={t("common.close")}>
				<DialogHeader>
					<DialogTitle>{t("pages.albums.add.title")}</DialogTitle>
					<DialogDescription>
						{t("pages.albums.add.description", { circle: keep.circle.name })}
					</DialogDescription>
				</DialogHeader>

				{albums.isPending ? (
					<p className="py-4 text-center text-sm text-muted-foreground">
						{t("pages.albums.add.loading")}
					</p>
				) : albums.isError ? (
					<div className="space-y-2 py-4 text-center">
						<p className="text-sm text-muted-foreground">
							{t("pages.albums.add.error")}
						</p>
						<Button
							variant="outline"
							size="sm"
							onClick={() => void albums.refetch()}
						>
							{t("pages.feed.retry")}
						</Button>
					</div>
				) : albums.data.length === 0 ? (
					<p className="py-2 text-sm text-muted-foreground">
						{t("pages.albums.add.empty")}
					</p>
				) : (
					<ul className="-mx-2 max-h-[50dvh] space-y-0.5 overflow-y-auto">
						{albums.data.map((album) => (
							<li key={album.id}>
								<label className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-muted">
									<input
										type="checkbox"
										className="size-4 shrink-0 accent-primary"
										checked={album.has_keep === true}
										disabled={pending.has(album.id)}
										onChange={(event) =>
											void toggle(album.id, event.target.checked)
										}
									/>
									{album.cover ? (
										<img
											src={album.cover.url}
											alt=""
											loading="lazy"
											className="size-10 shrink-0 rounded object-cover"
										/>
									) : (
										<span className="flex size-10 shrink-0 items-center justify-center rounded bg-muted">
											<Images
												className="size-4 text-muted-foreground"
												aria-hidden="true"
											/>
										</span>
									)}
									<span className="min-w-0 flex-1">
										<span className="block truncate text-sm font-medium">
											{album.name}
										</span>
										<span className="block text-xs text-muted-foreground">
											{t("pages.albums.post_count", {
												count: album.post_count,
											})}
										</span>
									</span>
								</label>
							</li>
						))}
					</ul>
				)}

				<form className="flex gap-2" onSubmit={createAlbum}>
					<label htmlFor={`${ids}-new`} className="sr-only">
						{t("pages.albums.add.new_label")}
					</label>
					<Input
						id={`${ids}-new`}
						value={newName}
						maxLength={NAME_MAX_LENGTH}
						placeholder={t("pages.albums.add.new_placeholder")}
						onChange={(event) => setNewName(event.target.value)}
					/>
					<Button
						type="submit"
						variant="outline"
						disabled={!newName.trim() || create.isPending}
					>
						{t("pages.albums.add.create")}
					</Button>
				</form>

				<DialogFooter>
					<Button type="button" onClick={() => onOpenChange(false)}>
						{t("pages.albums.add.done")}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

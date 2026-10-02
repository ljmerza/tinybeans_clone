import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
	type CircleMembershipSummary,
	useCircleMemberships,
} from "@/features/circles";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { useCreateAlbum, useUpdateAlbum } from "../hooks/useAlbums";
import type { Album } from "../types";

/** Matches the backend's `Album.name` max_length. */
const NAME_MAX_LENGTH = 120;

export interface AlbumFormDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	/** Edit this album; omit to create one. */
	album?: Album;
	/** Called with the created or updated album, after the dialog closes. */
	onSaved?: (album: Album) => void;
}

/**
 * Create an album in one of the viewer's circles, or rename one and change
 * its description. Mount it only while open, so each opening starts fresh.
 */
export function AlbumFormDialog({
	open,
	onOpenChange,
	album,
	onSaved,
}: AlbumFormDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const editing = album !== undefined;
	const { data: memberships } = useCircleMemberships();
	const circles = ((memberships ?? []) as CircleMembershipSummary[]).map(
		(membership) => membership.circle,
	);
	const create = useCreateAlbum();
	const update = useUpdateAlbum();
	const saving = create.isPending || update.isPending;

	const [circleId, setCircleId] = useState<number | null>(null);
	const [name, setName] = useState(album?.name ?? "");
	const [description, setDescription] = useState(album?.description ?? "");

	const selectedCircleId = circleId ?? circles[0]?.id ?? null;
	const canSave =
		name.trim() !== "" && (editing || selectedCircleId !== null) && !saving;

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		if (!canSave) return;
		try {
			const saved = editing
				? await update.mutateAsync({
						albumId: album.id,
						input: { name: name.trim(), description: description.trim() },
					})
				: await create.mutateAsync({
						circle: selectedCircleId as number,
						name: name.trim(),
						description: description.trim(),
					});
			onOpenChange(false);
			onSaved?.(saved);
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent
				className="max-w-md"
				aria-describedby={undefined}
				closeButtonLabel={t("common.close")}
			>
				<DialogHeader>
					<DialogTitle>
						{editing
							? t("pages.albums.form.edit_title")
							: t("pages.albums.form.create_title")}
					</DialogTitle>
				</DialogHeader>
				<form className="space-y-4" onSubmit={handleSubmit}>
					{!editing && circles.length > 1 && (
						<div className="space-y-1.5">
							<Label htmlFor={`${ids}-circle`}>
								{t("pages.albums.form.circle")}
							</Label>
							<Select
								value={
									selectedCircleId === null
										? undefined
										: String(selectedCircleId)
								}
								onValueChange={(value) => setCircleId(Number(value))}
							>
								<SelectTrigger id={`${ids}-circle`} className="w-full">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{circles.map((circle) => (
										<SelectItem key={circle.id} value={String(circle.id)}>
											{circle.name}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					)}
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-name`}>{t("pages.albums.form.name")}</Label>
						<Input
							id={`${ids}-name`}
							value={name}
							maxLength={NAME_MAX_LENGTH}
							placeholder={t("pages.albums.form.name_placeholder")}
							onChange={(event) => setName(event.target.value)}
							autoFocus
						/>
					</div>
					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-description`}>
							{t("pages.albums.form.description")}
						</Label>
						<Textarea
							id={`${ids}-description`}
							value={description}
							rows={3}
							onChange={(event) => setDescription(event.target.value)}
						/>
					</div>
					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="ghost"
							onClick={() => onOpenChange(false)}
						>
							{t("common.cancel")}
						</Button>
						<Button type="submit" disabled={!canSave}>
							{saving
								? t("pages.albums.form.saving")
								: editing
									? t("pages.albums.form.save")
									: t("pages.albums.form.create")}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

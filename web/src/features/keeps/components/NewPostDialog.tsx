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
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import type { CircleMembershipSummary } from "@/features/circles";
import { useCircleMemberships } from "@/features/circles";
import { showToast } from "@/lib/toast";
import { Link } from "@tanstack/react-router";
import { Film, ImagePlus, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	type PostFileState,
	type PostItem,
	useCreatePost,
} from "../hooks/useCreatePost";
import { useUploadLimits } from "../hooks/useUploadLimits";
import type { KeepPerson } from "../types";
import { readExifDate } from "../utils/exifDate";
import { makeThumbnail } from "../utils/imageThumbnail";
import {
	PHOTO_TYPES,
	VIDEO_TYPES,
	fileProblem,
	mediaTypeOf,
	sizeLimitFor,
} from "../utils/mediaFiles";
import { PeoplePicker } from "./PeoplePicker";

const ACCEPT = [...PHOTO_TYPES, ...VIDEO_TYPES].join(",");

/** `YYYY-MM-DD` for a moment in the viewer's own timezone. */
function localDate(moment: Date) {
	const month = String(moment.getMonth() + 1).padStart(2, "0");
	const day = String(moment.getDate()).padStart(2, "0");
	return `${moment.getFullYear()}-${month}-${day}`;
}

/** Never later than today (camera clocks can be wrong). */
function notAfterToday(date: string) {
	const today = localDate(new Date());
	return date > today ? today : date;
}

/**
 * A file's date until its EXIF date (if any) is read: when it was last
 * modified. Phones may report when the file was picked rather than taken.
 */
function defaultDate(file: File) {
	return notAfterToday(
		file.lastModified
			? localDate(new Date(file.lastModified))
			: localDate(new Date()),
	);
}

/** A file in the composer; `dateEdited` stops the EXIF date overwriting a picked one. */
interface DraftItem extends PostItem {
	dateEdited: boolean;
}

function fileKey(file: File) {
	return `${file.name}-${file.size}-${file.lastModified}`;
}

function formatSize(bytes: number) {
	if (bytes >= 1024 * 1024 * 1024)
		return `${Number((bytes / 1024 / 1024 / 1024).toFixed(1))} GB`;
	if (bytes >= 1024 * 1024) return `${Math.round(bytes / 1024 / 1024)} MB`;
	return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function FilePreview({ file }: { file: File }) {
	const isPhoto = mediaTypeOf(file) === "photo";
	const [url, setUrl] = useState<string | null>(null);
	// Created in the effect, not a memo: StrictMode runs the cleanup once on
	// mount, which would revoke a memoized URL the <img> still points at.
	useEffect(() => {
		if (!isPhoto) return;
		let cancelled = false;
		let objectUrl: string | null = null;
		// A small copy, not the full-size photo: decoding and rescaling a few
		// 12 MP originals on every paint makes the dialog sluggish.
		void makeThumbnail(file).then((thumbnail) => {
			if (cancelled) return;
			objectUrl = URL.createObjectURL(thumbnail ?? file);
			setUrl(objectUrl);
		});
		return () => {
			cancelled = true;
			if (objectUrl) URL.revokeObjectURL(objectUrl);
		};
	}, [file, isPhoto]);

	if (!isPhoto) {
		return (
			<div className="flex size-20 shrink-0 items-center justify-center rounded bg-muted">
				<Film className="size-5 text-muted-foreground" aria-hidden="true" />
			</div>
		);
	}
	if (!url) {
		return <div className="size-20 shrink-0 rounded bg-muted" />;
	}
	return (
		<img
			src={url}
			alt=""
			decoding="async"
			className="size-20 shrink-0 rounded object-cover"
		/>
	);
}

function FileStatus({ state }: { state: PostFileState | undefined }) {
	const { t } = useTranslation();
	if (!state) return null;
	if (state.status === "uploading") {
		const percent = Math.round(state.progress * 100);
		return (
			<div className="mt-1 space-y-1">
				<progress
					className="block h-1.5 w-full appearance-none overflow-hidden rounded bg-muted [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary"
					value={percent}
					max={100}
				/>
				<p className="text-xs text-muted-foreground">
					{t("pages.feed.new_post.status.uploading", { percent })}
				</p>
			</div>
		);
	}
	return (
		<p
			className={
				state.status === "failed"
					? "text-xs text-destructive"
					: "text-xs text-muted-foreground"
			}
		>
			{t(`pages.feed.new_post.status.${state.status}`)}
		</p>
	);
}

export interface NewPostDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * Post photos and videos to one of the viewer's circles. Each file becomes
 * its own post with its own title and date.
 */
export function NewPostDialog({ open, onOpenChange }: NewPostDialogProps) {
	const { t } = useTranslation();
	const ids = useId();
	const fileInputRef = useRef<HTMLInputElement>(null);
	const { data: memberships } = useCircleMemberships();
	const circles = ((memberships ?? []) as CircleMembershipSummary[]).map(
		(membership) => membership.circle,
	);
	const post = useCreatePost();
	const uploadLimits = useUploadLimits();

	const [circleId, setCircleId] = useState<number | null>(null);
	const [items, setItems] = useState<DraftItem[]>([]);
	const [rejected, setRejected] = useState<string[]>([]);
	// Tagged on every file in the batch; people belong to one circle.
	const [people, setPeople] = useState<KeepPerson[]>([]);

	const selectedCircleId = circleId ?? circles[0]?.id ?? null;
	const busy = post.phase === "posting";
	const locked = post.phase !== "idle";
	const canPost =
		selectedCircleId !== null &&
		items.length > 0 &&
		items.every((item) => item.date !== "");

	const { phase, reset } = post;
	const postedCount = post.fileStates.filter(
		(state) => state.status === "done",
	).length;
	const clear = useCallback(() => {
		setItems([]);
		setRejected([]);
		setPeople([]);
		reset();
	}, [reset]);

	useEffect(() => {
		if (phase !== "done") return;
		showToast({
			message: t("pages.feed.new_post.posted", { count: postedCount }),
			level: "success",
		});
		clear();
		onOpenChange(false);
	}, [phase, postedCount, clear, onOpenChange, t]);

	const addFiles = (list: FileList | null) => {
		const picked = Array.from(list ?? []);
		const problems = picked.flatMap((file) => {
			const problem = fileProblem(file, uploadLimits);
			if (!problem) return [];
			const mediaType = mediaTypeOf(file);
			const max = mediaType
				? formatSize(sizeLimitFor(mediaType, uploadLimits))
				: "";
			return [
				t(`pages.feed.new_post.rejected_${problem}`, { name: file.name, max }),
			];
		});
		setRejected(problems);
		const accepted = picked.filter(
			(file) => fileProblem(file, uploadLimits) === null,
		);
		setItems((current) => {
			// Picking the same file twice adds it once.
			const chosen = new Set(current.map((item) => fileKey(item.file)));
			return [
				...current,
				...accepted
					.filter((file) => !chosen.has(fileKey(file)))
					.map((file) => ({
						file,
						title: "",
						date: defaultDate(file),
						dateEdited: false,
					})),
			];
		});
		// Swap in the day each photo was taken, unless it's been changed already.
		for (const file of accepted) {
			if (mediaTypeOf(file) !== "photo") continue;
			void readExifDate(file).then((taken) => {
				if (!taken) return;
				setItems((current) =>
					current.map((item) =>
						item.file === file && !item.dateEdited
							? { ...item, date: notAfterToday(taken) }
							: item,
					),
				);
			});
		}
	};

	const updateItem = (index: number, patch: Partial<DraftItem>) =>
		setItems((current) =>
			current.map((item, i) => (i === index ? { ...item, ...patch } : item)),
		);

	const handleSubmit = (event: React.FormEvent) => {
		event.preventDefault();
		if (!canPost || selectedCircleId === null || locked) return;
		void post.submit(
			selectedCircleId,
			items,
			people.map((person) => person.id),
		);
	};

	const handleCancel = async () => {
		await post.cancel();
		clear();
		onOpenChange(false);
	};

	const handleOpenChange = (next: boolean) => {
		// Leaving mid-post would orphan the uploads; use the explicit buttons.
		if (!next && locked) return;
		if (!next) clear();
		onOpenChange(next);
	};

	// Nothing to post to: point the viewer at circle setup instead of a picker.
	if (memberships !== undefined && circles.length === 0) {
		return (
			<Dialog open={open} onOpenChange={handleOpenChange}>
				<DialogContent closeButtonLabel={t("common.close")}>
					<DialogHeader>
						<DialogTitle>{t("pages.feed.new_post.title")}</DialogTitle>
						<DialogDescription>
							{t("pages.feed.new_post.no_circles")}
						</DialogDescription>
					</DialogHeader>
					<DialogFooter className="gap-2">
						<Button
							type="button"
							variant="ghost"
							onClick={() => handleOpenChange(false)}
						>
							{t("common.close")}
						</Button>
						<Button asChild>
							<Link to="/circles/onboarding">
								{t("pages.feed.new_post.set_up_circle")}
							</Link>
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		);
	}

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogContent
				className="max-h-[90dvh] overflow-y-auto"
				closeButtonLabel={t("common.close")}
				showCloseButton={!locked}
			>
				<DialogHeader>
					<DialogTitle>{t("pages.feed.new_post.title")}</DialogTitle>
					<DialogDescription>
						{t("pages.feed.new_post.description")}
					</DialogDescription>
				</DialogHeader>

				<form className="space-y-4" onSubmit={handleSubmit}>
					{circles.length > 1 && (
						<div className="space-y-1.5">
							<Label htmlFor={`${ids}-circle`}>
								{t("pages.feed.new_post.circle")}
							</Label>
							<Select
								value={
									selectedCircleId === null
										? undefined
										: String(selectedCircleId)
								}
								onValueChange={(value) => {
									if (Number(value) !== selectedCircleId) setPeople([]);
									setCircleId(Number(value));
								}}
								disabled={locked}
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

					{/* Asked once there is something to tag. */}
					{selectedCircleId !== null && items.length > 0 && (
						<fieldset className="space-y-1.5">
							<legend className="mb-1.5 text-sm font-medium leading-none">
								{t("pages.people.composer.label")}
							</legend>
							<PeoplePicker
								circleId={selectedCircleId}
								selected={people}
								onChange={setPeople}
								disabled={locked}
							/>
							<p className="text-xs text-muted-foreground">
								{t("pages.people.composer.hint")}
							</p>
						</fieldset>
					)}

					<div className="space-y-2">
						<input
							ref={fileInputRef}
							type="file"
							accept={ACCEPT}
							multiple
							hidden
							data-testid="new-post-files"
							onChange={(event) => {
								addFiles(event.target.files);
								event.target.value = "";
							}}
						/>
						<Button
							type="button"
							variant="outline"
							onClick={() => fileInputRef.current?.click()}
							disabled={locked}
						>
							<ImagePlus aria-hidden="true" />
							{t("pages.feed.new_post.add_media")}
						</Button>
						<p className="text-xs text-muted-foreground">
							{t("pages.feed.new_post.media_hint", {
								photoMax: formatSize(uploadLimits.max_photo_bytes),
								videoMax: formatSize(uploadLimits.max_video_bytes),
							})}
						</p>
						{rejected.map((message) => (
							<p key={message} className="text-sm text-destructive">
								{message}
							</p>
						))}
					</div>

					{items.length > 0 && (
						<ul className="space-y-3">
							{items.map((item, index) => {
								const fieldId = `${ids}-${index}`;
								const state = post.fileStates[index];
								return (
									<li
										key={fileKey(item.file)}
										className="flex gap-3 rounded-md border p-3"
									>
										<FilePreview file={item.file} />
										<div className="min-w-0 flex-1 space-y-2">
											<div className="flex items-start gap-2">
												<p className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
													{item.file.name} · {formatSize(item.file.size)}
												</p>
												{!locked && (
													<Button
														type="button"
														variant="ghost"
														size="icon"
														className="-mr-2 -mt-2 size-7"
														aria-label={t("pages.feed.new_post.remove_file", {
															name: item.file.name,
														})}
														onClick={() =>
															setItems((current) =>
																current.filter((_, i) => i !== index),
															)
														}
													>
														<X aria-hidden="true" />
													</Button>
												)}
											</div>
											<div className="space-y-1">
												<Label htmlFor={`${fieldId}-title`} className="sr-only">
													{t("pages.feed.new_post.item_title_label", {
														name: item.file.name,
													})}
												</Label>
												<Input
													id={`${fieldId}-title`}
													value={item.title}
													maxLength={255}
													placeholder={t(
														"pages.feed.new_post.item_title_placeholder",
													)}
													onChange={(event) =>
														updateItem(index, { title: event.target.value })
													}
													disabled={locked}
												/>
											</div>
											<div className="space-y-1">
												<Label htmlFor={`${fieldId}-date`} className="sr-only">
													{t("pages.feed.new_post.item_date_label", {
														name: item.file.name,
													})}
												</Label>
												<Input
													id={`${fieldId}-date`}
													type="date"
													value={item.date}
													max={localDate(new Date())}
													onChange={(event) =>
														updateItem(index, {
															date: event.target.value,
															dateEdited: true,
														})
													}
													disabled={locked}
												/>
											</div>
											<FileStatus state={state} />
										</div>
									</li>
								);
							})}
						</ul>
					)}

					{post.phase === "failed" && (
						<p className="text-sm text-destructive">
							{t("pages.feed.new_post.upload_failed")}
						</p>
					)}

					<DialogFooter className="gap-2">
						{post.phase === "failed" ? (
							<>
								<Button
									type="button"
									variant="outline"
									// With nothing posted, skipping the failures is a discard.
									onClick={
										post.hasUploaded
											? () => void post.skipFailed()
											: handleCancel
									}
								>
									{post.hasUploaded
										? t("pages.feed.new_post.skip_failed")
										: t("pages.feed.new_post.discard")}
								</Button>
								<Button type="button" onClick={() => void post.retryFailed()}>
									{t("pages.feed.new_post.retry_failed")}
								</Button>
							</>
						) : (
							<>
								<Button
									type="button"
									variant="ghost"
									onClick={busy ? handleCancel : () => handleOpenChange(false)}
								>
									{t("common.cancel")}
								</Button>
								<Button type="submit" disabled={!canPost || busy}>
									{busy
										? t("pages.feed.new_post.posting")
										: t("pages.feed.new_post.submit", {
												// Plain "Post" until there are several files.
												count: Math.max(1, items.length),
											})}
								</Button>
							</>
						)}
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

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
import { Textarea } from "@/components/ui/textarea";
import type { CircleMembershipSummary } from "@/features/circles";
import { useCircleMemberships } from "@/features/circles";
import { showToast } from "@/lib/toast";
import { Film, ImagePlus, X } from "lucide-react";
import {
	useCallback,
	useEffect,
	useId,
	useMemo,
	useRef,
	useState,
} from "react";
import { useTranslation } from "react-i18next";

import { type PostFileState, useCreatePost } from "../hooks/useCreatePost";
import {
	PHOTO_TYPES,
	VIDEO_TYPES,
	fileProblem,
	mediaTypeOf,
} from "../utils/mediaFiles";

const ACCEPT = [...PHOTO_TYPES, ...VIDEO_TYPES].join(",");

/** Today as `YYYY-MM-DD` in the viewer's own timezone. */
function localToday() {
	const now = new Date();
	const month = String(now.getMonth() + 1).padStart(2, "0");
	const day = String(now.getDate()).padStart(2, "0");
	return `${now.getFullYear()}-${month}-${day}`;
}

function fileKey(file: File) {
	return `${file.name}-${file.size}-${file.lastModified}`;
}

function formatSize(bytes: number) {
	if (bytes >= 1024 * 1024 * 1024)
		return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
	if (bytes >= 1024 * 1024) return `${Math.round(bytes / 1024 / 1024)} MB`;
	return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function FilePreview({ file }: { file: File }) {
	const url = useMemo(
		() => (mediaTypeOf(file) === "photo" ? URL.createObjectURL(file) : null),
		[file],
	);
	useEffect(
		() => () => {
			if (url) URL.revokeObjectURL(url);
		},
		[url],
	);

	if (!url) {
		return (
			<div className="flex size-12 shrink-0 items-center justify-center rounded bg-muted">
				<Film className="size-5 text-muted-foreground" aria-hidden="true" />
			</div>
		);
	}
	return (
		<img src={url} alt="" className="size-12 shrink-0 rounded object-cover" />
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
 * Compose a post for one of the viewer's circles: text, photos and videos.
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

	const [circleId, setCircleId] = useState<number | null>(null);
	const [title, setTitle] = useState("");
	const [text, setText] = useState("");
	const [date, setDate] = useState(localToday);
	const [files, setFiles] = useState<File[]>([]);
	const [rejected, setRejected] = useState<string[]>([]);
	const [error, setError] = useState("");

	const selectedCircleId = circleId ?? circles[0]?.id ?? null;
	const busy = post.phase === "posting";
	const locked = post.phase !== "idle";
	const canPost =
		selectedCircleId !== null &&
		date !== "" &&
		(text.trim() !== "" || files.length > 0);

	const { phase, reset } = post;
	const clear = useCallback(() => {
		setTitle("");
		setText("");
		setDate(localToday());
		setFiles([]);
		setRejected([]);
		setError("");
		reset();
	}, [reset]);

	useEffect(() => {
		if (phase !== "done") return;
		showToast({ message: t("pages.feed.new_post.posted"), level: "success" });
		clear();
		onOpenChange(false);
	}, [phase, clear, onOpenChange, t]);

	const addFiles = (list: FileList | null) => {
		const picked = Array.from(list ?? []);
		const problems = picked.flatMap((file) => {
			const problem = fileProblem(file);
			return problem
				? [t(`pages.feed.new_post.rejected_${problem}`, { name: file.name })]
				: [];
		});
		setRejected(problems);
		setFiles((current) => {
			// Picking the same file twice adds it once.
			const chosen = new Set(current.map(fileKey));
			return [
				...current,
				...picked.filter(
					(file) => fileProblem(file) === null && !chosen.has(fileKey(file)),
				),
			];
		});
	};

	const handleSubmit = async (event: React.FormEvent) => {
		event.preventDefault();
		if (!canPost || selectedCircleId === null || locked) return;
		setError("");
		try {
			await post.submit({
				circleId: selectedCircleId,
				title,
				text,
				date,
				files,
			});
		} catch {
			setError(t("pages.feed.new_post.create_failed"));
		}
	};

	const handleDiscard = async () => {
		try {
			await post.discard();
		} catch {
			// The post may linger unseen (a media post with no media never shows).
		}
		clear();
		onOpenChange(false);
	};

	const handleOpenChange = (next: boolean) => {
		// Leaving mid-post would orphan the upload; use the explicit buttons.
		if (!next && locked) return;
		if (!next) clear();
		onOpenChange(next);
	};

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
								onValueChange={(value) => setCircleId(Number(value))}
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

					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-title`}>
							{t("pages.feed.new_post.title_label")}
						</Label>
						<Input
							id={`${ids}-title`}
							value={title}
							maxLength={255}
							onChange={(event) => setTitle(event.target.value)}
							disabled={locked}
						/>
					</div>

					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-text`}>
							{t("pages.feed.new_post.text_label")}
						</Label>
						<Textarea
							id={`${ids}-text`}
							value={text}
							placeholder={t("pages.feed.new_post.text_placeholder")}
							onChange={(event) => setText(event.target.value)}
							disabled={locked}
							rows={3}
						/>
					</div>

					<div className="space-y-1.5">
						<Label htmlFor={`${ids}-date`}>
							{t("pages.feed.new_post.date_label")}
						</Label>
						<Input
							id={`${ids}-date`}
							type="date"
							value={date}
							max={localToday()}
							onChange={(event) => setDate(event.target.value)}
							disabled={locked}
						/>
					</div>

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
							{t("pages.feed.new_post.media_hint")}
						</p>
						{rejected.map((message) => (
							<p key={message} className="text-sm text-destructive">
								{message}
							</p>
						))}
						{files.length > 0 && (
							<ul className="space-y-2">
								{files.map((file, index) => (
									<li key={fileKey(file)} className="flex items-center gap-3">
										<FilePreview file={file} />
										<div className="min-w-0 flex-1">
											<p className="truncate text-sm">{file.name}</p>
											{post.fileStates[index] ? (
												<FileStatus state={post.fileStates[index]} />
											) : (
												<p className="text-xs text-muted-foreground">
													{formatSize(file.size)}
												</p>
											)}
										</div>
										{!locked && (
											<Button
												type="button"
												variant="ghost"
												size="icon"
												aria-label={t("pages.feed.new_post.remove_file", {
													name: file.name,
												})}
												onClick={() =>
													setFiles((current) =>
														current.filter((_, i) => i !== index),
													)
												}
											>
												<X aria-hidden="true" />
											</Button>
										)}
									</li>
								))}
							</ul>
						)}
					</div>

					{error && <p className="text-sm text-destructive">{error}</p>}
					{post.phase === "failed" && (
						<p className="text-sm text-destructive">
							{t("pages.feed.new_post.upload_failed")}
						</p>
					)}

					<DialogFooter className="gap-2">
						{post.phase === "failed" ? (
							<>
								<Button type="button" variant="ghost" onClick={handleDiscard}>
									{t("pages.feed.new_post.discard")}
								</Button>
								{post.hasUploaded && (
									<Button
										type="button"
										variant="outline"
										onClick={() => void post.finishWithUploaded()}
									>
										{t("pages.feed.new_post.post_uploaded")}
									</Button>
								)}
								<Button type="button" onClick={() => void post.retryFailed()}>
									{t("pages.feed.new_post.retry_failed")}
								</Button>
							</>
						) : (
							<>
								<Button
									type="button"
									variant="ghost"
									onClick={busy ? handleDiscard : () => handleOpenChange(false)}
								>
									{t("common.cancel")}
								</Button>
								<Button type="submit" disabled={!canPost || busy}>
									{busy
										? t("pages.feed.new_post.posting")
										: t("pages.feed.new_post.submit")}
								</Button>
							</>
						)}
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}

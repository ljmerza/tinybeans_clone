import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import { uploadMedia } from "../api/uploadMedia";
import { captureVideoPoster } from "../utils/captureVideoPoster";
import { mediaTypeOf } from "../utils/mediaFiles";

/** Files uploading at once; more just splits the same bandwidth. */
const UPLOAD_CONCURRENCY = 2;
const STATUS_POLL_MS = 2000;
/** Give up on server processing after this long (a 1 GB video takes well under). */
const PROCESSING_TIMEOUT_MS = 20 * 60 * 1000;
const VISIBLE_POLL_MS = 1500;
const VISIBLE_POLL_ATTEMPTS = 40;

/**
 * Pin the memory to the chosen calendar day. The feed and calendar group by
 * UTC day, so the date keeps its UTC form and only borrows the current time
 * of day to order same-day posts.
 */
export function memoryTimestamp(date: string, now = new Date()) {
	return `${date}T${now.toISOString().slice(11)}`;
}

/** One photo or video; each becomes its own post. */
export interface PostItem {
	file: File;
	title: string;
	/** `YYYY-MM-DD` */
	date: string;
}

export type PostFileStatus =
	| "queued"
	| "uploading"
	| "processing"
	| "done"
	| "failed";

export interface PostFileState {
	status: PostFileStatus;
	/** Upload progress, 0–1. */
	progress: number;
	/** The item's post, once created. */
	keepId?: string;
}

/**
 * idle → posting → done, or → failed when any file didn't make it (retry
 * them, or skip them and keep what posted).
 */
export type PostPhase = "idle" | "posting" | "failed" | "done";

function isAbort(error: unknown) {
	return error instanceof DOMException && error.name === "AbortError";
}

function sleep(ms: number, signal: AbortSignal) {
	return new Promise<void>((resolve, reject) => {
		const timer = window.setTimeout(resolve, ms);
		signal.addEventListener(
			"abort",
			() => {
				window.clearTimeout(timer);
				reject(new DOMException("Aborted", "AbortError"));
			},
			{ once: true },
		);
	});
}

/**
 * Post photos and videos, one post per file (each with its own title and
 * date): create the post, upload the file with progress, wait for the server
 * to process it, then wait until the posts are visible in the feed before
 * refreshing it (a media post stays hidden until its file is ready).
 */
export function useCreatePost() {
	const queryClient = useQueryClient();
	const [phase, setPhase] = useState<PostPhase>("idle");
	const [fileStates, setFileStates] = useState<PostFileState[]>([]);
	const circleIdRef = useRef<number | null>(null);
	const itemsRef = useRef<PostItem[]>([]);
	const statesRef = useRef<PostFileState[]>([]);
	const abortRef = useRef(new AbortController());

	// Stop polling and uploading when the composer goes away.
	useEffect(() => {
		const controller = new AbortController();
		abortRef.current = controller;
		return () => controller.abort();
	}, []);

	const setFileState = useCallback(
		(index: number, patch: Partial<PostFileState>) => {
			statesRef.current = statesRef.current.map((state, i) =>
				i === index ? { ...state, ...patch } : state,
			);
			setFileStates(statesRef.current);
		},
		[],
	);

	const postOne = useCallback(
		async (index: number) => {
			const signal = abortRef.current.signal;
			const { file, title, date } = itemsRef.current[index];
			const mediaType = mediaTypeOf(file) ?? "photo";
			setFileState(index, { status: "uploading", progress: 0 });
			try {
				// A retry reuses the post created on the first attempt.
				let keepId = statesRef.current[index].keepId;
				if (!keepId) {
					const keep = await keepServices.createKeep({
						circle: circleIdRef.current as number,
						keep_type: "media",
						title: title.trim(),
						description: "",
						date_of_memory: memoryTimestamp(date),
					});
					keepId = keep.id;
					setFileState(index, { keepId });
				}
				const poster =
					mediaType === "video"
						? ((await captureVideoPoster(file)) ?? undefined)
						: undefined;
				// Re-render per whole percent, not per progress event (many a second).
				let shownPercent = -1;
				const upload = await uploadMedia(
					{ keepId, mediaType, file, poster, uploadOrder: 0 },
					(progress) => {
						const percent = Math.floor(progress * 100);
						if (percent === shownPercent) return;
						shownPercent = percent;
						setFileState(index, { progress: percent / 100 });
					},
					signal,
				);
				setFileState(index, { status: "processing", progress: 1 });

				const deadline = Date.now() + PROCESSING_TIMEOUT_MS;
				let status = upload.status;
				while (status !== "completed" && status !== "failed") {
					if (Date.now() > deadline) throw new Error("Processing timed out");
					await sleep(STATUS_POLL_MS, signal);
					const response = await keepServices.getUploadStatus(upload.id);
					status = response.data?.status ?? status;
				}
				setFileState(index, {
					status: status === "completed" ? "done" : "failed",
				});
			} catch (error) {
				if (signal.aborted) throw error;
				setFileState(index, { status: "failed" });
			}
		},
		[setFileState],
	);

	const waitUntilVisible = useCallback(async (keepIds: string[]) => {
		const signal = abortRef.current.signal;
		const pending = new Set(keepIds);
		for (
			let attempt = 0;
			attempt < VISIBLE_POLL_ATTEMPTS && pending.size > 0;
			attempt++
		) {
			for (const keepId of [...pending]) {
				try {
					await keepServices.getFeedKeep(keepId);
					pending.delete(keepId);
				} catch {
					// 404 until the photo or video poster is ready.
				}
			}
			if (pending.size > 0) await sleep(VISIBLE_POLL_MS, signal);
		}
	}, []);

	/** Wait for the posted files to show, then refresh the feed. */
	const finish = useCallback(async () => {
		const posted = statesRef.current.flatMap((state) =>
			state.status === "done" && state.keepId ? [state.keepId] : [],
		);
		await waitUntilVisible(posted);
		await queryClient.invalidateQueries({ queryKey: keepKeys.all() });
		setPhase("done");
	}, [queryClient, waitUntilVisible]);

	/** Post the given files, then settle the phase. */
	const run = useCallback(
		async (indices: number[]) => {
			setPhase("posting");
			const queue = [...indices];
			const worker = async () => {
				for (
					let index = queue.shift();
					index !== undefined;
					index = queue.shift()
				) {
					await postOne(index);
				}
			};
			await Promise.all(
				Array.from(
					{ length: Math.min(UPLOAD_CONCURRENCY, queue.length) },
					worker,
				),
			);

			if (statesRef.current.some((state) => state.status === "failed")) {
				setPhase("failed");
				return;
			}
			await finish();
		},
		[finish, postOne],
	);

	/** Ignore aborts (cancelled or unmounted); anything else is a real error. */
	const quietly = useCallback(async (work: () => Promise<void>) => {
		try {
			await work();
		} catch (error) {
			if (!isAbort(error)) throw error;
		}
	}, []);

	const submit = useCallback(
		(circleId: number, items: PostItem[]) => {
			circleIdRef.current = circleId;
			itemsRef.current = items;
			statesRef.current = items.map(() => ({ status: "queued", progress: 0 }));
			setFileStates(statesRef.current);
			return quietly(() => run(items.map((_, index) => index)));
		},
		[quietly, run],
	);

	const retryFailed = useCallback(() => {
		const failed = statesRef.current.flatMap((state, index) =>
			state.status === "failed" ? [index] : [],
		);
		return quietly(() => run(failed));
	}, [quietly, run]);

	/**
	 * Delete the posts of files that never finished uploading; they have no
	 * media, so they'd never show. Files already processing are left to finish.
	 */
	const deleteUnfinished = useCallback(async () => {
		const unfinished = statesRef.current.flatMap((state) =>
			state.keepId && state.status !== "done" && state.status !== "processing"
				? [state.keepId]
				: [],
		);
		await Promise.allSettled(
			unfinished.map((keepId) => keepServices.deleteKeep(keepId)),
		);
	}, []);

	/** Give up on the failed files and keep what posted. */
	const skipFailed = useCallback(async () => {
		setPhase("posting");
		await deleteUnfinished();
		await quietly(finish);
	}, [deleteUnfinished, finish, quietly]);

	/** Stop uploading; files that already posted stay posted. */
	const cancel = useCallback(async () => {
		abortRef.current.abort();
		abortRef.current = new AbortController();
		await deleteUnfinished();
		if (statesRef.current.some((state) => state.status !== "queued")) {
			await queryClient.invalidateQueries({ queryKey: keepKeys.all() });
		}
	}, [deleteUnfinished, queryClient]);

	const reset = useCallback(() => {
		abortRef.current.abort();
		abortRef.current = new AbortController();
		circleIdRef.current = null;
		itemsRef.current = [];
		statesRef.current = [];
		setFileStates([]);
		setPhase("idle");
	}, []);

	return {
		phase,
		fileStates,
		submit,
		retryFailed,
		skipFailed,
		cancel,
		reset,
		/** At least one file posted, so skipping the failures still shows something. */
		hasUploaded: fileStates.some((state) => state.status === "done"),
	};
}

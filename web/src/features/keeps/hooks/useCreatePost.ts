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

export interface PostDraft {
	circleId: number;
	title: string;
	text: string;
	/** `YYYY-MM-DD` */
	date: string;
	files: File[];
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
}

/**
 * idle → posting → done, or → failed when any file didn't make it (retry,
 * finish with what worked, or discard).
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
 * Create a post: make the keep, upload each file with progress, wait for the
 * server to process them, then wait until the post is visible in the feed
 * before refreshing it (a media post stays hidden until a file is ready).
 */
export function useCreatePost() {
	const queryClient = useQueryClient();
	const [phase, setPhase] = useState<PostPhase>("idle");
	const [fileStates, setFileStates] = useState<PostFileState[]>([]);
	const keepIdRef = useRef<string | null>(null);
	const filesRef = useRef<File[]>([]);
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

	const uploadOne = useCallback(
		async (keepId: string, index: number) => {
			const signal = abortRef.current.signal;
			const file = filesRef.current[index];
			const mediaType = mediaTypeOf(file) ?? "photo";
			setFileState(index, { status: "uploading", progress: 0 });
			try {
				const poster =
					mediaType === "video"
						? ((await captureVideoPoster(file)) ?? undefined)
						: undefined;
				const upload = await uploadMedia(
					{ keepId, mediaType, file, poster, uploadOrder: index },
					(progress) => setFileState(index, { progress }),
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

	const waitUntilVisible = useCallback(async (keepId: string) => {
		const signal = abortRef.current.signal;
		for (let attempt = 0; attempt < VISIBLE_POLL_ATTEMPTS; attempt++) {
			try {
				await keepServices.getFeedKeep(keepId);
				return;
			} catch {
				// 404 until a photo or video poster is ready.
			}
			await sleep(VISIBLE_POLL_MS, signal);
		}
	}, []);

	/** Upload the given files, then settle the phase. */
	const run = useCallback(
		async (keepId: string, indices: number[]) => {
			setPhase("posting");
			const queue = [...indices];
			const worker = async () => {
				for (
					let index = queue.shift();
					index !== undefined;
					index = queue.shift()
				) {
					await uploadOne(keepId, index);
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
			await waitUntilVisible(keepId);
			await queryClient.invalidateQueries({ queryKey: keepKeys.all() });
			setPhase("done");
		},
		[queryClient, uploadOne, waitUntilVisible],
	);

	const submit = useCallback(
		async ({ circleId, title, text, date, files }: PostDraft) => {
			filesRef.current = files;
			statesRef.current = files.map(() => ({ status: "queued", progress: 0 }));
			setFileStates(statesRef.current);
			setPhase("posting");
			try {
				const keep = await keepServices.createKeep({
					circle: circleId,
					keep_type: files.length > 0 ? "media" : "note",
					title: title.trim(),
					description: text.trim(),
					date_of_memory: memoryTimestamp(date),
				});
				keepIdRef.current = keep.id;
				await run(
					keep.id,
					files.map((_, index) => index),
				);
			} catch (error) {
				// Cancelled or unmounted: nothing to report.
				if (isAbort(error)) return;
				setPhase("idle");
				throw error;
			}
		},
		[run],
	);

	const retryFailed = useCallback(async () => {
		const keepId = keepIdRef.current;
		if (!keepId) return;
		const failed = statesRef.current.flatMap((state, index) =>
			state.status === "failed" ? [index] : [],
		);
		try {
			await run(keepId, failed);
		} catch (error) {
			if (!isAbort(error)) throw error;
		}
	}, [run]);

	/** Keep whatever uploaded and show the post. */
	const finishWithUploaded = useCallback(async () => {
		const keepId = keepIdRef.current;
		if (!keepId) return;
		setPhase("posting");
		try {
			await waitUntilVisible(keepId);
			await queryClient.invalidateQueries({ queryKey: keepKeys.all() });
			setPhase("done");
		} catch (error) {
			if (!isAbort(error)) throw error;
		}
	}, [queryClient, waitUntilVisible]);

	/**
	 * Stop any uploads and delete the half-made post, e.g. when nothing
	 * uploaded (a media post without media never shows).
	 */
	const discard = useCallback(async () => {
		abortRef.current.abort();
		abortRef.current = new AbortController();
		const keepId = keepIdRef.current;
		keepIdRef.current = null;
		setPhase("idle");
		if (keepId) await keepServices.deleteKeep(keepId);
	}, []);

	const reset = useCallback(() => {
		abortRef.current.abort();
		abortRef.current = new AbortController();
		keepIdRef.current = null;
		filesRef.current = [];
		statesRef.current = [];
		setFileStates([]);
		setPhase("idle");
	}, []);

	return {
		phase,
		fileStates,
		submit,
		retryFailed,
		finishWithUploaded,
		discard,
		reset,
		/** At least one file made it, so finishing shows a post. */
		hasUploaded: fileStates.some((state) => state.status === "done"),
	};
}

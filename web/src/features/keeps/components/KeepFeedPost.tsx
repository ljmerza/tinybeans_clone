import { ConfirmDialog } from "@/components";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	PostActionSpacer,
	PostActions,
	PostAuthor,
	PostAvatar,
	PostCaption,
	PostCommentButton,
	PostCommentForm,
	PostComments,
	PostFavoriteButton,
	PostHeader,
	PostLikeButton,
	PostLikers,
	PostMedia,
	PostMediaCounter,
	PostMediaNextButton,
	PostMediaPrevButton,
	PostRoot,
	PostShareButton,
	PostTimestamp,
	PostTitle,
	type SocialComment,
} from "react-social-feed";

import {
	RECENT_COMMENT_COUNT,
	useAddKeepComment,
	useDeleteKeepComment,
	useKeepComments,
	useKeepLikers,
	useSetKeepFavorited,
	useSetKeepLiked,
} from "../hooks/useKeepFeed";
import type { FeedKeep } from "../types";
import { keepToSocialPost } from "../utils/keepToSocialPost";

/** Comments each "Show more" reveals after the first RECENT_COMMENT_COUNT. */
const COMMENT_PAGE_SIZE = 5;

export interface KeepFeedPostProps {
	keep: FeedKeep;
	/** Open with the full comment thread loaded and one page shown (e.g. on a shared link). */
	defaultCommentsExpanded?: boolean;
}

/**
 * One keep rendered as a social feed post, wired to reactions and comments.
 */
export function KeepFeedPost({
	keep,
	defaultCommentsExpanded = false,
}: KeepFeedPostProps) {
	const { t, i18n } = useTranslation();
	const setLiked = useSetKeepLiked();
	const setFavorited = useSetKeepFavorited();
	const addComment = useAddKeepComment();
	const deleteComment = useDeleteKeepComment();
	const [pendingDelete, setPendingDelete] = useState<SocialComment | null>(
		null,
	);
	const [showAllComments, setShowAllComments] = useState(
		defaultCommentsExpanded,
	);
	const thread = useKeepComments(keep.id, showAllComments);
	const [likersOpen, setLikersOpen] = useState(false);
	const likers = useKeepLikers(keep.id, likersOpen);
	const likersHidden = likers.data
		? likers.data.count - likers.data.results.length
		: 0;

	const post = useMemo(
		() =>
			keepToSocialPost(keep, {
				comments: showAllComments ? thread.data : undefined,
				fallbackAlt: t("pages.feed.photo_alt", {
					name: keep.created_by_display_name,
				}),
				origin: window.location.origin,
			}),
		[keep, showAllComments, thread.data, t],
	);

	// Memories are stored as UTC dates; render them the way the calendar does.
	const dateFormatter = useMemo(
		() =>
			new Intl.DateTimeFormat(i18n.language, {
				dateStyle: "medium",
				timeZone: "UTC",
			}),
		[i18n.language],
	);

	const confirmDelete = async () => {
		if (!pendingDelete) return;
		try {
			await deleteComment.mutateAsync({
				keepId: keep.id,
				commentId: Number(pendingDelete.id),
			});
			setPendingDelete(null);
		} catch {
			// The mutation's error toast explains it; leave the dialog open to retry.
		}
	};

	return (
		<>
			<PostRoot
				post={post}
				defaultCommentsExpanded={defaultCommentsExpanded}
				// A keep's own page (e.g. a shared link) shows the whole discussion.
				defaultCommentPage={
					defaultCommentsExpanded ? Number.POSITIVE_INFINITY : 0
				}
				onLikeChange={(liked) => setLiked.mutateAsync({ keep, liked })}
				onFavoriteChange={(favorited) =>
					setFavorited.mutateAsync({ keepId: keep.id, favorited })
				}
				onCommentSubmit={(text, _post, { parentId }) =>
					addComment.mutateAsync({
						keepId: keep.id,
						text,
						parentId: parentId === undefined ? undefined : Number(parentId),
					})
				}
				onCommentDelete={setPendingDelete}
				onCommentsExpandedChange={setShowAllComments}
				likersOpen={likersOpen}
				onLikersOpenChange={setLikersOpen}
			>
				<PostHeader>
					<PostAvatar />
					<div className="rsf-post__byline">
						<PostAuthor />
						<span className="rsf-post__timestamp">
							{keep.circle.name} ·{" "}
							<PostTimestamp format={(date) => dateFormatter.format(date)} />
						</span>
					</div>
				</PostHeader>
				{/* Title and caption above the photo, aligned with the header's padding. */}
				<div className="-mt-1.5 space-y-1 px-[var(--rsf-spacing)] pb-2.5 empty:hidden">
					<PostTitle />
					<PostCaption />
				</div>
				<PostMedia>
					<PostMediaPrevButton aria-label={t("pages.feed.previous_photo")} />
					<PostMediaNextButton aria-label={t("pages.feed.next_photo")} />
					<PostMediaCounter />
				</PostMedia>
				<div className="rsf-post__body">
					<PostActions>
						<PostLikeButton
							label={(liked) =>
								liked ? t("pages.feed.unlike") : t("pages.feed.like")
							}
							likersHint={t("pages.feed.likers_hint")}
						/>
						<PostCommentButton aria-label={t("pages.feed.comment")} />
						<PostActionSpacer />
						<PostFavoriteButton
							label={(favorited) =>
								favorited
									? t("pages.feed.unfavorite")
									: t("pages.feed.favorite")
							}
						/>
						<PostShareButton aria-label={t("pages.feed.share")} />
					</PostActions>
					<div className="rsf-post__discussion">
						<PostComments
							previewCount={RECENT_COMMENT_COUNT}
							pageSize={COMMENT_PAGE_SIZE}
							showMoreLabel={(remaining) =>
								t("pages.feed.show_more_comments", { count: remaining })
							}
							// A failed fetch shouldn't read as loading forever.
							loadingLabel={
								thread.isError ? undefined : t("pages.feed.loading_comments")
							}
							hideLabel={t("pages.feed.hide_comments")}
							replyLabel={t("pages.feed.reply")}
							deleteLabel={t("pages.feed.delete_comment")}
						/>
						<PostCommentForm
							placeholder={t("pages.feed.comment_placeholder")}
							inputLabel={t("pages.feed.comment_label")}
							submitLabel={t("pages.feed.post_comment")}
							replyingToLabel={(name) => t("pages.feed.replying_to", { name })}
							cancelReplyLabel={t("pages.feed.cancel_reply")}
						/>
					</div>
				</div>
			</PostRoot>
			<Dialog open={likersOpen} onOpenChange={setLikersOpen}>
				<DialogContent
					className="max-w-sm"
					aria-describedby={undefined}
					closeButtonLabel={t("common.close")}
				>
					<DialogHeader>
						<DialogTitle>{t("pages.feed.likers_title")}</DialogTitle>
					</DialogHeader>
					<PostLikers
						className="[--rsf-likers-max-height:60vh]"
						likers={likers.data?.results.map((liker) => ({
							id: String(liker.user),
							name: liker.user_display_name,
						}))}
						loading={likers.isPending}
						error={likers.error}
						onRetry={() => void likers.refetch()}
						loadingLabel={t("pages.feed.likers_loading")}
						emptyLabel={t("pages.feed.likers_empty")}
						errorLabel={t("pages.feed.likers_error")}
						retryLabel={t("pages.feed.retry")}
						listLabel={t("pages.feed.likers_title")}
					/>
					{likersHidden > 0 && (
						<p className="text-sm text-muted-foreground">
							{t("pages.feed.likers_more", { count: likersHidden })}
						</p>
					)}
				</DialogContent>
			</Dialog>
			<ConfirmDialog
				open={pendingDelete !== null}
				onOpenChange={(open) => {
					if (!open) setPendingDelete(null);
				}}
				title={t("pages.feed.delete_comment_title")}
				description={
					pendingDelete?.parentId
						? t("pages.feed.delete_comment_description")
						: t("pages.feed.delete_comment_thread_description")
				}
				confirmLabel={t("pages.feed.delete_comment_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={deleteComment.isPending}
				onConfirm={confirmDelete}
			/>
		</>
	);
}

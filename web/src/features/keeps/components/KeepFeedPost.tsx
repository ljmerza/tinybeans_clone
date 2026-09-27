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
	PostHeader,
	PostLikeButton,
	PostMedia,
	PostMediaCounter,
	PostMediaNextButton,
	PostMediaPrevButton,
	PostRoot,
	PostShareButton,
	PostTimestamp,
	PostTitle,
} from "react-social-feed";

import {
	useAddKeepComment,
	useKeepComments,
	useSetKeepLiked,
} from "../hooks/useKeepFeed";
import type { FeedKeep } from "../types";
import { keepToSocialPost } from "../utils/keepToSocialPost";

export interface KeepFeedPostProps {
	keep: FeedKeep;
	/** Open with the full comment thread loaded (e.g. on a shared link). */
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
	const addComment = useAddKeepComment();
	const [showAllComments, setShowAllComments] = useState(
		defaultCommentsExpanded,
	);
	const thread = useKeepComments(keep.id, showAllComments);

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

	return (
		<PostRoot
			post={post}
			defaultCommentsExpanded={defaultCommentsExpanded}
			onLikeChange={(liked) => setLiked.mutateAsync({ keep, liked })}
			onCommentSubmit={(text) =>
				addComment.mutateAsync({ keepId: keep.id, text })
			}
			onCommentsExpandedChange={setShowAllComments}
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
					/>
					<PostCommentButton aria-label={t("pages.feed.comment")} />
					<PostActionSpacer />
					<PostShareButton aria-label={t("pages.feed.share")} />
				</PostActions>
				<PostTitle />
				<PostCaption />
				<div className="rsf-post__discussion">
					<PostComments
						viewAllLabel={(count) =>
							t("pages.feed.view_all_comments", { count })
						}
						hideLabel={t("pages.feed.hide_comments")}
					/>
					<PostCommentForm
						placeholder={t("pages.feed.comment_placeholder")}
						inputLabel={t("pages.feed.comment_label")}
						submitLabel={t("pages.feed.post_comment")}
					/>
				</div>
			</div>
		</PostRoot>
	);
}

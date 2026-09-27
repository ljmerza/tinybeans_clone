import type { SocialPost } from "react-social-feed";

import type { FeedComment, FeedKeep } from "../types";

interface ToSocialPostOptions {
	/** Full thread, once loaded; otherwise the keep's recent comments are shown. */
	comments?: FeedComment[];
	/** Alt text for media without a caption or keep title. */
	fallbackAlt: string;
	/** Origin for the share link, e.g. window.location.origin. */
	origin: string;
}

export function keepSharePath(keepId: string) {
	return `/keeps/${keepId}`;
}

/**
 * Map a feed keep onto the react-social-feed post shape.
 */
export function keepToSocialPost(
	keep: FeedKeep,
	{ comments, fallbackAlt, origin }: ToSocialPostOptions,
): SocialPost {
	return {
		id: keep.id,
		author: { name: keep.created_by_display_name },
		title: keep.title || undefined,
		caption: keep.description || undefined,
		media: keep.media.map((media) => ({
			id: String(media.id),
			type: media.media_type === "video" ? "video" : "image",
			src: media.url,
			poster: media.poster_url ?? undefined,
			alt: media.caption || keep.title || fallbackAlt,
			width: media.width ?? undefined,
			height: media.height ?? undefined,
		})),
		createdAt: keep.date_of_memory,
		likeCount: keep.reaction_count,
		liked: keep.viewer_reaction !== null,
		commentCount: keep.comment_count,
		comments: (comments ?? keep.recent_comments).map((comment) => ({
			id: String(comment.id),
			author: { name: comment.user_display_name },
			text: comment.comment,
			createdAt: comment.created_at,
		})),
		shareUrl: `${origin}${keepSharePath(keep.id)}`,
	};
}

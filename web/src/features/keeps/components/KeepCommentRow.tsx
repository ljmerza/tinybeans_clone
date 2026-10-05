import { type ReactNode, useMemo } from "react";
import {
	type SocialComment,
	usePostContext,
	usePostIcons,
} from "react-social-feed";

import type { CommentMention } from "../types";
import { splitMentions } from "../utils/mentions";

export interface MentionTextProps {
	text: string;
	mentions?: CommentMention[];
}

/** Comment text with the members it @mentions highlighted. */
export function MentionText({ text, mentions }: MentionTextProps) {
	const segments = useMemo(
		() =>
			splitMentions(
				text,
				(mentions ?? []).map((mention) => mention.display_name),
			),
		[text, mentions],
	);
	let offset = 0;
	return (
		<span>
			{segments.map((segment) => {
				const key = offset;
				offset += segment.text.length;
				return segment.mention ? (
					<span key={key} className="font-semibold text-primary" data-mention>
						{segment.text}
					</span>
				) : (
					segment.text
				);
			})}
		</span>
	);
}

export interface KeepCommentRowProps {
	comment: SocialComment;
	mentions?: CommentMention[];
	replyLabel: ReactNode;
	deleteLabel: string;
}

/**
 * One comment, laid out like react-social-feed's default row (author, text,
 * reply and delete buttons) but with its @mentions highlighted. Rendered
 * through `PostComments`' `renderComment`, which supplies the list item.
 */
export function KeepCommentRow({
	comment,
	mentions,
	replyLabel,
	deleteLabel,
}: KeepCommentRowProps) {
	const { canComment, startReply, canDeleteComment, deleteComment } =
		usePostContext("KeepCommentRow");
	const icons = usePostIcons();

	return (
		<div className="rsf-post__comment-row">
			<div className="rsf-post__comment-body">
				<span className="rsf-post__author">{comment.author.name}</span>{" "}
				<MentionText text={comment.text} mentions={mentions} />
				{canComment && (
					<button
						type="button"
						className="rsf-post__comment-reply"
						onClick={() => startReply(comment)}
					>
						{replyLabel}
					</button>
				)}
			</div>
			{canDeleteComment(comment) && (
				<button
					type="button"
					className="rsf-post__comment-delete"
					aria-label={deleteLabel}
					onClick={() => deleteComment(comment)}
				>
					{icons.remove}
				</button>
			)}
		</div>
	);
}

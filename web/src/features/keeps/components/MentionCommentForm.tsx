import { cn } from "@/lib/utils";
import { type FormEvent, type ReactNode, useId, useState } from "react";
import { usePostContext, usePostIcons } from "react-social-feed";

import { useMentionableMembers } from "../hooks/useMentionableMembers";
import type { CommentMention } from "../types";
import {
	type MentionQuery,
	hasMention,
	insertMention,
	matchMentionable,
	mentionQueryAt,
} from "../utils/mentions";

export interface MentionCommentFormProps {
	/** Circle whose members can be @mentioned. */
	circleId: number;
	/**
	 * Called with the user ids the draft @mentions right before it is
	 * submitted, so the root's `onCommentSubmit` can send them along.
	 */
	onSubmitMentions: (userIds: number[]) => void;
	placeholder: string;
	/** Accessible label for the icon-only submit button. */
	submitLabel: string;
	inputLabel: string;
	/** Accessible label for the suggestion list. */
	suggestionsLabel: string;
	replyingToLabel: (name: string) => ReactNode;
	cancelReplyLabel: ReactNode;
}

/**
 * The comment composer, with @mention suggestions for the circle's members.
 *
 * Stands in for react-social-feed's `PostCommentForm` (same markup and
 * classes) because that form's input can't be extended. Typing "@" suggests
 * members; picking one inserts "@Name " and marks them mentioned. Replying
 * prefills an @tag of the person replied to, which counts as a mention too.
 * A mention whose "@Name" is edited out of the draft is dropped on submit.
 */
export function MentionCommentForm({
	circleId,
	onSubmitMentions,
	placeholder,
	submitLabel,
	inputLabel,
	suggestionsLabel,
	replyingToLabel,
	cancelReplyLabel,
}: MentionCommentFormProps) {
	const {
		canComment,
		isCommentPending,
		submitComment,
		commentInputRef,
		replyTo,
		cancelReply,
	} = usePostContext("MentionCommentForm");
	const icons = usePostIcons();
	const ids = useId();
	const [draft, setDraft] = useState("");
	const [picked, setPicked] = useState<CommentMention[]>([]);
	const [query, setQuery] = useState<MentionQuery | null>(null);
	const [activeIndex, setActiveIndex] = useState(0);

	// Start (or clear) the draft whenever a reply starts or ends.
	const [syncedReplyTo, setSyncedReplyTo] = useState(replyTo);
	if (syncedReplyTo !== replyTo) {
		setSyncedReplyTo(replyTo);
		setDraft(replyTo ? `@${replyTo.author.name} ` : "");
		setPicked(
			replyTo?.author.id
				? [
						{
							id: Number(replyTo.author.id),
							display_name: replyTo.author.name,
						},
					]
				: [],
		);
		setQuery(null);
	}

	// Past a picked name and the space after it, the mention is done.
	const typingMention =
		query !== null &&
		!picked.some((mention) =>
			query.text.startsWith(`${mention.display_name} `),
		);
	// Members load the first time someone starts typing a mention.
	const members = useMentionableMembers(circleId, typingMention);

	if (!canComment) return null;

	const suggestions = typingMention
		? matchMentionable(members.data ?? [], query.text)
		: [];
	const open = suggestions.length > 0;
	const active = open ? Math.min(activeIndex, suggestions.length - 1) : -1;
	const listId = `${ids}-mentions`;
	const optionId = (index: number) => `${ids}-mention-${index}`;

	const track = (input: HTMLInputElement) => {
		setQuery(
			mentionQueryAt(input.value, input.selectionStart ?? input.value.length),
		);
	};

	const pick = (member: CommentMention) => {
		if (!query) return;
		const next = insertMention(draft, query, member.display_name);
		setDraft(next.text);
		setPicked((current) => [
			...current.filter((mention) => mention.id !== member.id),
			member,
		]);
		setQuery(null);
		const input = commentInputRef.current;
		if (input) {
			input.focus();
			requestAnimationFrame(() =>
				input.setSelectionRange(next.caret, next.caret),
			);
		}
	};

	const submit = async (event: FormEvent) => {
		event.preventDefault();
		onSubmitMentions(
			picked
				.filter((mention) => hasMention(draft, mention.display_name))
				.map((mention) => mention.id),
		);
		if (await submitComment(draft)) {
			setDraft("");
			setPicked([]);
			setQuery(null);
		}
	};

	return (
		<>
			{replyTo && (
				<div className="rsf-post__replying">
					<span>{replyingToLabel(replyTo.author.name)}</span>
					<button
						type="button"
						className="rsf-post__replying-cancel"
						onClick={cancelReply}
					>
						{cancelReplyLabel}
					</button>
				</div>
			)}
			<form
				className="rsf-post__comment-form relative"
				onSubmit={(event) => void submit(event)}
			>
				<label htmlFor={`${ids}-input`} className="rsf-visually-hidden">
					{inputLabel}
				</label>
				<input
					id={`${ids}-input`}
					ref={(input) => {
						commentInputRef.current = input;
					}}
					className="rsf-post__comment-input"
					value={draft}
					placeholder={placeholder}
					autoComplete="off"
					disabled={isCommentPending}
					aria-autocomplete="list"
					aria-controls={open ? listId : undefined}
					aria-activedescendant={open ? optionId(active) : undefined}
					onChange={(event) => {
						setDraft(event.target.value);
						setActiveIndex(0);
						track(event.target);
					}}
					onSelect={(event) => track(event.currentTarget)}
					onBlur={() => setQuery(null)}
					onKeyDown={(event) => {
						if (open) {
							if (event.key === "ArrowDown" || event.key === "ArrowUp") {
								event.preventDefault();
								const step = event.key === "ArrowDown" ? 1 : -1;
								setActiveIndex(
									(active + step + suggestions.length) % suggestions.length,
								);
								return;
							}
							if (event.key === "Enter" || event.key === "Tab") {
								event.preventDefault();
								const member = suggestions[active];
								if (member) pick(member);
								return;
							}
							if (event.key === "Escape") {
								event.preventDefault();
								setQuery(null);
								return;
							}
						}
						if (event.key === "Escape" && replyTo) cancelReply();
					}}
				/>
				<button
					type="submit"
					className="rsf-post__comment-submit"
					aria-label={submitLabel}
					disabled={isCommentPending || draft.trim().length === 0}
				>
					{icons.send}
				</button>
				{open && (
					<ul
						id={listId}
						aria-label={suggestionsLabel}
						className="absolute bottom-full left-0 z-20 mb-1 w-full max-w-xs overflow-hidden rounded-md border border-border bg-popover py-1 text-popover-foreground shadow-md"
					>
						{suggestions.map((member, index) => (
							<li key={member.id}>
								{/* Arrow keys, Enter and Tab work from the input, so these stay out of the tab order. */}
								<button
									type="button"
									id={optionId(index)}
									tabIndex={-1}
									data-active={index === active || undefined}
									className={cn(
										"w-full truncate px-3 py-1.5 text-left text-sm",
										index === active && "bg-accent text-accent-foreground",
									)}
									// Keep focus in the input so the pick lands in the draft.
									onMouseDown={(event) => event.preventDefault()}
									onMouseEnter={() => setActiveIndex(index)}
									onClick={() => pick(member)}
								>
									{member.display_name}
								</button>
							</li>
						))}
					</ul>
				)}
			</form>
		</>
	);
}

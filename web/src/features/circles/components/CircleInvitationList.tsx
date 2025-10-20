import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	StatusMessage,
	ConfirmDialog,
	LoadingState,
	EmptyState,
} from '@/components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { showToast } from '@/lib/toast';
import type { ApiError } from '@/types';
import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
	useCancelCircleInvitation,
	useCircleInvitationsQuery,
	useResendCircleInvitation,
	useRemoveCircleMember,
} from '../hooks/useCircleInvitationAdmin';
import { useCircleMembers } from '../hooks/useCircleMemberships';
import type {
	CircleInvitationStatus,
	CircleInvitationSummary,
	CircleMemberSummary,
} from '../types';

interface CircleInvitationListProps {
	circleId: number | string;
}

const STATUS_VARIANTS: Record<
	CircleInvitationStatus,
	'default' | 'success' | 'warning' | 'destructive'
> = {
	pending: 'default',
	accepted: 'success',
	declined: 'destructive',
	cancelled: 'destructive',
	expired: 'warning',
};

function describeTimestamp(value: string | null, locale: string) {
	if (!value) return null;
	try {
		const date = new Date(value);
		return new Intl.DateTimeFormat(locale, {
			dateStyle: 'medium',
			timeStyle: 'short',
		}).format(date);
	} catch {
		return value;
	}
}

function sortInvitations(
	invitations: CircleInvitationSummary[] | undefined,
): CircleInvitationSummary[] {
	if (!invitations?.length) return [];
	return [...invitations].sort((a, b) => {
		const aTime = new Date(a.created_at).getTime();
		const bTime = new Date(b.created_at).getTime();
		return bTime - aTime;
	});
}

export function CircleInvitationList({ circleId }: CircleInvitationListProps) {
	const { t, i18n } = useTranslation();
	const invitationsQuery = useCircleInvitationsQuery(circleId);
	const resendInvitation = useResendCircleInvitation(circleId);
	const cancelInvitation = useCancelCircleInvitation(circleId);
	const removeMember = useRemoveCircleMember(circleId);
	const membersQuery = useCircleMembers(circleId);

	const [resendTarget, setResendTarget] = useState<string | null>(null);
	const [cancelTarget, setCancelTarget] = useState<string | null>(null);
	const [confirming, setConfirming] = useState<string | null>(null);
	const [removeTarget, setRemoveTarget] = useState<string | null>(null);
	const [removeConfirm, setRemoveConfirm] = useState<{
		invitation: CircleInvitationSummary;
		memberId?: string;
	} | null>(null);
	const [resolvingMemberFor, setResolvingMemberFor] = useState<string | null>(
		null,
	);
	const confirmingRemovalRef = useRef(false);

	const invitations = useMemo(
		() => sortInvitations(invitationsQuery.data),
		[invitationsQuery.data],
	);

	const normalizeString = (value: string | null | undefined) =>
		value?.trim().toLowerCase() ?? null;

	const normalizeId = (value: number | string | null | undefined) => {
		if (value === null || value === undefined) return null;
		const stringValue = String(value).trim();
		return stringValue.length ? stringValue : null;
	};

	const findMemberId = (
		invitation: CircleInvitationSummary,
		members: CircleMemberSummary[] | undefined,
	): string | null => {
		const invitedId =
			normalizeId(invitation.invited_user?.id) ??
			normalizeId(invitation.invited_user_id);

		if (invitedId) {
			return invitedId;
		}

		if (!members?.length) return null;
		const targetEmail = normalizeString(invitation.email);
		const targetUsername = normalizeString(invitation.invited_user?.username);

		for (const member of members) {
			const memberId = normalizeId(member.user.id);
			if (memberId && invitedId && memberId === invitedId) {
				return memberId;
			}
			const memberEmail = normalizeString(member.user.email);
			if (targetEmail && memberEmail === targetEmail) {
				return memberId ?? null;
			}
			const memberUsername = normalizeString(member.user.username);
			if (targetUsername && memberUsername === targetUsername) {
				return memberId ?? null;
			}
		}

		return null;
	};

	const resolveMemberId = (invitation: CircleInvitationSummary) =>
		findMemberId(invitation, membersQuery.data?.members);

	const handleResend = async (invitationId: string) => {
		setResendTarget(invitationId);
		try {
			await resendInvitation.mutateAsync(invitationId);
		} finally {
			setResendTarget(null);
		}
	};

	const handleCancel = async (invitationId: string) => {
		setCancelTarget(invitationId);
		try {
			await cancelInvitation.mutateAsync(invitationId);
		} finally {
			setCancelTarget(null);
			setConfirming(null);
		}
	};

	const ensureMemberId = async (
		invitation: CircleInvitationSummary,
	): Promise<string | null> => {
		const existing = resolveMemberId(invitation);
		if (existing) return existing;

		const refreshed = await membersQuery.refetch();
		return findMemberId(invitation, refreshed.data?.members);
	};

	const openRemoveDialog = (invitation: CircleInvitationSummary) => {
		const initialMemberId =
			resolveMemberId(invitation) ??
			normalizeId(invitation.invited_user?.id) ??
			normalizeId(invitation.invited_user_id) ??
			undefined;
		setRemoveConfirm({
			invitation,
			memberId: initialMemberId,
		});

		if (initialMemberId) return;

		setResolvingMemberFor(invitation.id);
		void ensureMemberId(invitation)
			.then((resolvedId) => {
				if (!resolvedId) {
					return;
				}
				setRemoveConfirm((current) =>
					current && current.invitation.id === invitation.id
						? { ...current, memberId: resolvedId }
						: current,
				);
			})
			.finally(() => {
				setResolvingMemberFor(null);
			});
	};

	const error = invitationsQuery.error as ApiError | null;

	const confirmId = confirming;


	return (
		<>
			<Card>
				<CardHeader className="space-y-2">
					<CardTitle>{t('pages.circles.invites.list.title')}</CardTitle>
					<CardDescription>
						{t('pages.circles.invites.list.description')}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					{invitationsQuery.isFetching ? (
						<LoadingState
							layout="inline"
							spinnerSize="sm"
							className="text-sm text-muted-foreground"
							message={t('pages.circles.invites.list.loading')}
						/>
					) : null}

					{error ? (
						<div className="space-y-3 rounded-md border border-destructive/30 bg-destructive/5 p-4">
							<StatusMessage variant="error">
								{error.message ??
									t('pages.circles.invites.list.error', {
										status: error.status ?? 500,
									})}
							</StatusMessage>
							<div className="flex justify-end">
								<Button
									variant="secondary"
									size="sm"
									onClick={() => invitationsQuery.refetch()}
									disabled={invitationsQuery.isFetching}
								>
									{t('pages.circles.invites.list.retry')}
								</Button>
							</div>
						</div>
					) : null}

					{invitations.length === 0 ? (
						<EmptyState
							title={t('pages.circles.invites.list.empty_title')}
							description={t('pages.circles.invites.list.empty_description')}
							actions={
								<Button
									variant="secondary"
									onClick={() => {
										if (typeof window !== 'undefined') {
											window.scrollTo({ top: 0, behavior: 'smooth' });
										}
									}}
								>
									{t('pages.circles.invites.list.empty_action')}
								</Button>
							}
						/>
					) : (
						<ul className="space-y-3">
							{invitations.map((invitation) => {
								const statusVariant = STATUS_VARIANTS[invitation.status];
								const createdAt = describeTimestamp(
									invitation.created_at,
									i18n.language,
								);
								const respondedAt = describeTimestamp(
									invitation.responded_at,
									i18n.language,
								);

								const isPending = invitation.status === 'pending';
								const isResending = resendTarget === invitation.id;
								const isCancelling = cancelTarget === invitation.id;
								const canRemove = invitation.status === 'accepted';
								const isRemoving =
									removeTarget === invitation.id && removeMember.isPending;
								const isResolving = resolvingMemberFor === invitation.id;
								const disableRemove =
									isResolving ||
									(removeMember.isPending && !isRemoving);

								return (
									<li
										key={invitation.id}
										className="border border-border rounded-md px-4 py-3 flex flex-col gap-3 transition-colors bg-card/60"
									>
										<div className="flex flex-wrap items-center justify-between gap-2">
											<div className="flex items-center gap-3">
												<div className="font-medium text-sm text-foreground">
													{invitation.email}
												</div>
												<Badge variant={statusVariant}>
													{t(`pages.circles.invites.status.${invitation.status as CircleInvitationStatus}`)}
												</Badge>
												{invitation.existing_user ? (
													<Badge variant="accent">
														{t('pages.circles.invites.list.existing_user')}
													</Badge>
												) : null}
											</div>
											<div className="flex items-center gap-2">
												{isPending ? (
													<>
														<Button
															variant="ghost"
															size="sm"
															onClick={() => void handleResend(invitation.id)}
															disabled={isResending || isCancelling}
														>
															{isResending
																? t('pages.circles.invites.list.resending')
																: t('pages.circles.invites.list.resend')}
														</Button>
														<Button
															variant="ghost"
															size="sm"
															className="text-destructive hover:text-destructive"
															onClick={() => setConfirming(invitation.id)}
															disabled={isCancelling || isResending}
														>
															{isCancelling
																? t('pages.circles.invites.list.cancelling')
																: t('pages.circles.invites.list.cancel')}
														</Button>
													</>
												) : null}
												{canRemove ? (
													<Button
														variant="ghost"
														size="sm"
														className="text-destructive hover:text-destructive"
														onClick={() => void openRemoveDialog(invitation)}
														disabled={disableRemove}
													>
														{isRemoving
															? t('pages.circles.invites.list.removing')
															: t('pages.circles.invites.list.remove')}
													</Button>
												) : null}
											</div>
										</div>

										<div className="text-xs text-muted-foreground space-y-1">
											{createdAt ? (
												<div>{t('pages.circles.invites.list.created_at', { createdAt })}</div>
											) : null}
											{respondedAt ? (
												<div>{t('pages.circles.invites.list.responded_at', { respondedAt })}</div>
											) : null}
											{invitation.reminder_sent_at ? (
												<div>
													{t('pages.circles.invites.list.reminder_sent_at', {
														reminderAt: describeTimestamp(invitation.reminder_sent_at, i18n.language),
													})}
												</div>
											) : null}
										</div>
									</li>
								);
							})}
						</ul>
					)}
				</CardContent>
			</Card>
			<ConfirmDialog
				open={Boolean(confirmId)}
				onOpenChange={(open) => {
					if (!open) {
						setConfirming(null);
						setCancelTarget(null);
					}
				}}
				title={t('pages.circles.invites.list.cancel_title')}
				description={t('pages.circles.invites.list.cancel_description')}
				confirmLabel={t('pages.circles.invites.list.cancel_confirm')}
				cancelLabel={t('common.cancel')}
				variant='destructive'
				isLoading={cancelInvitation.isPending}
				onConfirm={async () => {
					if (!confirmId) return;
					await handleCancel(confirmId);
				}}
			/>
			<ConfirmDialog
				open={Boolean(removeConfirm)}
				onOpenChange={(open) => {
					if (!open) {
						if (confirmingRemovalRef.current) {
							return;
						}
						setRemoveConfirm(null);
						setRemoveTarget(null);
					}
				}}
				title={t('pages.circles.invites.list.remove_title', {
					email: removeConfirm?.invitation.email ?? '',
				})}
				description={t('pages.circles.invites.list.remove_description')}
				confirmLabel={t('pages.circles.invites.list.remove_confirm')}
				cancelLabel={t('common.cancel')}
				variant='destructive'
				isLoading={removeMember.isPending}
				disabled={
					Boolean(removeConfirm && resolvingMemberFor === removeConfirm.invitation.id) &&
					!removeMember.isPending
				}
				onConfirm={async () => {
					const current = removeConfirm;
					if (!current) return;
					const { invitation } = current;

					confirmingRemovalRef.current = true;
					try {
						let memberId =
							normalizeId(current.memberId) ??
							normalizeId(invitation.invited_user?.id) ??
							normalizeId(invitation.invited_user_id);

						if (!memberId) {
							setResolvingMemberFor(invitation.id);
							try {
								memberId = await ensureMemberId(invitation);
							} finally {
								setResolvingMemberFor(null);
							}
						}

						if (!memberId) {
							showToast({
								message: t("pages.circles.invites.list.remove_error"),
								level: "error",
							});
							return;
						}

						setRemoveConfirm({ invitation, memberId });
						setRemoveTarget(invitation.id);
						await removeMember.mutateAsync(memberId);
						setRemoveConfirm(null);
					} finally {
						confirmingRemovalRef.current = false;
						setRemoveTarget(null);
					}
				}}
			/>
		</>
	);
}

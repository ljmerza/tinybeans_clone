import {Card, CardContent, CardDescription, CardHeader, CardTitle, StatusMessage, ConfirmDialog} from '@/components';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ApiError } from '@/types';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
	useCancelCircleInvitation,
	useCircleInvitationsQuery,
	useResendCircleInvitation,
} from '../hooks/useCircleInvitationAdmin';
import type { CircleInvitationStatus, CircleInvitationSummary } from '../types';

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

	const [resendTarget, setResendTarget] = useState<string | null>(null);
	const [cancelTarget, setCancelTarget] = useState<string | null>(null);
	const [confirming, setConfirming] = useState<string | null>(null);

	const invitations = useMemo(
		() => sortInvitations(invitationsQuery.data),
		[invitationsQuery.data],
	);

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

	const isLoading =
		invitationsQuery.isLoading ||
		resendInvitation.isPending ||
		cancelInvitation.isPending;

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
						<div className="flex items-center gap-2 text-sm text-muted-foreground">
							<LoadingSpinner size="sm" />
							<span>{t('pages.circles.invites.list.loading')}</span>
						</div>
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
							const isConfirming = confirmId === invitation.id;

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
											<Button
												variant="ghost"
												size="sm"
												onClick={() => void handleResend(invitation.id)}
												disabled={!isPending || isResending || isCancelling}
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
												disabled={!isPending || isCancelling || isResending}
											>
												{isCancelling
													? t('pages.circles.invites.list.cancelling')
													: t('pages.circles.invites.list.cancel')}
											</Button>
										</div>
									</div>

									<div className="text-xs text-muted-foreground space-y-1">
										{createdAt ? t('pages.circles.invites.list.created_at', { createdAt }) : null}
										{respondedAt
											? t('pages.circles.invites.list.responded_at', { respondedAt })
											: null}
										{invitation.reminder_sent_at
											? t('pages.circles.invites.list.reminder_sent_at', {
												reminderAt: describeTimestamp(invitation.reminder_sent_at, i18n.language),
											})
											: null}
									</div>
								</li>
							);
						})}
					</ul>
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
		</>
	);
}

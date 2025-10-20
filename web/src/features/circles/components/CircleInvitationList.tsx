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
import type { ApiError } from '@/types';
import { useTranslation } from 'react-i18next';

import { useCircleInvitationListController } from '../hooks/useCircleInvitationListController';
import type { CircleInvitationStatus } from '../types';
import { describeTimestamp } from '../utils/invitationHelpers';

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

export function CircleInvitationList({ circleId }: CircleInvitationListProps) {
	const { t, i18n } = useTranslation();
	const {
		invitations,
		query,
		resend,
		cancel,
		removal,
	} = useCircleInvitationListController(circleId);

	const error = query.error as ApiError | null;
	const confirmId = cancel.confirmId;

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
					{query.isFetching ? (
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
									onClick={() => query.refetch()}
									disabled={query.isFetching}
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
								const isResending = resend.targetId === invitation.id;
								const isCancelling = cancel.targetId === invitation.id;
								const canRemove = invitation.status === 'accepted';
								const isRemoving =
									removal.targetId === invitation.id && removal.isPending;
								const isResolving = removal.resolvingId === invitation.id;
								const disableRemove =
									isResolving ||
									(removal.isPending && !isRemoving);

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
															onClick={() => void resend.trigger(invitation.id)}
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
															onClick={() => cancel.open(invitation.id)}
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
														onClick={() => removal.open(invitation)}
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
				onOpenChange={cancel.close}
				title={t('pages.circles.invites.list.cancel_title')}
				description={t('pages.circles.invites.list.cancel_description')}
				confirmLabel={t('pages.circles.invites.list.cancel_confirm')}
				cancelLabel={t('common.cancel')}
				variant='destructive'
				isLoading={cancel.isPending}
				onConfirm={cancel.confirm}
			/>
			<ConfirmDialog
				open={Boolean(removal.dialog)}
				onOpenChange={removal.close}
				onCancel={removal.cancel}
				title={t('pages.circles.invites.list.remove_title', {
					email: removal.dialog?.invitation.email ?? '',
				})}
				description={t('pages.circles.invites.list.remove_description')}
				confirmLabel={t('pages.circles.invites.list.remove_confirm')}
				cancelLabel={t('common.cancel')}
				variant='destructive'
				isLoading={removal.isPending}
				disabled={
					Boolean(
						removal.dialog &&
							removal.resolvingId === removal.dialog.invitation.id,
					) && !removal.isPending
				}
				onConfirm={removal.confirm}
			/>
		</>
	);
}

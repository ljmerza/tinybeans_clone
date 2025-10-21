import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	ConfirmDialog,
	EmptyState,
	LoadingState,
	StatusMessage,
} from "@/components";
import { Button } from "@/components/ui/button";
import type { ApiError } from "@/types";
import { useTranslation } from "react-i18next";

import { useCircleInvitationListController } from "../hooks/useCircleInvitationListController";
import { CircleInvitationListItem } from "./CircleInvitationListItem";

interface CircleInvitationListProps {
	circleId: number | string;
}

export function CircleInvitationList({ circleId }: CircleInvitationListProps) {
	const { t, i18n } = useTranslation();
	const { invitations, query, resend, cancel, removal } =
		useCircleInvitationListController(circleId);

	const error = query.error as ApiError | null;
	const confirmId = cancel.confirmId;

	return (
		<>
			<Card>
				<CardHeader className="space-y-2">
					<CardTitle>{t("pages.circles.invites.list.title")}</CardTitle>
					<CardDescription>
						{t("pages.circles.invites.list.description")}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					{query.isFetching ? (
						<LoadingState
							layout="inline"
							spinnerSize="sm"
							className="text-sm text-muted-foreground"
							message={t("pages.circles.invites.list.loading")}
						/>
					) : null}

					{error ? (
						<div className="space-y-3 rounded-md border border-destructive/30 bg-destructive/5 p-4">
							<StatusMessage variant="error">
								{error.message ??
									t("pages.circles.invites.list.error", {
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
									{t("pages.circles.invites.list.retry")}
								</Button>
							</div>
						</div>
					) : null}

					{invitations.length === 0 ? (
						<EmptyState
							title={t("pages.circles.invites.list.empty_title")}
							description={t("pages.circles.invites.list.empty_description")}
							actions={
								<Button
									variant="secondary"
									onClick={() => {
										if (typeof window !== "undefined") {
											window.scrollTo({ top: 0, behavior: "smooth" });
										}
									}}
								>
									{t("pages.circles.invites.list.empty_action")}
								</Button>
							}
						/>
					) : (
						<ul className="space-y-3">
							{invitations.map((invitation) => (
								<CircleInvitationListItem
									key={invitation.id}
									invitation={invitation}
									t={t}
									language={i18n.language}
									actions={{
										resend,
										cancel,
										removal,
									}}
								/>
							))}
						</ul>
					)}
				</CardContent>
			</Card>
			<ConfirmDialog
				open={Boolean(confirmId)}
				onOpenChange={cancel.close}
				title={t("pages.circles.invites.list.cancel_title")}
				description={t("pages.circles.invites.list.cancel_description")}
				confirmLabel={t("pages.circles.invites.list.cancel_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={cancel.isPending}
				onConfirm={cancel.confirm}
			/>
			<ConfirmDialog
				open={Boolean(removal.dialog)}
				onOpenChange={removal.close}
				onCancel={removal.cancel}
				title={t("pages.circles.invites.list.remove_title", {
					email: removal.dialog?.invitation.email ?? "",
				})}
				description={t("pages.circles.invites.list.remove_description")}
				confirmLabel={t("pages.circles.invites.list.remove_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
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

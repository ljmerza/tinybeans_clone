import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	ConfirmDialog,
	EmptyState,
	StatusMessage,
	Layout,
} from "@/components";
import { Button } from "@/components/ui/button";
import { useAuthSession } from "@/features/auth";
import type { ApiError } from "@/types";
import { useTranslation } from "react-i18next";

import { useCircleMemberListController } from "../hooks/useCircleMemberListController";
import { CircleMemberListItem } from "./CircleMemberListItem";

interface CircleMemberListProps {
	circleId: number | string;
	isAdmin?: boolean;
}

export function CircleMemberList({ circleId, isAdmin = false }: CircleMemberListProps) {
	const { t, i18n } = useTranslation();
	const { user } = useAuthSession();
	const { members, query, removal } = useCircleMemberListController(circleId);

	const error = query.error as ApiError | null;

	return (
		<>
			<Card>
				<CardHeader className="space-y-2">
					<CardTitle>{t("pages.circles.members.list.title")}</CardTitle>
					<CardDescription>
						{t("pages.circles.members.list.description")}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					{query.isFetching ? (
						<Layout.Loading
							showHeader={false}
							layout="inline"
							spinnerSize="sm"
							className="text-sm text-muted-foreground"
							message={t("pages.circles.members.list.loading")}
						/>
					) : null}

					{error ? (
						<div className="space-y-3 rounded-md border border-destructive/30 bg-destructive/5 p-4">
							<StatusMessage variant="error">
								{error.message ??
									t("pages.circles.members.list.error", {
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
									{t("pages.circles.members.list.retry")}
								</Button>
							</div>
						</div>
					) : null}

					{members.length === 0 ? (
						<EmptyState
							title={t("pages.circles.members.list.empty_title")}
							description={t("pages.circles.members.list.empty_description")}
						/>
					) : (
						<ul className="space-y-3">
							{members.map((member) => (
								<CircleMemberListItem
									key={member.membership_id}
									member={member}
									t={t}
									language={i18n.language}
									currentUserId={user?.id}
									canRemoveMembers={isAdmin}
									actions={{
										remove: removal,
									}}
								/>
							))}
						</ul>
					)}
				</CardContent>
			</Card>
			<ConfirmDialog
				open={Boolean(removal.dialog)}
				onOpenChange={removal.close}
				onCancel={removal.cancel}
				title={t("pages.circles.members.list.remove_title", {
					name: removal.dialog?.user.display_name ?? removal.dialog?.user.email ?? "",
				})}
				description={t("pages.circles.members.list.remove_description")}
				confirmLabel={t("pages.circles.members.list.remove_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={removal.isPending}
				onConfirm={removal.confirm}
			/>
		</>
	);
}

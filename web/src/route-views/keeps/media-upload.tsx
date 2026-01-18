import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Layout, EmptyState } from "@/components";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/Card";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { CircleMediaSection } from "@/features/keeps";
import { useCircleMemberships } from "@/features/circles";

export function CircleMediaUploadView() {
	const { t } = useTranslation();
	const membershipsQuery = useCircleMemberships();
	const [selectedCircleId, setSelectedCircleId] = useState<string | null>(null);

	const adminMemberships = useMemo(
		() =>
			(membershipsQuery.data ?? []).filter(
				(membership) => membership.role === "admin" || membership.is_owner,
			),
		[membershipsQuery.data],
	);

	useEffect(() => {
		if (!adminMemberships.length) {
			setSelectedCircleId(null);
			return;
		}

		setSelectedCircleId((current) => {
			if (!current) {
				return String(adminMemberships[0]?.circle.id);
			}
			const stillExists = adminMemberships.some(
				(membership) => String(membership.circle.id) === current,
			);
			return stillExists ? current : String(adminMemberships[0]?.circle.id);
		});
	}, [adminMemberships]);

	if (membershipsQuery.isLoading && !membershipsQuery.data) {
		return (
			<Layout.Loading
				message={t("pages.keeps.upload.loading")}
				spinnerSize="sm"
			/>
		);
	}

	if (membershipsQuery.error) {
		return (
			<Layout.Error
				title={t("pages.keeps.upload.error_title")}
				message={t("pages.keeps.upload.error_message")}
				actionLabel={t("pages.keeps.upload.retry")}
				onAction={() => membershipsQuery.refetch()}
			/>
		);
	}

	if (!adminMemberships.length) {
		return (
			<Layout>
				<div className="container-page py-10">
					<EmptyState
						title={t("pages.keeps.upload.no_admin_title")}
						description={t("pages.keeps.upload.no_admin_description")}
					/>
				</div>
			</Layout>
		);
	}

	const hasSelection = Boolean(selectedCircleId);

	return (
		<Layout>
			<div className="container-page space-y-6">
				<div className="space-y-2">
					<h1 className="heading-2">
						{t("pages.keeps.upload.title")}
					</h1>
					<p className="text-subtitle">
						{t("pages.keeps.upload.description")}
					</p>
				</div>

				<Card>
					<CardHeader className="space-y-2">
						<CardTitle>{t("pages.keeps.upload.form_title")}</CardTitle>
						<CardDescription>
							{t("pages.keeps.upload.form_description")}
						</CardDescription>
					</CardHeader>
					<CardContent>
						<div className="space-y-2">
							<label className="text-sm font-medium text-foreground">
								{t("pages.keeps.upload.select_circle_label")}
							</label>
							<Select
								value={selectedCircleId ?? ""}
								onValueChange={(value) => setSelectedCircleId(value)}
								disabled={membershipsQuery.isFetching}
							>
								<SelectTrigger className="max-w-md">
									<SelectValue
										placeholder={t(
											"pages.keeps.upload.select_circle_placeholder",
										)}
									/>
								</SelectTrigger>
								<SelectContent>
									{adminMemberships.map((membership) => (
										<SelectItem
											key={membership.circle.id}
											value={String(membership.circle.id)}
										>
											{membership.circle.name}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					</CardContent>
				</Card>

				{hasSelection ? (
					<CircleMediaSection circleId={selectedCircleId!} isAdmin />
				) : (
					<EmptyState
						title={t("pages.keeps.upload.selection_title")}
						description={t("pages.keeps.upload.selection_description")}
					/>
				)}
			</div>
		</Layout>
	);
}

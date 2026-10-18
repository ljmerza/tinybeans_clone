import { ConfirmDialog, StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	useAiSettings,
	useScanMilestones,
	useTestAiConnection,
	useUpdateAiSettings,
} from "../hooks/useAiAssist";
import type { AvailableAiSettings } from "../types";

export interface CircleAiSettingProps {
	circleId: number | string;
}

/**
 * The in-app AI milestone switch on a circle's settings page, with a
 * connection test, the last scan's status and "Scan now". Turning it on asks
 * the admin to accept that captions go to the operator's AI service. Renders
 * nothing while the operator hasn't set AI up. Only render it for circle
 * admins.
 */
export function CircleAiSetting({ circleId }: CircleAiSettingProps) {
	const settings = useAiSettings(circleId);
	if (!settings.data?.available) return null;
	return <AiSettingCard circleId={circleId} settings={settings.data} />;
}

function AiSettingCard({
	circleId,
	settings,
}: {
	circleId: number | string;
	settings: AvailableAiSettings;
}) {
	const { t, i18n } = useTranslation();
	const ids = useId();
	const save = useUpdateAiSettings(circleId);
	const test = useTestAiConnection(circleId);
	const scan = useScanMilestones(circleId);
	const [confirming, setConfirming] = useState(false);
	const [acknowledged, setAcknowledged] = useState(false);

	// Show the requested state while it saves, so the switch doesn't jump back.
	const checked = save.isPending
		? (save.variables?.enabled ?? settings.enabled)
		: settings.enabled;

	const codeLabel = (code: string) =>
		t(`pages.circles.dashboard.ai_assist.codes.${code}`, {
			defaultValue: t("pages.circles.dashboard.ai_assist.codes.unknown"),
		});
	const formatDateTime = (value: string) =>
		new Intl.DateTimeFormat(i18n.language, {
			dateStyle: "medium",
			timeStyle: "short",
		}).format(new Date(value));

	const closeConfirm = () => {
		setConfirming(false);
		setAcknowledged(false);
	};

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-4">
			<div className="flex items-center justify-between gap-4">
				<div className="space-y-1">
					<Label htmlFor={`${ids}-enabled`}>
						{t("pages.circles.dashboard.ai_assist.title")}
					</Label>
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.ai_assist.description")}
					</p>
				</div>
				<Switch
					id={`${ids}-enabled`}
					checked={checked}
					disabled={save.isPending}
					onCheckedChange={(next) => {
						if (next) {
							setConfirming(true);
						} else {
							save.mutate({ enabled: false });
						}
					}}
				/>
			</div>

			<div className="space-y-1 text-sm text-muted-foreground">
				<p>
					{settings.last_success_at
						? t("pages.circles.dashboard.ai_assist.last_success", {
								when: formatDateTime(settings.last_success_at),
							})
						: t("pages.circles.dashboard.ai_assist.never_succeeded")}
				</p>
				{settings.last_error && (
					<p className="text-amber-700 dark:text-amber-400">
						{t("pages.circles.dashboard.ai_assist.last_error", {
							error: codeLabel(settings.last_error),
						})}
					</p>
				)}
				{settings.pending_count > 0 && (
					<p>
						{t("pages.circles.dashboard.ai_assist.pending", {
							count: settings.pending_count,
						})}
					</p>
				)}
			</div>

			<div className="flex flex-wrap gap-2">
				<Button
					type="button"
					size="sm"
					variant="outline"
					isLoading={test.isPending}
					onClick={() => test.mutate()}
				>
					{t("pages.circles.dashboard.ai_assist.test")}
				</Button>
				{settings.enabled && (
					<Button
						type="button"
						size="sm"
						variant="outline"
						isLoading={scan.isPending}
						onClick={() => scan.mutate()}
					>
						{t("pages.circles.dashboard.ai_assist.scan_now")}
					</Button>
				)}
			</div>
			{test.data && !test.isPending && (
				<StatusMessage variant={test.data.ok ? "success" : "error"}>
					{test.data.ok
						? t("pages.circles.dashboard.ai_assist.test_ok", {
								ms: test.data.latency_ms,
							})
						: t("pages.circles.dashboard.ai_assist.test_error", {
								error: codeLabel(test.data.code),
							})}
				</StatusMessage>
			)}

			<ConfirmDialog
				open={confirming}
				onOpenChange={(open) => !open && closeConfirm()}
				title={t("pages.circles.dashboard.ai_assist.confirm_title")}
				description={t("pages.circles.dashboard.ai_assist.disclosure")}
				confirmLabel={t("pages.circles.dashboard.ai_assist.confirm")}
				cancelLabel={t("common.cancel")}
				disabled={!acknowledged}
				isLoading={save.isPending}
				onConfirm={async () => {
					try {
						await save.mutateAsync({
							enabled: true,
							acknowledge_data_sharing: true,
						});
						closeConfirm();
					} catch {
						// The mutation's error toast explains it; leave the dialog open to retry.
					}
				}}
			>
				<label className="flex cursor-pointer items-start gap-3 text-sm">
					<input
						type="checkbox"
						className="mt-0.5 size-4 shrink-0 accent-primary"
						checked={acknowledged}
						onChange={(event) => setAcknowledged(event.target.checked)}
					/>
					<span>{t("pages.circles.dashboard.ai_assist.acknowledge")}</span>
				</label>
			</ConfirmDialog>
		</div>
	);
}

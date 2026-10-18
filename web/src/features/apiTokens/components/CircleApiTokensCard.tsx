import { ConfirmDialog } from "@/components";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type ReactNode, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useApiTokens, useRevokeApiToken } from "../hooks/useApiTokens";
import type { ApiToken } from "../types";
import { CreateApiTokenDialog } from "./CreateApiTokenDialog";

/** Revoked or expired tokens older than this are collapsed. */
const COLLAPSE_AFTER_MS = 30 * 86_400_000;

/** When a token stopped working, or null while it still works. */
function endedAt(token: ApiToken): number | null {
	if (token.status === "revoked" && token.revoked_at) {
		return Date.parse(token.revoked_at);
	}
	if (token.status === "expired" && token.expires_at) {
		return Date.parse(token.expires_at);
	}
	return null;
}

export interface CircleApiTokensCardProps {
	circleId: number | string;
}

/**
 * A circle's API tokens, for the agent API and MCP clients: create one (with
 * an emailed re-authentication code) and revoke them. Only render it for
 * circle admins; the API refuses anyone else.
 */
export function CircleApiTokensCard({ circleId }: CircleApiTokensCardProps) {
	const { t } = useTranslation();
	const tokens = useApiTokens(circleId);
	const revoke = useRevokeApiToken(circleId);
	const [creating, setCreating] = useState(false);
	const [revoking, setRevoking] = useState<ApiToken | null>(null);
	const [showOlder, setShowOlder] = useState(false);

	const [recent, older] = useMemo(() => {
		const cutoff = Date.now() - COLLAPSE_AFTER_MS;
		const all = tokens.data?.tokens ?? [];
		const isOld = (token: ApiToken) => {
			const ended = endedAt(token);
			return ended !== null && ended < cutoff;
		};
		return [all.filter((token) => !isOld(token)), all.filter(isOld)];
	}, [tokens.data]);

	const enabled = tokens.data?.agent_api_enabled ?? false;

	let body: ReactNode;
	if (tokens.isPending) {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("pages.circles.dashboard.api_tokens.loading")}
			</p>
		);
	} else if (tokens.isError) {
		body = (
			<p className="text-sm text-destructive">
				{t("pages.circles.dashboard.api_tokens.load_failed")}
			</p>
		);
	} else if (recent.length + older.length === 0) {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("pages.circles.dashboard.api_tokens.empty")}
			</p>
		);
	} else {
		body = (
			<div className="space-y-3">
				<ul className="divide-y divide-border rounded-md border border-border">
					{(showOlder ? [...recent, ...older] : recent).map((token) => (
						<ApiTokenRow
							key={token.id}
							token={token}
							onRevoke={() => setRevoking(token)}
						/>
					))}
				</ul>
				{older.length > 0 && (
					<Button
						type="button"
						variant="link"
						size="sm"
						onClick={() => setShowOlder((value) => !value)}
					>
						{showOlder
							? t("pages.circles.dashboard.api_tokens.hide_older")
							: t("pages.circles.dashboard.api_tokens.show_older", {
									count: older.length,
								})}
					</Button>
				)}
			</div>
		);
	}

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-4">
			<div className="flex items-start justify-between gap-4">
				<div className="space-y-1">
					<h2 className="text-sm font-medium leading-none">
						{t("pages.circles.dashboard.api_tokens.title")}
					</h2>
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.api_tokens.description")}
					</p>
				</div>
				<Button
					type="button"
					size="sm"
					variant="outline"
					className="shrink-0"
					disabled={!enabled}
					onClick={() => setCreating(true)}
				>
					{t("pages.circles.dashboard.api_tokens.create_action")}
				</Button>
			</div>
			{tokens.data && !enabled && (
				<p className="text-sm text-amber-700 dark:text-amber-400">
					{t("pages.circles.dashboard.api_tokens.disabled")}
				</p>
			)}
			{body}
			{creating && (
				<CreateApiTokenDialog circleId={circleId} onOpenChange={setCreating} />
			)}
			<ConfirmDialog
				open={revoking !== null}
				onOpenChange={(open) => !open && setRevoking(null)}
				title={t("pages.circles.dashboard.api_tokens.revoke_title")}
				description={t(
					"pages.circles.dashboard.api_tokens.revoke_description",
					{ name: revoking?.name ?? "" },
				)}
				confirmLabel={t("pages.circles.dashboard.api_tokens.revoke_confirm")}
				cancelLabel={t("common.cancel")}
				variant="destructive"
				isLoading={revoke.isPending}
				onConfirm={async () => {
					if (!revoking) return;
					try {
						await revoke.mutateAsync(revoking.id);
						setRevoking(null);
					} catch {
						// The mutation's error toast explains it; leave the dialog open to retry.
					}
				}}
			/>
		</div>
	);
}

function ApiTokenRow({
	token,
	onRevoke,
}: {
	token: ApiToken;
	onRevoke: () => void;
}) {
	const { t, i18n } = useTranslation();
	const formatDate = (value: string) =>
		new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(
			new Date(value),
		);
	const formatDateTime = (value: string) =>
		new Intl.DateTimeFormat(i18n.language, {
			dateStyle: "medium",
			timeStyle: "short",
		}).format(new Date(value));

	const lastUsed = token.last_used_at
		? token.last_used_ip
			? t("pages.circles.dashboard.api_tokens.last_used_from", {
					when: formatDateTime(token.last_used_at),
					ip: token.last_used_ip,
				})
			: t("pages.circles.dashboard.api_tokens.last_used", {
					when: formatDateTime(token.last_used_at),
				})
		: t("pages.circles.dashboard.api_tokens.never_used");

	return (
		<li className="flex flex-wrap items-start justify-between gap-3 p-3">
			<div className="min-w-0 space-y-1">
				<div className="flex flex-wrap items-center gap-2">
					<span className="font-medium">{token.name}</span>
					<Badge variant={token.status === "active" ? "success" : "default"}>
						{t(`pages.circles.dashboard.api_tokens.status.${token.status}`)}
					</Badge>
					{token.can_suggest && (
						<Badge variant="accent">
							{t("pages.circles.dashboard.api_tokens.can_suggest_badge")}
						</Badge>
					)}
				</div>
				<p className="font-mono text-xs text-muted-foreground">
					{token.display_prefix}…
				</p>
				{token.status === "revoked" && token.revoked_reason && (
					<p className="text-xs text-muted-foreground">
						{t(
							`pages.circles.dashboard.api_tokens.revoked_reasons.${token.revoked_reason}`,
						)}
					</p>
				)}
				<p className="text-xs text-muted-foreground">
					{t("pages.circles.dashboard.api_tokens.created", {
						name: token.created_by.display_name,
						when: formatDate(token.created_at),
					})}
				</p>
				<p className="text-xs text-muted-foreground">{lastUsed}</p>
				<p className="text-xs text-muted-foreground">
					{token.expires_at
						? t("pages.circles.dashboard.api_tokens.expires", {
								when: formatDate(token.expires_at),
							})
						: t("pages.circles.dashboard.api_tokens.expires_never")}
				</p>
			</div>
			{token.status === "active" && (
				<Button
					type="button"
					size="sm"
					variant="ghost"
					className="text-muted-foreground hover:text-destructive"
					aria-label={t("pages.circles.dashboard.api_tokens.revoke_label", {
						name: token.name,
					})}
					onClick={onRevoke}
				>
					{t("pages.circles.dashboard.api_tokens.revoke")}
				</Button>
			)}
		</li>
	);
}

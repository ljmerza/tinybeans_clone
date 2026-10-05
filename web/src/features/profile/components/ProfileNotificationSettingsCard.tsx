import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useCircleMemberships } from "@/features/circles";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
	useNotificationPreferences,
	useNotificationPreferencesMutation,
} from "../hooks/useNotificationPreferences";
import { NotificationChannelSettings } from "./NotificationChannelSettings";

const DEFAULT_SCOPE = "default";

const EVENTS = [
	{ field: "notify_new_media", key: "new_media" },
	{ field: "notify_comments", key: "comments" },
	{ field: "notify_replies", key: "replies" },
	{ field: "notify_likes", key: "likes" },
] as const;

export function ProfileNotificationSettingsCard() {
	const { t } = useTranslation();
	const [scope, setScope] = useState(DEFAULT_SCOPE);
	const circleId = scope === DEFAULT_SCOPE ? null : Number(scope);
	const memberships = useCircleMemberships();
	const preferences = useNotificationPreferences(circleId);
	const save = useNotificationPreferencesMutation(circleId);
	const prefs = preferences.data;

	return (
		<div className="space-y-6">
			<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-6">
				<div className="space-y-2">
					<h2 className="text-xl font-semibold">
						{t("profile.notifications.title")}
					</h2>
					<p className="text-sm text-muted-foreground">
						{t("profile.notifications.description")}
					</p>
				</div>

				<div className="space-y-2">
					<Label htmlFor="notification-scope">
						{t("profile.notifications.scope_label")}
					</Label>
					<Select value={scope} onValueChange={setScope}>
						<SelectTrigger id="notification-scope" className="w-full">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value={DEFAULT_SCOPE}>
								{t("profile.notifications.scope_default")}
							</SelectItem>
							{(memberships.data ?? []).map(({ circle }) => (
								<SelectItem key={circle.id} value={String(circle.id)}>
									{circle.name}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>

				{!prefs ? (
					preferences.isError ? (
						<p className="text-sm text-destructive">
							{t("profile.notifications.load_error")}
						</p>
					) : (
						<Layout.Loading
							showHeader={false}
							layout="section"
							className="py-10"
							spinnerSize="md"
							message={t("common.loading", { defaultValue: "Loading..." })}
						/>
					)
				) : (
					<>
						{circleId !== null && (
							<div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-muted px-4 py-3">
								<p className="text-sm text-muted-foreground">
									{prefs.per_circle_override
										? t("profile.notifications.circle_override")
										: t("profile.notifications.circle_uses_default")}
								</p>
								{prefs.per_circle_override && (
									<Button
										variant="outline"
										size="sm"
										disabled={save.isPending}
										onClick={() => save.mutate("reset")}
									>
										{t("profile.notifications.use_default")}
									</Button>
								)}
							</div>
						)}

						<ul className="divide-y divide-border">
							{EVENTS.map(({ field, key }) => (
								<li
									key={field}
									className="flex items-center justify-between gap-4 py-3"
								>
									<div className="space-y-1">
										<Label htmlFor={`notify-${key}`}>
											{t(`profile.notifications.events.${key}.title`)}
										</Label>
										<p className="text-sm text-muted-foreground">
											{t(`profile.notifications.events.${key}.description`)}
										</p>
									</div>
									<Switch
										id={`notify-${key}`}
										checked={prefs[field]}
										disabled={save.isPending}
										onCheckedChange={(checked) =>
											save.mutate({ [field]: checked })
										}
									/>
								</li>
							))}
						</ul>

						{/* The digest covers every circle, so it's a default-only setting. */}
						{circleId === null && (
							<div className="flex items-center justify-between gap-4">
								<div className="space-y-1">
									<Label htmlFor="notify-digest">
										{t("profile.notifications.digest.title")}
									</Label>
									<p className="text-sm text-muted-foreground">
										{t("profile.notifications.digest.description")}
									</p>
								</div>
								<Switch
									id="notify-digest"
									checked={prefs.email_digest}
									disabled={save.isPending}
									onCheckedChange={(checked) =>
										save.mutate({ email_digest: checked })
									}
								/>
							</div>
						)}

						<NotificationChannelSettings
							preferences={prefs}
							isDefaultScope={circleId === null}
							saving={save.isPending}
							onChange={(change) => save.mutate(change)}
							onPushSubscribed={() => {
								if (!prefs.push_enabled) save.mutate({ push_enabled: true });
							}}
						/>
					</>
				)}
			</div>
		</div>
	);
}

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
import type { NotificationChannel } from "../api/services";
import {
	useNotificationPreferences,
	useNotificationPreferencesMutation,
} from "../hooks/useNotificationPreferences";

const DEFAULT_SCOPE = "default";

const EVENTS = [
	{ field: "notify_new_media", key: "new_media" },
	{ field: "notify_comments", key: "comments" },
	{ field: "notify_replies", key: "replies" },
	{ field: "notify_likes", key: "likes" },
] as const;

// Phone delivery isn't built yet; the API rejects it until it is.
const CHANNELS: { value: NotificationChannel; available: boolean }[] = [
	{ value: "email", available: true },
	{ value: "sms", available: false },
];

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

						<div className="space-y-2">
							<Label htmlFor="notification-channel">
								{t("profile.notifications.channel_label")}
							</Label>
							<p className="text-sm text-muted-foreground">
								{t("profile.notifications.channel_description")}
							</p>
							<Select
								value={prefs.channel}
								disabled={save.isPending}
								onValueChange={(channel) =>
									save.mutate({ channel: channel as NotificationChannel })
								}
							>
								<SelectTrigger id="notification-channel" className="w-full">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{CHANNELS.map(({ value, available }) => (
										<SelectItem key={value} value={value} disabled={!available}>
											{available
												? t(`profile.notifications.channels.${value}`)
												: t("profile.notifications.channel_coming_soon", {
														channel: t(
															`profile.notifications.channels.${value}`,
														),
													})}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					</>
				)}
			</div>
		</div>
	);
}

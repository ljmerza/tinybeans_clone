import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTranslation } from "react-i18next";
import type {
	NotificationPreferences,
	UpdateNotificationPreferencesRequest,
} from "../api/services";
import { useNotificationChannels } from "../hooks/useNotificationChannels";
import { NotificationPhoneSetup } from "./NotificationPhoneSetup";
import { PushDeviceSetup } from "./PushDeviceSetup";

interface NotificationChannelSettingsProps {
	preferences: NotificationPreferences;
	/** The default (all circles) scope, where the phone and devices are set up. */
	isDefaultScope: boolean;
	saving: boolean;
	onChange: (change: UpdateNotificationPreferencesRequest) => void;
	/** Switch push on in the default preferences after this device subscribes. */
	onPushSubscribed: () => void;
}

/** Email, text message and push switches, plus phone and device setup. */
export function NotificationChannelSettings({
	preferences,
	isDefaultScope,
	saving,
	onChange,
	onPushSubscribed,
}: NotificationChannelSettingsProps) {
	const { t } = useTranslation();
	const channels = useNotificationChannels().data;
	// Texts only go to a confirmed phone, so the switch waits for one.
	const phoneReady = channels?.phone_verified ?? false;

	const rows = [
		{ field: "email_enabled", key: "email", shown: true, disabled: false },
		{
			field: "sms_enabled",
			key: "sms",
			shown: channels?.sms_available ?? false,
			disabled: !phoneReady,
		},
		{
			field: "push_enabled",
			key: "push",
			shown: channels?.push_available ?? false,
			disabled: false,
		},
	] as const;

	return (
		<div className="space-y-3">
			<div className="space-y-1">
				<h3 className="font-medium">
					{t("profile.notifications.channels_title")}
				</h3>
				<p className="text-sm text-muted-foreground">
					{t("profile.notifications.channels_description")}
				</p>
			</div>

			<ul className="divide-y divide-border">
				{rows
					.filter((row) => row.shown)
					.map(({ field, key, disabled }) => (
						<li
							key={field}
							className="flex items-center justify-between gap-4 py-3"
						>
							<div className="space-y-1">
								<Label htmlFor={`channel-${key}`}>
									{t(`profile.notifications.channels.${key}`)}
								</Label>
								<p className="text-sm text-muted-foreground">
									{key === "sms" && disabled
										? t(
												isDefaultScope
													? "profile.notifications.sms_needs_phone"
													: "profile.notifications.sms_needs_phone_default",
											)
										: t(`profile.notifications.channel_descriptions.${key}`)}
								</p>
							</div>
							<Switch
								id={`channel-${key}`}
								checked={preferences[field] && !disabled}
								disabled={saving || disabled}
								onCheckedChange={(checked) => onChange({ [field]: checked })}
							/>
						</li>
					))}
			</ul>

			{isDefaultScope && channels?.sms_available && (
				<NotificationPhoneSetup
					// Start fresh when the saved number changes.
					key={channels.phone_number ?? "none"}
					channels={channels}
				/>
			)}
			{isDefaultScope && channels?.push_available && (
				<PushDeviceSetup channels={channels} onSubscribed={onPushSubscribed} />
			)}
		</div>
	);
}

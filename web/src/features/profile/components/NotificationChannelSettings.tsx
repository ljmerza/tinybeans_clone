import { cn } from "@/lib/utils";
import { Bell, type LucideIcon, Mail, MessageSquare } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
	NOTIFICATION_EVENTS,
	type NotificationChannel,
	type NotificationPreferences,
	type UpdateNotificationPreferencesRequest,
} from "../api/services";
import { useNotificationChannels } from "../hooks/useNotificationChannels";
import { getPushSupport } from "../utils/webPush";
import { NotificationPhoneSetup } from "./NotificationPhoneSetup";
import { PushDeviceSetup } from "./PushDeviceSetup";

const CHANNEL_ICONS: Record<NotificationChannel, LucideIcon> = {
	email: Mail,
	sms: MessageSquare,
	push: Bell,
};

interface ChannelColumn {
	channel: NotificationChannel;
	shown: boolean;
	/** Offered, but not usable until a phone or device is set up. */
	blocked: boolean;
}

interface NotificationChannelSettingsProps {
	preferences: NotificationPreferences;
	/** The default (all circles) scope, where the phone and devices are set up. */
	isDefaultScope: boolean;
	saving: boolean;
	onChange: (change: UpdateNotificationPreferencesRequest) => void;
}

/**
 * One row per event with an email, text message and push toggle each. The text
 * column shows only when the server offers SMS, and push only when it offers
 * push. Texts wait for a confirmed phone, pushes for a subscribed device.
 */
export function NotificationChannelSettings({
	preferences,
	isDefaultScope,
	saving,
	onChange,
}: NotificationChannelSettingsProps) {
	const { t } = useTranslation();
	const channels = useNotificationChannels().data;
	const [pushSupport] = useState(getPushSupport);
	const smsBlocked = !(channels?.phone_verified ?? false);
	// Pushes go to every subscribed device, so any one of them is enough.
	const pushBlocked = (channels?.push_device_count ?? 0) === 0;

	const allColumns: ChannelColumn[] = [
		{ channel: "email", shown: true, blocked: false },
		{
			channel: "sms",
			shown: channels?.sms_available ?? false,
			blocked: smsBlocked,
		},
		{
			channel: "push",
			shown: channels?.push_available ?? false,
			blocked: pushBlocked,
		},
	];
	const columns = allColumns.filter((column) => column.shown);
	const showSmsHint = (channels?.sms_available ?? false) && smsBlocked;
	const showPushHint = (channels?.push_available ?? false) && pushBlocked;

	let pushHint = "profile.notifications.push_needs_device_default";
	if (pushSupport === "unsupported") {
		pushHint = "profile.notifications.push_unsupported";
	} else if (isDefaultScope) {
		pushHint = "profile.notifications.push_needs_device";
	}

	return (
		<div className="space-y-2">
			{/* Column headings for the eye; each toggle is named on its own. */}
			<div className="flex justify-end gap-1" aria-hidden="true">
				{columns.map(({ channel }) => (
					<span
						key={channel}
						className="w-11 text-center text-xs text-muted-foreground"
					>
						{t(`profile.notifications.channels_short.${channel}`)}
					</span>
				))}
			</div>

			<ul className="divide-y divide-border">
				{NOTIFICATION_EVENTS.map((event) => (
					<li
						key={event}
						className="flex items-center justify-between gap-3 py-3"
					>
						<div className="min-w-0 space-y-1">
							<p
								id={`notify-${event}-title`}
								className="text-sm leading-none font-medium"
							>
								{t(`profile.notifications.events.${event}.title`)}
							</p>
							<p className="text-sm text-muted-foreground">
								{t(`profile.notifications.events.${event}.description`)}
							</p>
						</div>
						<fieldset
							aria-labelledby={`notify-${event}-title`}
							className="flex shrink-0 gap-1"
						>
							{columns.map(({ channel, blocked }) => {
								const field = `${event}_${channel}` as const;
								const on = preferences[field] && !blocked;
								const label = t(`profile.notifications.channels.${channel}`);
								const Icon = CHANNEL_ICONS[channel];
								return (
									<span key={channel} className="flex w-11 justify-center">
										<button
											type="button"
											aria-pressed={on}
											aria-label={label}
											title={label}
											disabled={saving || blocked}
											onClick={() => onChange({ [field]: !on })}
											className={cn(
												"inline-flex size-10 items-center justify-center rounded-full border transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50",
												on
													? "border-primary bg-primary text-primary-foreground"
													: "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
											)}
										>
											<Icon className="size-5" aria-hidden="true" />
										</button>
									</span>
								);
							})}
						</fieldset>
					</li>
				))}
			</ul>

			{channels?.sms_available && (
				<p className="text-sm text-muted-foreground">
					{t("profile.notifications.channel_descriptions.sms")}
				</p>
			)}
			{showSmsHint && (
				<p className="text-sm text-muted-foreground">
					{t(
						isDefaultScope
							? "profile.notifications.sms_needs_phone"
							: "profile.notifications.sms_needs_phone_default",
					)}
				</p>
			)}
			{showPushHint && (
				<p className="text-sm text-muted-foreground">{t(pushHint)}</p>
			)}
		</div>
	);
}

interface NotificationChannelSetupProps {
	/** Called once this device is subscribed to push. */
	onPushSubscribed: () => void;
}

/** The phone texts go to and push on this device; default scope only. */
export function NotificationChannelSetup({
	onPushSubscribed,
}: NotificationChannelSetupProps) {
	const channels = useNotificationChannels().data;
	if (!channels) return null;
	return (
		<>
			{channels.sms_available && (
				<NotificationPhoneSetup
					// Start fresh when the saved number changes.
					key={channels.phone_number ?? "none"}
					channels={channels}
				/>
			)}
			{channels.push_available && (
				<PushDeviceSetup channels={channels} onSubscribed={onPushSubscribed} />
			)}
		</>
	);
}

import { Button } from "@/components/ui/button";
import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { NotificationChannels } from "../api/services";
import { usePushSubscriptionMutation } from "../hooks/useNotificationChannels";
import {
	PushPermissionDeniedError,
	getNotificationPermission,
	getPushSubscription,
	getPushSupport,
	subscribeToPush,
	unsubscribeFromPush,
} from "../utils/webPush";

interface PushDeviceSetupProps {
	channels: NotificationChannels;
	/** Called once this device is subscribed, so push can be switched on. */
	onSubscribed?: () => void;
}

/** Turn push on or off for the browser (or installed app) in use right now. */
export function PushDeviceSetup({
	channels,
	onSubscribed,
}: PushDeviceSetupProps) {
	const { t } = useTranslation();
	const save = usePushSubscriptionMutation();
	const [support] = useState(getPushSupport);
	const [permission, setPermission] = useState(getNotificationPermission);
	const [subscribed, setSubscribed] = useState(false);
	const [busy, setBusy] = useState(false);
	const [failed, setFailed] = useState(false);

	useEffect(() => {
		if (support !== "supported") return;
		let active = true;
		getPushSubscription()
			.then((subscription) => {
				if (active) setSubscribed(subscription !== null);
			})
			.catch(() => undefined);
		return () => {
			active = false;
		};
	}, [support]);

	const enable = async () => {
		setBusy(true);
		setFailed(false);
		try {
			const subscription = await subscribeToPush(channels.vapid_public_key);
			await save.mutateAsync({ subscribe: subscription });
			setSubscribed(true);
			onSubscribed?.();
		} catch (error) {
			if (error instanceof PushPermissionDeniedError) {
				setPermission(getNotificationPermission());
			} else {
				setFailed(true);
			}
		} finally {
			setBusy(false);
		}
	};

	const disable = async () => {
		setBusy(true);
		setFailed(false);
		try {
			const endpoint = await unsubscribeFromPush();
			if (endpoint) {
				await save.mutateAsync({ remove: endpoint });
			}
			setSubscribed(false);
		} catch {
			setFailed(true);
		} finally {
			setBusy(false);
		}
	};

	let body: ReactNode;
	if (support === "unsupported") {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("profile.notifications.push.unsupported")}
			</p>
		);
	} else if (support === "install-required") {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("profile.notifications.push.install_required")}
			</p>
		);
	} else if (subscribed) {
		body = (
			<div className="flex flex-wrap items-center justify-between gap-2">
				<p className="text-sm text-muted-foreground">
					{t("profile.notifications.push.enabled")}
				</p>
				<Button
					variant="outline"
					size="sm"
					disabled={busy}
					onClick={() => void disable()}
				>
					{t("profile.notifications.push.disable")}
				</Button>
			</div>
		);
	} else if (permission === "denied") {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("profile.notifications.push.denied")}
			</p>
		);
	} else {
		body = (
			<Button disabled={busy} onClick={() => void enable()}>
				{t("profile.notifications.push.enable")}
			</Button>
		);
	}

	return (
		<div className="space-y-3 rounded-md border border-border p-4">
			<h3 className="text-sm font-medium">
				{t("profile.notifications.push.title")}
			</h3>
			{body}
			{failed && (
				<p className="text-sm text-destructive">
					{t("profile.notifications.push.failed")}
				</p>
			)}
			{channels.push_device_count > 0 && (
				<p className="text-xs text-muted-foreground">
					{t("profile.notifications.push.device_count", {
						count: channels.push_device_count,
					})}
				</p>
			)}
		</div>
	);
}

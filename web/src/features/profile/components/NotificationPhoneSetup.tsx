import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { NotificationChannels } from "../api/services";
import { useNotificationPhoneMutation } from "../hooks/useNotificationChannels";

interface NotificationPhoneSetupProps {
	channels: NotificationChannels;
}

/** Add, confirm (with a texted code), change or remove the phone texts go to. */
export function NotificationPhoneSetup({
	channels,
}: NotificationPhoneSetupProps) {
	const { t } = useTranslation();
	const phone = useNotificationPhoneMutation();
	const [editing, setEditing] = useState(false);
	const [number, setNumber] = useState(channels.phone_number ?? "");
	const [code, setCode] = useState("");

	const sendCode = async (phoneNumber: string) => {
		try {
			await phone.mutateAsync({ action: "start", phoneNumber });
			setEditing(false);
			setCode("");
		} catch {
			// The server's message is shown as a toast.
		}
	};

	const verify = async () => {
		try {
			await phone.mutateAsync({ action: "verify", code });
		} catch {
			setCode("");
		}
	};

	const showNumberForm =
		editing ||
		!channels.phone_number ||
		(!channels.phone_verified && !channels.phone_verification_pending);

	return (
		<div className="space-y-3 rounded-md border border-border p-4">
			<h3 className="text-sm font-medium">
				{t("profile.notifications.phone.title")}
			</h3>

			{showNumberForm ? (
				<form
					className="flex flex-wrap items-end gap-2"
					onSubmit={(event) => {
						event.preventDefault();
						void sendCode(number.trim());
					}}
				>
					<div className="min-w-48 flex-1 space-y-1">
						<Label htmlFor="notification-phone">
							{t("profile.notifications.phone.label")}
						</Label>
						<Input
							id="notification-phone"
							type="tel"
							autoComplete="tel"
							inputMode="tel"
							placeholder={t("profile.notifications.phone.placeholder")}
							value={number}
							onChange={(event) => setNumber(event.target.value)}
						/>
					</div>
					<Button type="submit" disabled={phone.isPending || !number.trim()}>
						{t("profile.notifications.phone.send_code")}
					</Button>
					{editing && channels.phone_number && (
						<Button
							type="button"
							variant="ghost"
							onClick={() => setEditing(false)}
						>
							{t("common.cancel")}
						</Button>
					)}
				</form>
			) : channels.phone_verified ? (
				<div className="flex flex-wrap items-center justify-between gap-2">
					<p className="text-sm text-muted-foreground">
						{t("profile.notifications.phone.verified", {
							phone: channels.phone_number,
						})}
					</p>
					<div className="flex gap-2">
						<Button
							variant="outline"
							size="sm"
							onClick={() => setEditing(true)}
						>
							{t("profile.notifications.phone.change")}
						</Button>
						<Button
							variant="outline"
							size="sm"
							disabled={phone.isPending}
							onClick={() => phone.mutate({ action: "remove" })}
						>
							{t("profile.notifications.phone.remove")}
						</Button>
					</div>
				</div>
			) : (
				<form
					className="space-y-2"
					onSubmit={(event) => {
						event.preventDefault();
						void verify();
					}}
				>
					<Label htmlFor="notification-phone-code">
						{t("profile.notifications.phone.code_sent", {
							phone: channels.phone_number,
						})}
					</Label>
					<div className="flex flex-wrap gap-2">
						<Input
							id="notification-phone-code"
							className="w-32"
							inputMode="numeric"
							autoComplete="one-time-code"
							maxLength={6}
							aria-label={t("profile.notifications.phone.code_label")}
							value={code}
							onChange={(event) =>
								setCode(event.target.value.replace(/\D/g, ""))
							}
						/>
						<Button
							type="submit"
							disabled={phone.isPending || code.length !== 6}
						>
							{t("profile.notifications.phone.confirm")}
						</Button>
					</div>
					<div className="flex flex-wrap gap-2">
						<Button
							type="button"
							variant="link"
							size="sm"
							className="px-0"
							disabled={phone.isPending}
							onClick={() => void sendCode(channels.phone_number ?? "")}
						>
							{t("profile.notifications.phone.resend")}
						</Button>
						<Button
							type="button"
							variant="link"
							size="sm"
							className="px-0"
							onClick={() => setEditing(true)}
						>
							{t("profile.notifications.phone.use_different")}
						</Button>
					</div>
				</form>
			)}
		</div>
	);
}

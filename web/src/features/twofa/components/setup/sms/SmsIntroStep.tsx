import { Input } from "@/components/ui/input";
import { GenericIntroStep } from "../generic";

interface SmsIntroStepProps {
	phone: string;
	onPhoneChange: (value: string) => void;
	isSending: boolean;
	errorMessage?: string;
	onSend: () => void;
	onCancel?: () => void;
}

export function SmsIntroStep(props: SmsIntroStepProps) {
	return (
		<GenericIntroStep
			config={{
				title: "Verify by SMS",
				description:
					"Receive a verification code via text message. Use E.164 format (e.g. +15551234567).",
				customContent: (
					<div className="space-y-2 text-left">
						<label
							className="text-sm font-medium text-gray-700"
							htmlFor="sms-phone"
						>
							Phone number
						</label>
						<Input
							id="sms-phone"
							value={props.phone}
							onChange={(event) => props.onPhoneChange(event.target.value)}
							placeholder="+15551234567"
							disabled={props.isSending}
						/>
					</div>
				),
				infoPanelTitle: "How it works",
				infoPanelItems: [
					"We send a 6-digit code via SMS.",
					"Enter the code to enable SMS-based 2FA.",
					"The SMS method becomes your default 2FA option.",
				],
				actionText: "Send Verification Code",
				loadingText: "Sending...",
			}}
			isLoading={props.isSending}
			errorMessage={props.errorMessage}
			onAction={props.onSend}
			onCancel={props.onCancel}
		/>
	);
}

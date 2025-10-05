import { StatusMessage } from "@/components";
import type { TwoFactorMethod } from "@/features/twofa/types";
import { GenericMethodCard } from "./GenericMethodCard";

interface SmsMethodCardProps {
	isCurrent: boolean;
	configured: boolean;
	phoneNumber?: string;
	removalInProgress: boolean;
	methodToRemove: TwoFactorMethod | null;
	onSetup: () => void;
	onRequestRemoval: () => void;
	onSetAsDefault?: () => void;
	setAsDefaultInProgress?: boolean;
}

export function SmsMethodCard(props: SmsMethodCardProps) {
	return (
		<GenericMethodCard
			config={{
				icon: "💬",
				title: "SMS Verification",
				description: "Receive verification codes via text message.",
				chips: [
					{ label: "Quick", variant: "primary" },
					{
						label: "Requires Phone Number",
						className: "bg-orange-100 text-orange-800",
					},
				],
				methodId: "sms",
			}}
			isCurrent={props.isCurrent}
			configured={props.configured}
			additionalInfo={
				props.configured && props.phoneNumber ? (
					<StatusMessage variant="info" className="text-xs">
						Currently sending to {props.phoneNumber}
					</StatusMessage>
				) : undefined
			}
			removalInProgress={props.removalInProgress}
			methodToRemove={props.methodToRemove}
			onSetup={props.onSetup}
			onRequestRemoval={props.onRequestRemoval}
			onSetAsDefault={props.onSetAsDefault}
			setAsDefaultInProgress={props.setAsDefaultInProgress}
		/>
	);
}

import type { TwoFactorMethod } from "@/features/twofa/types";
import { GenericMethodCard } from "./GenericMethodCard";

interface TotpMethodCardProps {
	isCurrent: boolean;
	configured: boolean;
	removalInProgress: boolean;
	methodToRemove: TwoFactorMethod | null;
	onSetup: () => void;
	onRequestRemoval: () => void;
	onSetAsDefault?: () => void;
	setAsDefaultInProgress?: boolean;
}

export function TotpMethodCard(props: TotpMethodCardProps) {
	return (
		<GenericMethodCard
			config={{
				icon: "📱",
				title: "Authenticator App (Recommended)",
				description:
					"Use Google Authenticator, Authy, 1Password, or similar apps to generate verification codes.",
				chips: [
					{ label: "Most Secure", variant: "success" },
					{ label: "Works Offline", variant: "primary" },
					{ label: "No Costs", variant: "info" },
				],
				methodId: "totp",
			}}
			isCurrent={props.isCurrent}
			configured={props.configured}
			removalInProgress={props.removalInProgress}
			methodToRemove={props.methodToRemove}
			onSetup={props.onSetup}
			onRequestRemoval={props.onRequestRemoval}
			onSetAsDefault={props.onSetAsDefault}
			setAsDefaultInProgress={props.setAsDefaultInProgress}
		/>
	);
}

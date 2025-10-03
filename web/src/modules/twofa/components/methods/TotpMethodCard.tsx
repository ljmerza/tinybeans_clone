import type { TwoFactorMethod } from "@/modules/twofa/types";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
	Chip,
	ChipGroup,
	StatusMessage,
	ButtonGroup,
} from "@/components";
import { Button } from "@/components/ui/button";

interface TotpMethodCardProps {
	isCurrent: boolean;
	configured: boolean;
	removalInProgress: boolean;
	methodToRemove: TwoFactorMethod | null;
	onSetup: () => void;
	onRequestRemoval: () => void;
}

export function TotpMethodCard({
	isCurrent,
	configured,
	removalInProgress,
	methodToRemove,
	onSetup,
	onRequestRemoval,
}: TotpMethodCardProps) {
	return (
		<Card className="border-2 border-gray-200">
			<CardHeader className="flex items-start gap-4 pb-0">
				<div className="text-3xl">📱</div>
				<div className="flex-1 space-y-2">
					<CardTitle>Authenticator App (Recommended)</CardTitle>
					<CardDescription>
						Use Google Authenticator, Authy, 1Password, or similar apps to
						generate verification codes.
					</CardDescription>
					<ChipGroup className="mb-1">
						<Chip variant="success">Most Secure</Chip>
						<Chip variant="primary">Works Offline</Chip>
						<Chip variant="info">No Costs</Chip>
					</ChipGroup>
					{isCurrent && (
						<StatusMessage variant="success" className="text-xs">
							Current default method
						</StatusMessage>
					)}
				</div>
			</CardHeader>
			<CardContent className="pt-4">
				<ButtonGroup>
					{configured ? (
						<Button
							variant="outline"
							onClick={onRequestRemoval}
							disabled={removalInProgress}
							className="border-red-200 text-red-600 hover:bg-red-50"
						>
							{removalInProgress && methodToRemove === "totp"
								? "Removing..."
								: "Remove"}
						</Button>
					) : (
						<Button
							onClick={onSetup}
							className="bg-blue-600 hover:bg-blue-700 text-white"
						>
							Setup
						</Button>
					)}
				</ButtonGroup>
			</CardContent>
		</Card>
	);
}

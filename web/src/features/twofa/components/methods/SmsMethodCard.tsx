import type { TwoFactorMethod } from "@/features/twofa/types";
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

export function SmsMethodCard({
	isCurrent,
	configured,
	phoneNumber,
	removalInProgress,
	methodToRemove,
	onSetup,
	onRequestRemoval,
	onSetAsDefault,
	setAsDefaultInProgress = false,
}: SmsMethodCardProps) {
	return (
		<Card className="border-2 border-gray-200">
			<CardHeader className="flex items-start gap-4 pb-0">
				<div className="text-3xl">💬</div>
				<div className="flex-1 space-y-2">
					<CardTitle>SMS Verification</CardTitle>
					<CardDescription>
						Receive verification codes via text message.
					</CardDescription>
					<ChipGroup className="mb-1">
						<Chip variant="primary">Quick</Chip>
						<Chip className="bg-orange-100 text-orange-800">
							Requires Phone Number
						</Chip>
					</ChipGroup>
					{isCurrent && (
						<StatusMessage variant="success" className="text-xs">
							Current default method
						</StatusMessage>
					)}
					{configured && phoneNumber && (
						<StatusMessage variant="info" className="text-xs">
							Currently sending to {phoneNumber}
						</StatusMessage>
					)}
				</div>
			</CardHeader>
			<CardContent className="pt-4">
				<ButtonGroup>
					{configured ? (
						<>
							{!isCurrent && onSetAsDefault && (
								<Button
									onClick={onSetAsDefault}
									disabled={setAsDefaultInProgress}
									className="bg-green-600 hover:bg-green-700 text-white"
								>
									{setAsDefaultInProgress ? "Setting..." : "Set as Default"}
								</Button>
							)}
							<Button
								variant="outline"
								onClick={onRequestRemoval}
								disabled={removalInProgress}
								className="border-red-200 text-red-600 hover:bg-red-50"
							>
								{removalInProgress && methodToRemove === "sms"
									? "Removing..."
									: "Remove"}
							</Button>
						</>
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

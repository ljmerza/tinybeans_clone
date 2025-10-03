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

interface EmailMethodCardProps {
	isCurrent: boolean;
	configured: boolean;
	onSetup: () => void;
	onSetAsDefault?: () => void;
	setAsDefaultInProgress?: boolean;
	onRequestRemoval?: () => void;
	removalInProgress?: boolean;
	methodToRemove?: TwoFactorMethod | null;
}

export function EmailMethodCard({
	isCurrent,
	configured,
	onSetup,
	onSetAsDefault,
	setAsDefaultInProgress = false,
	onRequestRemoval,
	removalInProgress = false,
	methodToRemove = null,
}: EmailMethodCardProps) {
	return (
		<Card className="border-2 border-gray-200">
			<CardHeader className="flex items-start gap-4 pb-0">
				<div className="text-3xl">📧</div>
				<div className="flex-1 space-y-2">
					<CardTitle>Email Verification</CardTitle>
					<CardDescription>
						Receive verification codes via email.
					</CardDescription>
					<ChipGroup className="mb-1">
						<Chip variant="primary">Simple</Chip>
						<Chip variant="info">No Extra App Needed</Chip>
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
							{onRequestRemoval && (
								<Button
									variant="outline"
									onClick={onRequestRemoval}
									disabled={removalInProgress}
									className="border-red-200 text-red-600 hover:bg-red-50"
								>
									{removalInProgress && methodToRemove === "email"
										? "Removing..."
										: "Remove"}
								</Button>
							)}
							{!onRequestRemoval && (
								<StatusMessage variant="success" className="text-sm">
									✓ Configured
								</StatusMessage>
							)}
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

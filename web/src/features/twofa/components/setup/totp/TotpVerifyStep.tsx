import { StatusMessage, WizardFooter, WizardSection } from "@/components";
import { Button } from "@/components/ui/button";
import { verificationCodeSchema } from "@/lib/validations";
import { VerificationInput } from "../../VerificationInput";

interface TotpVerifyStepProps {
	code: string;
	isVerifying: boolean;
	errorMessage?: string;
	onCodeChange: (value: string) => void;
	onVerify: (value?: string) => void;
	onBack: () => void;
}

export function TotpVerifyStep({
	code,
	isVerifying,
	errorMessage,
	onCodeChange,
	onVerify,
	onBack,
}: TotpVerifyStepProps) {
	return (
		<>
			<WizardSection
				title="Verify Setup"
				description="Enter the 6-digit code from your authenticator app."
			>
				<VerificationInput
					value={code}
					onChange={onCodeChange}
					onComplete={(val) => onVerify(val)}
					disabled={isVerifying}
				/>
				{errorMessage && (
					<StatusMessage variant="error" align="center">
						{errorMessage}
					</StatusMessage>
				)}
			</WizardSection>
			<WizardFooter align="between">
				<Button
					variant="ghost"
					onClick={onBack}
					disabled={isVerifying}
					className="flex-1 sm:flex-none"
				>
					Back to QR Code
				</Button>
				<Button
					onClick={() => onVerify()}
					disabled={
						!verificationCodeSchema.safeParse(code).success || isVerifying
					}
					className="flex-1 sm:flex-none"
				>
					{isVerifying ? "Verifying..." : "Verify & Enable 2FA"}
				</Button>
			</WizardFooter>
		</>
	);
}

import { GenericVerifyStep } from "../generic";

interface SmsVerifyStepProps {
code: string;
message: string;
isVerifying: boolean;
isResending: boolean;
errorMessage?: string;
onCodeChange: (value: string) => void;
onVerify: (value?: string) => void;
onResend: () => void;
onCancel?: () => void;
}

export function SmsVerifyStep(props: SmsVerifyStepProps) {
return (
<GenericVerifyStep
config={{
title: "Enter SMS Code",
verifyButtonText: "Verify & Enable SMS",
loadingText: "Verifying...",
showResend: true,
resendButtonText: "Resend Code",
}}
code={props.code}
message={props.message}
isVerifying={props.isVerifying}
isResending={props.isResending}
errorMessage={props.errorMessage}
onCodeChange={props.onCodeChange}
onVerify={props.onVerify}
onResend={props.onResend}
onSecondaryAction={props.onCancel}
/>
);
}

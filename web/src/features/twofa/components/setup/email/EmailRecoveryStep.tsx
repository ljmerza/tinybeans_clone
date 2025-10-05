import { GenericRecoveryStep } from "../generic";

interface EmailRecoveryStepProps {
recoveryCodes?: string[];
onComplete: () => void;
}

export function EmailRecoveryStep(props: EmailRecoveryStepProps) {
return (
<GenericRecoveryStep
config={{
title: "✅ Email 2FA Enabled",
description: "Save your recovery codes to keep access if you can't reach your email.",
}}
recoveryCodes={props.recoveryCodes}
onComplete={props.onComplete}
/>
);
}

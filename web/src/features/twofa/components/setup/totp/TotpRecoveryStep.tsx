import { InfoPanel } from "@/components";
import { GenericRecoveryStep } from "../generic";

interface TotpRecoveryStepProps {
recoveryCodes?: string[];
onComplete: () => void;
}

export function TotpRecoveryStep(props: TotpRecoveryStepProps) {
return (
<GenericRecoveryStep
config={{
title: "✅ 2FA Enabled!",
description: "Save your recovery codes to regain access if you lose your device.",
additionalContent: (
<InfoPanel variant="success" className="text-center">
<p className="font-semibold">
✓ Two-factor authentication is now active
</p>
</InfoPanel>
),
}}
recoveryCodes={props.recoveryCodes}
onComplete={props.onComplete}
/>
);
}

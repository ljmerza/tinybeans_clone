import type { TwoFactorMethod } from "@/features/twofa/types";
import { GenericMethodCard } from "./GenericMethodCard";

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

export function EmailMethodCard(props: EmailMethodCardProps) {
return (
<GenericMethodCard
config={{
icon: "📧",
title: "Email Verification",
description: "Receive verification codes via email.",
chips: [
{ label: "Simple", variant: "primary" },
{ label: "No Extra App Needed", variant: "info" },
],
methodId: "email",
}}
isCurrent={props.isCurrent}
configured={props.configured}
removalInProgress={props.removalInProgress ?? false}
methodToRemove={props.methodToRemove ?? null}
onSetup={props.onSetup}
onRequestRemoval={props.onRequestRemoval ?? (() => {})}
onSetAsDefault={props.onSetAsDefault}
setAsDefaultInProgress={props.setAsDefaultInProgress}
showRemoval={!!props.onRequestRemoval}
/>
);
}

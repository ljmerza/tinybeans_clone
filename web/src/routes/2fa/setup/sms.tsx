import { Layout } from "@/components";
import { SmsSetup } from "@/modules/twofa/components/SmsSetup";
import { use2FAStatus } from "@/modules/twofa/hooks";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function SmsSetupRoute() {
    const navigate = useNavigate();
    const { data: status } = use2FAStatus();

    return (
        <Layout>
            <div className="max-w-2xl mx-auto">
                <SmsSetup
                    defaultPhone={status?.phone_number ?? ""}
                    onComplete={() => navigate({ to: "/2fa/settings" })}
                    onCancel={() => navigate({ to: "/2fa/setup" })}
                />
            </div>
        </Layout>
    );
}

export const Route = createFileRoute("/2fa/setup/sms")({
    component: SmsSetupRoute,
});

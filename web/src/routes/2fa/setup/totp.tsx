import { Layout } from "@/components";
import { TotpSetup } from "@/modules/twofa/components/TotpSetup";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function TotpSetupRoute() {
    const navigate = useNavigate();

    return (
        <Layout>
            <div className="max-w-2xl mx-auto">
                <TotpSetup
                    onComplete={() => navigate({ to: "/2fa/settings" })}
                    onCancel={() => navigate({ to: "/2fa/setup" })}
                />
            </div>
        </Layout>
    );
}

export const Route = createFileRoute("/2fa/setup/totp")({
    component: TotpSetupRoute,
});

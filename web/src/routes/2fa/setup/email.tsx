import { Layout } from "@/components";
import { EmailSetup } from "@/modules/twofa/components/EmailSetup";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

function EmailSetupRoute() {
    const navigate = useNavigate();

    return (
        <Layout>
            <div className="max-w-2xl mx-auto">
                <EmailSetup
                    onComplete={() => navigate({ to: "/2fa/settings" })}
                    onCancel={() => navigate({ to: "/2fa/setup" })}
                />
            </div>
        </Layout>
    );
}

export const Route = createFileRoute("/2fa/setup/email")({
    component: EmailSetupRoute,
});

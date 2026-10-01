import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

type ProfileTabKey = "general" | "notifications" | "2fa";

type ProfileSettingsTabsProps = {
	general: ReactNode;
	notifications?: ReactNode;
	twoFactor?: ReactNode;
};

export function ProfileSettingsTabs({
	general,
	notifications,
	twoFactor,
}: ProfileSettingsTabsProps) {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const pathname = useRouterState({
		select: (state) => state.location.pathname,
	});

	const currentTab: ProfileTabKey = pathname.startsWith("/profile/general")
		? "general"
		: pathname.startsWith("/profile/notifications")
			? "notifications"
			: "2fa";

	const handleTabChange = (value: string) => {
		if (value === currentTab) return;

		if (value === "general") {
			navigate({ to: "/profile/general" });
		} else if (value === "notifications") {
			navigate({ to: "/profile/notifications" });
		} else if (value === "2fa") {
			navigate({ to: "/profile/2fa" });
		}
	};

	return (
		<Tabs
			className="max-w-3xl mx-auto"
			value={currentTab}
			onValueChange={handleTabChange}
		>
			<TabsList className="grid h-auto w-full grid-cols-1 sm:h-9 sm:grid-cols-3">
				<TabsTrigger value="general">
					{t("twofa.settings.tabs.general")}
				</TabsTrigger>
				<TabsTrigger value="notifications">
					{t("twofa.settings.tabs.notifications")}
				</TabsTrigger>
				<TabsTrigger value="2fa">
					{t("twofa.settings.tabs.two_factor")}
				</TabsTrigger>
			</TabsList>

			<TabsContent value="general">{general}</TabsContent>
			<TabsContent value="notifications">{notifications}</TabsContent>
			<TabsContent value="2fa">{twoFactor}</TabsContent>
		</Tabs>
	);
}

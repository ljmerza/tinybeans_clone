import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

type ProfileTabKey = "general" | "2fa";

type ProfileSettingsTabsProps = {
	general: ReactNode;
	twoFactor?: ReactNode;
};

export function ProfileSettingsTabs({
	general,
	twoFactor,
}: ProfileSettingsTabsProps) {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const pathname = useRouterState({
		select: (state) => state.location.pathname,
	});

	const currentTab: ProfileTabKey = pathname.startsWith("/profile/general")
		? "general"
		: "2fa";

	const handleTabChange = (value: string) => {
		if (value === currentTab) return;

		if (value === "general") {
			navigate({ to: "/profile/general" });
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
			<TabsList className="grid w-full grid-cols-2">
				<TabsTrigger value="general">
					{t("twofa.settings.tabs.general")}
				</TabsTrigger>
				<TabsTrigger value="2fa">
					{t("twofa.settings.tabs.two_factor")}
				</TabsTrigger>
			</TabsList>

			<TabsContent value="general">{general}</TabsContent>
			<TabsContent value="2fa">{twoFactor}</TabsContent>
		</Tabs>
	);
}

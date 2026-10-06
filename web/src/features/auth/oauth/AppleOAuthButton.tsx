import { Button } from "@/components/ui/button";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { useAppleOAuth, useOAuthProviders } from "./appleHooks";

interface AppleOAuthButtonProps {
	mode: "signup" | "login" | "link";
	onSuccess?: () => void;
	className?: string;
	disabled?: boolean;
	redirect?: string;
}

/**
 * Sign in with Apple button (black/white per Apple's guidelines).
 * Renders nothing until the server reports Apple credentials are configured.
 */
export function AppleOAuthButton({
	mode,
	onSuccess,
	className = "",
	disabled = false,
	redirect,
}: AppleOAuthButtonProps) {
	const { t } = useTranslation();
	const { data: providers } = useOAuthProviders();
	const { initiateOAuth, isLoading } = useAppleOAuth();

	if (!providers?.apple) {
		return null;
	}

	const handleClick = () => {
		rememberInviteRedirect(redirect ?? null);
		initiateOAuth();
		onSuccess?.();
	};

	const buttonText = {
		signup: t("auth.oauth.apple_signup"),
		login: t("auth.oauth.apple_signin"),
		link: t("auth.oauth.apple_link"),
	}[mode];

	return (
		<Button
			type="button"
			onClick={handleClick}
			disabled={isLoading || disabled}
			isLoading={isLoading}
			variant="brand-apple"
			className={cn("w-full justify-center font-medium", className)}
			aria-label={buttonText}
		>
			{!isLoading && (
				<svg
					className="h-5 w-5"
					viewBox="0 0 24 24"
					xmlns="http://www.w3.org/2000/svg"
					fill="currentColor"
					aria-hidden="true"
					focusable="false"
				>
					<title>Apple Logo</title>
					<path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
				</svg>
			)}
			<span>{buttonText}</span>
		</Button>
	);
}

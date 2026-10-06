import { Eye, EyeOff } from "lucide-react";
import { type ComponentProps, useState } from "react";
import { useTranslation } from "react-i18next";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * Password field with a button that shows or hides what was typed.
 */
export function PasswordInput({
	className,
	disabled,
	...props
}: Omit<ComponentProps<"input">, "type">) {
	const { t } = useTranslation();
	const [visible, setVisible] = useState(false);
	const Icon = visible ? EyeOff : Eye;

	return (
		<div className="relative">
			<Input
				{...props}
				type={visible ? "text" : "password"}
				disabled={disabled}
				className={cn("pr-10", className)}
			/>
			<button
				type="button"
				onClick={() => setVisible((value) => !value)}
				disabled={disabled}
				aria-label={
					visible
						? t("auth.signup.hide_password")
						: t("auth.signup.show_password")
				}
				aria-pressed={visible}
				className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-md text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"
			>
				<Icon aria-hidden className="size-4" />
			</button>
		</div>
	);
}

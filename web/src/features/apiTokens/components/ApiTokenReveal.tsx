import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export interface ApiTokenRevealProps {
	/** The new token; this dialog is the only place it is ever shown. */
	plaintext: string;
	/** "I've copied it": the only way out. Clear the plaintext here. */
	onDone: () => void;
}

/** Copy with the Clipboard API, falling back to execCommand outside secure contexts. */
async function copyText(text: string): Promise<boolean> {
	if (navigator.clipboard && window.isSecureContext) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch {
			// Fall through to the older way.
		}
	}
	try {
		const textArea = document.createElement("textarea");
		textArea.value = text;
		textArea.style.position = "fixed";
		textArea.style.left = "-999999px";
		textArea.style.top = "-999999px";
		document.body.appendChild(textArea);
		textArea.focus();
		textArea.select();
		const copied = document.execCommand("copy");
		textArea.remove();
		return copied;
	} catch {
		return false;
	}
}

/** A client config that reads the token from the environment, never inline. */
function mcpConfig(origin: string) {
	return JSON.stringify(
		{
			mcpServers: {
				circles: {
					command: "uv",
					args: [
						"run",
						"--directory",
						"/path/to/circles-mcp",
						"--frozen",
						"circles-mcp",
					],
					env: { CIRCLES_URL: origin, CIRCLES_TOKEN: "${CIRCLES_TOKEN}" },
				},
			},
		},
		null,
		2,
	);
}

/**
 * Shows a new API token once. It can't be dismissed by Escape, an outside
 * click or a close button: only "I've copied it" closes it, so the parent can
 * drop the plaintext from memory at that moment. No toast, no download.
 */
export function ApiTokenReveal({ plaintext, onDone }: ApiTokenRevealProps) {
	const { t } = useTranslation();
	const [copied, setCopied] = useState(false);

	const copy = async () => {
		if (await copyText(plaintext)) {
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} else {
			showToast({
				message: t("pages.circles.dashboard.api_tokens.reveal.copy_failed"),
				level: "error",
			});
		}
	};

	return (
		<Dialog open>
			<DialogContent
				className="max-w-lg"
				showCloseButton={false}
				onEscapeKeyDown={(event) => event.preventDefault()}
				onInteractOutside={(event) => event.preventDefault()}
			>
				<DialogHeader>
					<DialogTitle>
						{t("pages.circles.dashboard.api_tokens.reveal.title")}
					</DialogTitle>
					<DialogDescription>
						{t("pages.circles.dashboard.api_tokens.reveal.description")}
					</DialogDescription>
				</DialogHeader>
				<div className="rounded-lg border border-amber-500/30 bg-amber-500/15 p-4 dark:border-amber-500/40">
					<p className="text-sm font-semibold text-amber-800 dark:text-amber-200">
						{t("pages.circles.dashboard.api_tokens.reveal.warning_title")}
					</p>
					<p className="text-sm text-amber-700 dark:text-amber-100">
						{t("pages.circles.dashboard.api_tokens.reveal.warning_body")}
					</p>
				</div>
				<code className="block select-all break-all rounded-md bg-muted/60 p-3 font-mono text-sm dark:bg-muted/20">
					{plaintext}
				</code>
				<Button type="button" variant="outline" onClick={copy}>
					{copied
						? t("pages.circles.dashboard.api_tokens.reveal.copied")
						: t("pages.circles.dashboard.api_tokens.reveal.copy")}
				</Button>
				<details className="text-sm">
					<summary className="cursor-pointer text-muted-foreground">
						{t("pages.circles.dashboard.api_tokens.reveal.mcp_title")}
					</summary>
					<p className="mt-2 text-muted-foreground">
						{t("pages.circles.dashboard.api_tokens.reveal.mcp_hint")}
					</p>
					<pre className="mt-2 overflow-x-auto rounded-md bg-muted/60 p-3 font-mono text-xs dark:bg-muted/20">
						{mcpConfig(window.location.origin)}
					</pre>
				</details>
				<DialogFooter>
					<Button type="button" onClick={onDone}>
						{t("pages.circles.dashboard.api_tokens.reveal.done")}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

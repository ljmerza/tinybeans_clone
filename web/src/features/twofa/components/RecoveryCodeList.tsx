/**
 * Recovery Code List Component
 * Displays recovery codes with copy and download functionality
 */

import { Button } from "@/components/ui/button";
import { showToast } from "@/lib/toast";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { twoFactorApi } from "../api/twoFactorApi";

interface RecoveryCodeListProps {
	codes: string[];
	showDownloadButton?: boolean;
}

export function RecoveryCodeList({
	codes,
	showDownloadButton = true,
}: RecoveryCodeListProps) {
	const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
	const { t } = useTranslation();

	// Fallback copy function for browsers without clipboard API
	const copyToClipboard = async (text: string): Promise<boolean> => {
		// Try modern clipboard API first
		if (navigator.clipboard && window.isSecureContext) {
			try {
				await navigator.clipboard.writeText(text);
				return true;
			} catch (err) {
				console.warn("Clipboard API failed, trying fallback", err);
			}
		}

		// Fallback for older browsers or non-secure contexts
		try {
			const textArea = document.createElement("textarea");
			textArea.value = text;
			textArea.style.position = "fixed";
			textArea.style.left = "-999999px";
			textArea.style.top = "-999999px";
			document.body.appendChild(textArea);
			textArea.focus();
			textArea.select();
			const success = document.execCommand("copy");
			textArea.remove();
			return success;
		} catch (err) {
			showToast({ message: t("twofa.errors.copy"), level: "error" });
			return false;
		}
	};

	const handleCopy = async (code: string, index: number) => {
		const success = await copyToClipboard(code);
		if (success) {
			setCopiedIndex(index);
			setTimeout(() => setCopiedIndex(null), 2000);
		} else {
			showToast({ message: t("twofa.errors.copy_code"), level: "error" });
		}
	};

	const handleCopyAll = async () => {
		const allCodes = codes.join("\n");
		const success = await copyToClipboard(allCodes);
		if (success) {
			setCopiedIndex(-1);
			setTimeout(() => setCopiedIndex(null), 2000);
		} else {
			showToast({ message: t("twofa.errors.copy_codes"), level: "error" });
		}
	};

	const importantItems = t("twofa.setup.recovery.important_items", {
		returnObjects: true,
	}) as string[];

	return (
		<div className="space-y-4">
			<div className="bg-amber-500/15 border border-amber-500/30 dark:border-amber-500/40 rounded-lg p-4 transition-colors">
				<h3 className="text-lg font-semibold text-amber-800 dark:text-amber-200 mb-2">
					{t("twofa.setup.recovery.warning_title")}
				</h3>
				<p className="text-sm text-amber-700 dark:text-amber-100">
					{t("twofa.setup.recovery.warning_body")}
				</p>
			</div>

			<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
				{codes.map((code, index) => (
					<button
						key={code}
						type="button"
						onClick={() => handleCopy(code, index)}
						className="bg-muted/60 hover:bg-muted p-3 rounded text-left font-mono text-sm transition-colors group relative dark:bg-muted/20 dark:hover:bg-muted/30"
					>
						<span className="font-semibold text-muted-foreground mr-2">
							{index + 1}.
						</span>
						<span className="select-all">{code}</span>
						{copiedIndex === index && (
							<span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-emerald-600 dark:text-emerald-300 font-semibold">
								{t("twofa.setup.recovery.copied")}
							</span>
						)}
					</button>
				))}
			</div>

			<div className="flex flex-col sm:flex-row gap-2">
				<Button
					type="button"
					variant="outline"
					onClick={handleCopyAll}
					className="flex-1"
				>
					{copiedIndex === -1
						? t("twofa.setup.recovery.copied_all")
						: t("twofa.setup.recovery.copy_all")}
				</Button>
				{showDownloadButton && (
					<>
						<Button
							type="button"
							variant="outline"
							onClick={() => twoFactorApi.downloadRecoveryCodes(codes, "txt")}
							className="flex-1"
						>
							{t("twofa.setup.recovery.download_txt")}
						</Button>
						<Button
							type="button"
							variant="outline"
							onClick={() => twoFactorApi.downloadRecoveryCodes(codes, "pdf")}
							className="flex-1"
						>
							{t("twofa.setup.recovery.download_pdf")}
						</Button>
					</>
				)}
			</div>

			<div className="bg-destructive/10 border border-destructive/30 dark:border-destructive/40 rounded-lg p-4 transition-colors">
				<h4 className="text-sm font-semibold text-destructive mb-2">
					{t("twofa.setup.recovery.important_title")}
				</h4>
				<ul className="text-sm text-destructive-foreground space-y-1 list-disc list-inside">
					{importantItems.map((item) => (
						<li key={item}>{item}</li>
					))}
				</ul>
			</div>
		</div>
	);
}

/**
 * QR Code Display Component
 * Shows QR code and manual entry secret for TOTP setup
 */

import { useTranslation } from "react-i18next";

interface QRCodeDisplayProps {
	qrCodeImage: string;
	secret: string;
	showManualEntry?: boolean;
}

export function QRCodeDisplay({
	qrCodeImage,
	secret,
	showManualEntry = true,
}: QRCodeDisplayProps) {
	const { t } = useTranslation();
	const appList = t("twofa.setup.totp.apps", {
		returnObjects: true,
	}) as string[];

	return (
		<div className="space-y-4">
			{/* QR Code */}
			<div className="bg-white p-6 rounded-lg border-2 border-gray-200 flex justify-center">
				<img
					src={qrCodeImage}
					alt={t("twofa.setup.totp.qr_alt")}
					className="w-64 h-64"
				/>
			</div>

			{/* Instructions */}
			<div className="text-sm text-gray-600 space-y-2">
				<p className="font-semibold">{t("twofa.setup.totp.scan_prompt")}</p>
				<ul className="list-disc list-inside space-y-1 ml-2">
					{appList.map((app) => (
						<li key={app}>{app}</li>
					))}
				</ul>
			</div>

			{/* Manual Entry */}
			{showManualEntry && (
				<div className="bg-gray-50 p-4 rounded-lg">
					<p className="text-sm font-semibold text-gray-700 mb-2">
						{t("twofa.setup.totp.manual_title")}
					</p>
					<div className="bg-white p-3 rounded border border-gray-300">
						<code className="text-lg font-mono select-all break-all">
							{secret}
						</code>
					</div>
					<p className="text-xs text-gray-500 mt-2">
						{t("twofa.setup.totp.manual_help")}
					</p>
				</div>
			)}
		</div>
	);
}

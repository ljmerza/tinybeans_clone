/**
 * QR Code Display Component
 * Shows QR code and manual entry secret for TOTP setup
 */

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
	return (
		<div className="space-y-4">
			{/* QR Code */}
			<div className="bg-white p-6 rounded-lg border-2 border-gray-200 flex justify-center">
				<img
					src={qrCodeImage}
					alt="QR Code for authenticator app"
					className="w-64 h-64"
				/>
			</div>

			{/* Instructions */}
			<div className="text-sm text-gray-600 space-y-2">
				<p className="font-semibold">
					Scan this QR code with your authenticator app:
				</p>
				<ul className="list-disc list-inside space-y-1 ml-2">
					<li>Google Authenticator</li>
					<li>Authy</li>
					<li>1Password</li>
					<li>Microsoft Authenticator</li>
					<li>Or any TOTP-compatible app</li>
				</ul>
			</div>

			{/* Manual Entry */}
			{showManualEntry && (
				<div className="bg-gray-50 p-4 rounded-lg">
					<p className="text-sm font-semibold text-gray-700 mb-2">
						Can't scan? Enter this code manually:
					</p>
					<div className="bg-white p-3 rounded border border-gray-300">
						<code className="text-lg font-mono select-all break-all">
							{secret}
						</code>
					</div>
					<p className="text-xs text-gray-500 mt-2">
						Use this secret key if your authenticator app doesn't support QR
						codes
					</p>
				</div>
			)}
		</div>
	);
}

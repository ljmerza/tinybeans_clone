import { useMutation } from "@tanstack/react-query";

import { sendReauthCode } from "./api";

/** Sends (or re-sends) the emailed re-authentication code. */
export function useSendReauthCode() {
	return useMutation({
		mutationFn: sendReauthCode,
		// Never pause offline: the step should say at once that sending failed.
		networkMode: "always",
	});
}

import { authStore } from "../store/authStore";
import { EventClient } from "@tanstack/devtools-event-client";
import { useEffect, useState } from "react";

type EventMap = {
	"auth-store:state": {
		accessToken: string | null;
	};
};

class AuthStoreDevtoolsEventClient extends EventClient<EventMap> {
	constructor() {
		super({
			pluginId: "auth-store",
		});
	}
}

const adec = new AuthStoreDevtoolsEventClient();

authStore.subscribe(() => {
	adec.emit("state", {
		accessToken: authStore.state.accessToken,
	});
});

function DevtoolPanel() {
	const [state, setState] = useState<EventMap["auth-store:state"]>(() => ({
		accessToken: authStore.state.accessToken,
	}));

	useEffect(() => {
		return adec.on("state", (e) => setState(e.payload));
	}, []);

	return (
		<div className="p-4 grid gap-4 grid-cols-[1fr_10fr]">
			<div className="text-sm font-bold text-gray-500 whitespace-nowrap">
				Access Token
			</div>
			<div className="text-sm break-all font-mono">
				{state?.accessToken || <span className="text-gray-400">null</span>}
			</div>
		</div>
	);
}

export const AuthDevtools = {
	name: "Auth Store",
	render: <DevtoolPanel />,
};

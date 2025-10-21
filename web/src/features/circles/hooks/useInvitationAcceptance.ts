import { useAuthSession } from "@/features/auth";
import type { CircleInvitationDetails } from "@/features/circles";
import {
	type StoredCircleInvitation,
	clearInvitation,
	clearInvitationRequest,
	hasActiveInvitationRequest,
	loadInvitation,
	markInvitationRequest,
	subscribeInvitationStorage,
} from "@/features/circles/utils/invitationStorage";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import type { ApiError } from "@/types";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	useFinalizeCircleInvitation,
	useRespondToCircleInvitation,
	useStartCircleInvitationOnboarding,
} from "./useCircleInvitationOnboarding";

export type InvitationViewState =
	| "loading"
	| "invalid"
	| "pending"
	| "finalizing"
	| "accepted"
	| "declined"
	| "expired"
	| "error";

export interface NavigateOptions {
	to: string;
	search?: Record<string, string | undefined>;
}

interface UseInvitationAcceptanceParams {
	token?: string;
	currentPath: string;
	navigate: (options: NavigateOptions) => void | Promise<void>;
}

interface UseInvitationAcceptanceResult {
	viewState: InvitationViewState;
	invitationDetails: CircleInvitationDetails | null;
	errorMessage: string | null;
	isLoading: boolean;
	mutations: {
		finalizePending: boolean;
		respondPending: boolean;
	};
	handleAccept: () => void;
	handleDecline: () => void;
}

export function useInvitationAcceptance({
	token,
	currentPath,
	navigate,
}: UseInvitationAcceptanceParams): UseInvitationAcceptanceResult {
	const { t } = useTranslation();
	const session = useAuthSession();

	const startMutation = useStartCircleInvitationOnboarding();
	const finalizeMutation = useFinalizeCircleInvitation();
	const respondMutation = useRespondToCircleInvitation();

	const [storedInvitation, setStoredInvitation] =
		useState<StoredCircleInvitation | null>(() => loadInvitation());
	const [invitationDetails, setInvitationDetails] =
		useState<CircleInvitationDetails | null>(
			() => storedInvitation?.invitation ?? null,
		);
	const onboardingTokenRef = useRef<string | null>(
		storedInvitation?.onboardingToken ?? null,
	);
	const invitationIdRef = useRef<string | null>(
		storedInvitation?.invitation?.id ?? null,
	);
	const previousTokenRef = useRef<string | undefined>(undefined);
	const hasRequestedRef = useRef(false);
	const autoFinalizeRef = useRef(false);
	const redirectAfterAcceptRef = useRef(false);

	const [viewState, setViewState] = useState<InvitationViewState>(() => {
		if (!token && !storedInvitation) return "invalid";
		return storedInvitation ? "pending" : "loading";
	});
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	useEffect(() => {
		if (previousTokenRef.current && previousTokenRef.current !== token) {
			clearInvitationRequest(previousTokenRef.current);
		}
		previousTokenRef.current = token;
		hasRequestedRef.current = false;
		autoFinalizeRef.current = false;
		redirectAfterAcceptRef.current = false;
	}, [token]);

	useEffect(() => {
		const unsubscribe = subscribeInvitationStorage((payload) => {
			setStoredInvitation(payload);
		});
		return unsubscribe;
	}, []);

	useEffect(() => {
		if (
			storedInvitation &&
			token &&
			storedInvitation.sourceToken &&
			storedInvitation.sourceToken !== token
		) {
			clearInvitation();
			clearInvitationRequest(storedInvitation.sourceToken);
			hasRequestedRef.current = false;
			setStoredInvitation(null);
			onboardingTokenRef.current = null;
			invitationIdRef.current = null;
			setInvitationDetails(null);
			setViewState("loading");
			return;
		}

		if (storedInvitation) {
			setInvitationDetails(storedInvitation.invitation);
			onboardingTokenRef.current = storedInvitation.onboardingToken;
			invitationIdRef.current = storedInvitation.invitation.id;
			if (viewState === "loading") {
				setViewState("pending");
			}
			return;
		}

		if (
			viewState === "accepted" ||
			viewState === "declined" ||
			viewState === "finalizing"
		) {
			return;
		}

		if (!token) {
			setViewState("invalid");
			return;
		}

		if (viewState === "expired" || viewState === "error") {
			return;
		}

		if (hasRequestedRef.current || startMutation.isPending) {
			return;
		}

		if (hasActiveInvitationRequest(token)) {
			return;
		}

		markInvitationRequest(token);
		hasRequestedRef.current = true;
		setViewState("loading");
		startMutation.mutate(token, {
			onSuccess: () => {
				clearInvitationRequest(token);
			},
			onError: (error) => {
				clearInvitationRequest(token);
				hasRequestedRef.current = false;
				const apiError = error as ApiError;
				const messageKey =
					apiError.messages?.[0]?.i18n_key ?? apiError.message ?? "";
				const normalizedKey = typeof messageKey === "string" ? messageKey : "";
				if (
					normalizedKey.includes("errors.token_invalid_expired") ||
					normalizedKey.includes("errors.invitation_not_found")
				) {
					setViewState("expired");
				} else {
					setViewState("error");
					setErrorMessage(
						apiError.message ?? t("pages.inviteAccept.invalidMessage"),
					);
				}
			},
		});
	}, [startMutation, storedInvitation, token, t, viewState]);

	useEffect(() => {
		if (viewState === "accepted" || viewState === "declined") return;
		const onboardingToken =
			storedInvitation?.onboardingToken ?? onboardingTokenRef.current;
		if (!onboardingToken) return;
		if (session.status !== "authenticated") return;
		if (autoFinalizeRef.current) return;

		autoFinalizeRef.current = true;
		setViewState("finalizing");
		finalizeMutation.mutate(onboardingToken, {
			onSuccess: () => {
				setViewState("accepted");
			},
			onError: (error) => {
				const apiError = error as ApiError;
				setViewState("error");
				setErrorMessage(
					apiError.message ?? t("pages.inviteAccept.finalizeFailed"),
				);
				autoFinalizeRef.current = false;
			},
		});
	}, [finalizeMutation, session.status, storedInvitation, t, viewState]);

	useEffect(() => {
		if (viewState !== "accepted") return;
		if (redirectAfterAcceptRef.current) return;

		redirectAfterAcceptRef.current = true;
		void navigate({ to: "/" });
	}, [navigate, viewState]);

	const buildRedirectTarget = useCallback(() => {
		let target = currentPath;
		const onboardingToken = onboardingTokenRef.current;
		if (onboardingToken && typeof window !== "undefined") {
			try {
				const url = new URL(target, window.location.origin);
				url.searchParams.set("onboarding", onboardingToken);
				target = `${url.pathname}${url.search}`;
			} catch (error) {
				console.warn(
					"[inviteAccept] Failed to append onboarding token to redirect",
					error,
				);
			}
		}
		return target;
	}, [currentPath]);

	const handleNavigateAuth = useCallback(
		(path: "/login" | "/signup" | "/magic-link-request") => {
			const target = buildRedirectTarget();
			rememberInviteRedirect(target);
			const search: Record<string, string> = { redirect: target };
			if (path === "/signup" && invitationDetails?.email) {
				search.email = invitationDetails.email;
			}
			void navigate({
				to: path,
				search,
			});
		},
		[buildRedirectTarget, invitationDetails?.email, navigate],
	);

	const handleAccept = useCallback(() => {
		if (session.status !== "authenticated") {
			const target = invitationDetails?.existing_user ? "/login" : "/signup";
			handleNavigateAuth(target);
			return;
		}

		const tokenToUse = onboardingTokenRef.current;
		if (!tokenToUse) return;
		setViewState("finalizing");
		autoFinalizeRef.current = true;
		finalizeMutation.mutate(tokenToUse, {
			onSuccess: () => {
				setViewState("accepted");
			},
			onError: (error) => {
				const apiError = error as ApiError;
				setViewState("error");
				setErrorMessage(
					apiError.message ?? t("pages.inviteAccept.finalizeFailed"),
				);
				autoFinalizeRef.current = false;
			},
		});
	}, [
		finalizeMutation,
		handleNavigateAuth,
		invitationDetails?.existing_user,
		session.status,
		t,
	]);

	const handleDecline = useCallback(() => {
		const invitationId = invitationIdRef.current;
		if (!invitationId) return;

		if (session.status !== "authenticated") {
			handleNavigateAuth("/login");
			return;
		}

		respondMutation.mutate(
			{ invitationId, action: "decline" },
			{
				onSuccess: () => {
					setViewState("declined");
				},
				onError: (error) => {
					const apiError = error as ApiError;
					setViewState("error");
					setErrorMessage(
						apiError.message ?? t("pages.inviteAccept.declineFailed"),
					);
				},
			},
		);
	}, [handleNavigateAuth, respondMutation, session.status, t]);

	const isLoading =
		viewState === "loading" ||
		(viewState === "finalizing" && finalizeMutation.isPending);

	return {
		viewState,
		invitationDetails,
		errorMessage,
		isLoading,
		mutations: {
			finalizePending: finalizeMutation.isPending,
			respondPending: respondMutation.isPending,
		},
		handleAccept,
		handleDecline,
	};
}

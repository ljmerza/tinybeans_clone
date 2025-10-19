import { Card, CardContent, CardHeader, CardTitle } from "@/components/Card";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import { Button } from "@/components/ui/button";
import { useAuthSession } from "@/features/auth";
import type { CircleInvitationDetails } from "@/features/circles";
import {
	clearInvitation,
	clearInvitationRequest,
	hasActiveInvitationRequest,
	loadInvitation,
	markInvitationRequest,
	subscribeInvitationStorage,
	type StoredCircleInvitation,
} from "@/features/circles/utils/invitationStorage";
import {
	useFinalizeCircleInvitation,
	useRespondToCircleInvitation,
	useStartCircleInvitationOnboarding,
} from "@/features/circles/hooks/useCircleInvitationOnboarding";
import { rememberInviteRedirect } from "@/features/circles/utils/inviteAnalytics";
import type { ApiError } from "@/types";
import { useLocation } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Route } from "@/routes/invitations.accept";

type InvitationViewState =
	| "loading"
	| "invalid"
	| "pending"
	| "finalizing"
	| "accepted"
	| "declined"
	| "expired"
	| "error";

interface InvitationAcceptContentProps {
	token?: string;
}

export function InvitationAcceptContent({ token }: InvitationAcceptContentProps) {
	const { t } = useTranslation();
	const session = useAuthSession();
	const location = useLocation();
	const navigate = Route.useNavigate();
	const { token: inviteTokenParam } = Route.useSearch();

	const startMutation = useStartCircleInvitationOnboarding();
	const finalizeMutation = useFinalizeCircleInvitation();
	const respondMutation = useRespondToCircleInvitation();

	const [storedInvitation, setStoredInvitation] = useState<StoredCircleInvitation | null>(
		() => loadInvitation(),
	);
	const [invitationDetails, setInvitationDetails] = useState<CircleInvitationDetails | null>(
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
	const [viewState, setViewState] = useState<InvitationViewState>(() => {
		if (!token && !storedInvitation) return "invalid";
		return storedInvitation ? "pending" : "loading";
	});
	const [errorMessage, setErrorMessage] = useState<string | null>(null);
	const autoFinalizeRef = useRef(false);
	const redirectAfterAcceptRef = useRef(false);

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

		if (viewState === "accepted" || viewState === "declined" || viewState === "finalizing") {
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
					setErrorMessage(apiError.message ?? t("pages.inviteAccept.invalidMessage"));
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

	const currentPath = useMemo(() => {
		if (!inviteTokenParam) {
			return location.pathname;
		}
		const query = new URLSearchParams({ token: inviteTokenParam }).toString();
		return `${location.pathname}?${query}`;
	}, [inviteTokenParam, location.pathname]);

	const buildRedirectTarget = useCallback(() => {
		let target = currentPath;
		const onboardingToken = onboardingTokenRef.current;
		if (onboardingToken && typeof window !== "undefined") {
			try {
				const url = new URL(target, window.location.origin);
				url.searchParams.set("onboarding", onboardingToken);
				target = `${url.pathname}${url.search}`;
			} catch (error) {
				console.warn("[inviteAccept] Failed to append onboarding token to redirect", error);
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
			navigate({
				to: path,
				search,
			});
		},
		[buildRedirectTarget, invitationDetails?.email, navigate],
	);

	const handleAccept = () => {
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
	};

	const handleDecline = () => {
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
	};

	useEffect(() => {
		if (viewState !== "accepted") return;
		if (redirectAfterAcceptRef.current) return;

		redirectAfterAcceptRef.current = true;
		navigate({ to: "/" });
	}, [navigate, viewState]);

	const isLoading =
		viewState === "loading" ||
		(viewState === "finalizing" && finalizeMutation.isPending);

	if (viewState === "invalid") {
		return (
			<div className="flex min-h-[60vh] items-center justify-center px-4">
				<StatusMessage variant="error">
					{t("pages.inviteAccept.invalidMessage")}
				</StatusMessage>
			</div>
		);
	}

	const circleName = invitationDetails?.circle?.name ?? "";
	const invitedBy = invitationDetails?.invited_by?.username;

	return (
		<div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col gap-6 py-12">
			<header className="space-y-2 text-center">
				<h1 className="heading-2">
					{circleName
						? t("pages.inviteAccept.title", { circle: circleName })
						: t("pages.inviteAccept.genericTitle")}
				</h1>
				<p className="text-muted-foreground">
					{circleName
						? t("pages.inviteAccept.subtitle", { circle: circleName })
						: t("pages.inviteAccept.genericSubtitle")}
				</p>
			</header>

			{isLoading ? (
				<div className="flex min-h-[30vh] items-center justify-center">
					<LoadingSpinner label={t("pages.inviteAccept.loading") ?? ""} />
				</div>
			) : null}

			{viewState === "expired" ? (
				<StatusMessage variant="warning">
					{t("pages.inviteAccept.expired")}
				</StatusMessage>
			) : null}

			{viewState === "error" && errorMessage ? (
				<StatusMessage variant="error">{errorMessage}</StatusMessage>
			) : null}

			{["pending", "finalizing"].includes(viewState) && invitationDetails ? (
				<Card>
					<CardHeader>
						<CardTitle>
							{t("pages.inviteAccept.invitationHeading", {
								circle: invitationDetails.circle?.name,
							})}
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<p className="text-sm text-muted-foreground">
							{invitedBy
								? t("pages.inviteAccept.invitedBy", { inviter: invitedBy })
								: t("pages.inviteAccept.invitedGeneric")}
						</p>
						<div className="flex flex-wrap gap-3">
							<Button onClick={handleAccept} disabled={finalizeMutation.isPending}>
								{finalizeMutation.isPending
									? t("pages.inviteAccept.accepting")
									: t("pages.inviteAccept.accept")}
							</Button>
							<Button
								variant="outline"
								onClick={handleDecline}
								disabled={respondMutation.isPending}
							>
								{respondMutation.isPending
									? t("pages.inviteAccept.declining")
									: t("pages.inviteAccept.decline")}
							</Button>
						</div>
					</CardContent>
				</Card>
			) : null}

			{viewState === "finalizing" ? (
				<StatusMessage variant="info">
					{t("pages.inviteAccept.finalizing")}
				</StatusMessage>
			) : null}

			{viewState === "accepted" ? (
				<Card className="border-success/40 bg-success/10">
					<CardHeader>
						<CardTitle>{t("pages.inviteAccept.acceptedTitle")}</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3 text-sm text-success-foreground">
						<p>{t("pages.inviteAccept.acceptedMessage", { circle: circleName })}</p>
						<Button
							variant="secondary"
							onClick={() => navigate({ to: "/circles" })}
						>
							{t("pages.inviteAccept.viewCircles")}
						</Button>
					</CardContent>
				</Card>
			) : null}

			{viewState === "declined" ? (
				<StatusMessage variant="info">
					{t("pages.inviteAccept.declinedMessage")}
				</StatusMessage>
			) : null}
		</div>
	);
}

function InvitationAcceptRouteView() {
	const { token } = Route.useSearch();
	return <InvitationAcceptContent token={token} />;
}

export default InvitationAcceptRouteView;

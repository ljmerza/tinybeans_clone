import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  Layout,
  LoadingState,
  EmptyState,
} from "@/components";
import { Button } from "@/components/ui/button";
import { useCircleMemberships, useCircleRemoveSelfMutation } from "@/features/circles";
import { useAuthSession } from "@/features/auth";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export function CirclesIndexRouteView() {
  const { t } = useTranslation();
  const session = useAuthSession();
  const { data, isLoading, error, refetch, isFetching } = useCircleMemberships();
  const [removeTarget, setRemoveTarget] = useState<{ circleId: number; name: string } | null>(null);
  const removeSelfMutation = useCircleRemoveSelfMutation();

  if (isLoading && !data) {
    return (
      <Layout.Loading
        message={t("pages.circles.index.loading")}
        spinnerSize="sm"
      />
    );
  }

  if (error) {
    return (
      <Layout.Error
        title={t("pages.circles.index.error_title")}
        message={t("pages.circles.index.error_message")}
        actionLabel={t("pages.circles.index.retry")}
        onAction={() => refetch()}
      />
    );
  }

  const memberships = data ?? [];

  return (
    <Layout>
      <div className="container-page space-y-6">
        <header className="space-y-2">
          <h1 className="heading-2">{t("pages.circles.index.title")}</h1>
          <p className="text-subtitle">{t("pages.circles.index.subtitle")}</p>
          {isFetching ? (
            <LoadingState
              layout="inline"
              spinnerSize="sm"
              className="text-sm text-muted-foreground"
              message={t("pages.circles.index.refreshing")}
            />
          ) : null}
        </header>

        {memberships.length === 0 ? (
          <EmptyState
            title={t("pages.circles.index.empty_title")}
            description={t("pages.circles.index.empty_description")}
            actions={
              <Button asChild variant="primary">
                <Link to="/circles/onboarding">
                  {t("pages.circles.index.empty_action")}
                </Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {memberships.map((membership) => {
              const isAdmin = membership.role === "admin";
              return (
                <Card key={membership.membership_id}>
                  <CardHeader>
                    <CardTitle>{membership.circle.name}</CardTitle>
                    <CardDescription>
                      {t("pages.circles.index.member_count", {
                        count: membership.circle.member_count,
                      })}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between gap-4">
                    <span className="text-sm text-muted-foreground">
                      {t("pages.circles.index.role_label", {
                        role: t(`pages.circles.invites.roles.${membership.role}`),
                      })}
                    </span>
                    {isAdmin ? (
                      <Button asChild variant="secondary" size="sm">
                        <Link
                          to="/circles/$circleId"
                          params={{ circleId: String(membership.circle.id) }}
                        >
                          {t("pages.circles.index.manage")}
                        </Link>
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!session.user?.id || removeSelfMutation.isPending}
                        onClick={() =>
                          setRemoveTarget({
                            circleId: membership.circle.id,
                            name: membership.circle.name,
                          })
                        }
                      >
                        {t("pages.circles.index.leave")}
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={removeTarget != null}
        title={t("pages.circles.index.leave_confirm_title")}
        description={t("pages.circles.index.leave_confirm_body", {
          circle: removeTarget?.name ?? "",
        })}
        confirmLabel={t("pages.circles.index.leave_confirm_cta")}
        cancelLabel={t("common.cancel")}
        confirmVariant="destructive"
        loading={removeSelfMutation.isPending}
        onOpenChange={(open) => {
          if (!open && !removeSelfMutation.isPending) {
            setRemoveTarget(null);
          }
        }}
        onConfirm={async () => {
          if (!removeTarget) return;
          try {
            await removeSelfMutation.mutateAsync({
              circleId: removeTarget.circleId,
            });
            setRemoveTarget(null);
            void refetch();
          } catch (error) {
            console.error("Failed to leave circle", error);
          }
        }}
      />
    </Layout>
  );
}

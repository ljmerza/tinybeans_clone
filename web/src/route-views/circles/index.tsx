import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Layout,
  LoadingSpinner,
  StatusMessage,
} from "@/components";
import { Button } from "@/components/ui/button";
import { useCircleMemberships } from "@/features/circles";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export function CirclesIndexRouteView() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch, isFetching } = useCircleMemberships();

  if (isLoading && !data) {
    return (
      <Layout.Loading
        message={
          <span className="flex items-center gap-2">
            <LoadingSpinner size="sm" />
            {t("pages.circles.index.loading")}
          </span>
        }
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
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoadingSpinner size="sm" />
              <span>{t("pages.circles.index.refreshing")}</span>
            </div>
          ) : null}
        </header>

        {memberships.length === 0 ? (
          <StatusMessage variant="info">
            {t("pages.circles.index.empty")}
          </StatusMessage>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {memberships.map((membership) => (
              <Card key={membership.membership_id}>
                <CardHeader>
                  <CardTitle>{membership.circle.name}</CardTitle>
                  <CardDescription>
                    {t("pages.circles.index.member_count", {
                      count: membership.circle.member_count,
                    })}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    {t("pages.circles.index.role_label", {
                      role: t(`pages.circles.invites.roles.${membership.role}`),
                    })}
                  </span>
                  <Button asChild variant="secondary" size="sm">
                    <Link
                      to="/circles/$circleId"
                      params={{ circleId: String(membership.circle.id) }}
                    >
                      {t("pages.circles.index.manage")}
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}

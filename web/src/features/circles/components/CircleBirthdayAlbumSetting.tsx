import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { localToday } from "@/features/growth/utils/dates";
import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import {
	useChildBirthdateMutation,
	useCircleBirthdayAlbumSettingMutation,
	useCircleChildren,
} from "../hooks/useCircleBirthdayAlbumSetting";
import type { CircleChild } from "../types";

interface CircleBirthdayAlbumSettingProps {
	circleId: number | string;
	enabled: boolean;
}

/**
 * The Birthdays album switch on a circle's settings page. While it is on, it
 * lists the circle's children so admins can fill in missing birthdates, since
 * the album is built from them. Only render it for circle admins.
 */
export function CircleBirthdayAlbumSetting({
	circleId,
	enabled,
}: CircleBirthdayAlbumSettingProps) {
	const { t } = useTranslation();
	const save = useCircleBirthdayAlbumSettingMutation(circleId);
	// Show the requested state while it saves, so the switch doesn't jump back.
	const checked = save.isPending ? save.variables : enabled;

	return (
		<div className="bg-card text-card-foreground border border-border rounded-lg shadow-md p-6 space-y-4">
			<div className="flex items-center justify-between gap-4">
				<div className="space-y-1">
					<Label htmlFor="circle-birthday-album">
						{t("pages.circles.dashboard.birthdays.title")}
					</Label>
					<p className="text-sm text-muted-foreground">
						{t("pages.circles.dashboard.birthdays.description")}
					</p>
				</div>
				<Switch
					id="circle-birthday-album"
					checked={checked}
					disabled={save.isPending}
					onCheckedChange={(next) => save.mutate(next)}
				/>
			</div>
			{checked && <ChildBirthdates circleId={circleId} />}
		</div>
	);
}

function ChildBirthdates({ circleId }: { circleId: number | string }) {
	const { t } = useTranslation();
	const children = useCircleChildren(circleId);

	let body: ReactNode;
	if (children.isPending) {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("pages.circles.dashboard.birthdays.loading")}
			</p>
		);
	} else if (children.isError) {
		body = (
			<p className="text-sm text-destructive">
				{t("pages.circles.dashboard.birthdays.load_failed")}
			</p>
		);
	} else if (children.data.length === 0) {
		body = (
			<p className="text-sm text-muted-foreground">
				{t("pages.circles.dashboard.birthdays.no_children")}
			</p>
		);
	} else {
		body = (
			<ul className="space-y-3">
				{children.data.map((child) => (
					<ChildBirthdateRow key={child.id} circleId={circleId} child={child} />
				))}
			</ul>
		);
	}

	return (
		<div className="space-y-3 border-t border-border pt-4">
			<div className="space-y-1">
				<h3 className="text-sm font-medium leading-none">
					{t("pages.circles.dashboard.birthdays.children_title")}
				</h3>
				<p className="text-sm text-muted-foreground">
					{t("pages.circles.dashboard.birthdays.children_hint")}
				</p>
			</div>
			{body}
		</div>
	);
}

function ChildBirthdateRow({
	circleId,
	child,
}: {
	circleId: number | string;
	child: CircleChild;
}) {
	const { t } = useTranslation();
	const save = useChildBirthdateMutation(circleId);
	const [draft, setDraft] = useState(child.birthdate ?? "");
	const saved = child.birthdate ?? "";
	const inputId = `child-birthdate-${child.id}`;

	return (
		<li className="space-y-1">
			<form
				className="flex flex-wrap items-center gap-3"
				onSubmit={(event) => {
					event.preventDefault();
					save.mutate({ childId: child.id, birthdate: draft || null });
				}}
			>
				<Label htmlFor={inputId} className="min-w-24">
					{child.display_name}
				</Label>
				<Input
					id={inputId}
					type="date"
					className="w-44"
					aria-label={t("pages.circles.dashboard.birthdays.birthdate_label", {
						name: child.display_name,
					})}
					value={draft}
					max={localToday()}
					disabled={save.isPending}
					onChange={(event) => setDraft(event.target.value)}
				/>
				<Button
					type="submit"
					size="sm"
					variant="outline"
					disabled={save.isPending || draft === saved}
				>
					{save.isPending
						? t("pages.circles.dashboard.birthdays.saving")
						: t("pages.circles.dashboard.birthdays.save")}
				</Button>
			</form>
			{!child.birthdate && (
				<p className="text-sm text-amber-700 dark:text-amber-400">
					{t("pages.circles.dashboard.birthdays.missing")}
				</p>
			)}
		</li>
	);
}

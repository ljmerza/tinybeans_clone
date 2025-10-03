import { cloneElement, type ReactElement } from "react";
import type { ReactNode } from "react";
import { ButtonGroup } from "./ButtonGroup";
import {
	Card,
	CardContent,
	CardFooter,
	CardHeader,
	CardTitle,
	CardDescription,
} from "./Card";

export interface WizardStepProps<TStep extends string = string> {
	step: TStep;
	children: ReactNode;
	footer?: ReactNode;
}

export function WizardStep<TStep extends string>({
	children,
}: WizardStepProps<TStep>) {
	return <>{children}</>;
}

interface WizardProps<TStep extends string> {
	currentStep: TStep;
	children: ReactNode;
	className?: string;
}

export function Wizard<TStep extends string>({
	currentStep,
	children,
	className,
}: WizardProps<TStep>) {
	const steps = Array.isArray(children) ? children : [children];
	const active = steps.find((child) => {
		if (!child || typeof child !== "object") return false;
		const element = child as ReactElement<WizardStepProps<TStep>>;
		return element.props.step === currentStep;
	});

	if (!active) {
		return null;
	}

	const { footer } = (active as ReactElement<WizardStepProps<TStep>>).props;
	const content = cloneElement(active as ReactElement<WizardStepProps<TStep>>);

	return (
		<Card className={className}>
			{content}
			{footer}
		</Card>
	);
}

interface WizardSectionProps {
	title: ReactNode;
	description?: ReactNode;
	children: ReactNode;
}

export function WizardSection({
	title,
	description,
	children,
}: WizardSectionProps) {
	return (
		<>
			<CardHeader className="text-center">
				<CardTitle>{title}</CardTitle>
				{description ? <CardDescription>{description}</CardDescription> : null}
			</CardHeader>
			<CardContent className="space-y-4">{children}</CardContent>
		</>
	);
}

interface WizardFooterProps {
	children: ReactNode;
	align?: "start" | "center" | "end" | "between" | "around";
}

export function WizardFooter({ children, align = "end" }: WizardFooterProps) {
	return (
		<CardFooter>
			<ButtonGroup align={align}>{children}</ButtonGroup>
		</CardFooter>
	);
}

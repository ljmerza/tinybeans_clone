import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";
import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import type { ComponentPropsWithoutRef, ComponentPropsWithRef } from "react";
import * as React from "react";

const buttonVariants = cva(
	"inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:border-ring aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
	{
		variants: {
			variant: {
				primary:
					"bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-primary/40",
				default:
					"bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-primary/40",
				secondary:
					"bg-secondary text-secondary-foreground hover:bg-secondary/80 focus-visible:ring-secondary/40",
				ghost:
					"text-foreground hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50",
				outline:
					"border border-border bg-background shadow-xs hover:bg-accent/60 hover:text-accent-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50",
				destructive:
					"bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive/30 dark:focus-visible:ring-destructive/40",
				link: "text-primary underline-offset-4 hover:underline focus-visible:ring-0 focus-visible:border-transparent px-0 h-auto",
				success:
					"bg-emerald-500 text-white hover:bg-emerald-600 focus-visible:ring-emerald-400/40",
				"brand-google":
					"border border-[#dadce0] bg-white text-neutral-700 shadow-sm hover:bg-neutral-50 hover:shadow focus-visible:ring-[#4285F4]/40 dark:border-[#3c4043] dark:bg-[#1f1f1f] dark:text-white dark:hover:bg-[#2a2a2a]",
			},
			size: {
				default: "h-9 px-4 py-2 has-[>svg]:px-3",
				sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
				lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
				icon: "size-9",
			},
		},
		defaultVariants: {
			variant: "primary",
			size: "default",
		},
	},
);

type ButtonProps = ComponentPropsWithoutRef<"button"> &
	VariantProps<typeof buttonVariants> & {
		asChild?: boolean;
		isLoading?: boolean;
		iconPosition?: "left" | "right";
	};

type SlotElementRef = ComponentPropsWithRef<typeof Slot>["ref"];

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	(
		{
			className,
			variant,
			size,
			asChild = false,
			isLoading = false,
			iconPosition = "left",
			disabled,
			children,
			tabIndex,
			type = "button",
			...rest
		},
		ref,
	) => {
		const isDisabled = Boolean(disabled) || isLoading;
		const spinner = isLoading ? (
			<LoadingSpinner
				size="sm"
				className="text-current [&>div]:border-2 [&>div]:border-border/60 [&>div]:border-t-current"
				aria-hidden
			/>
		) : null;
		const baseClassName = cn(
			buttonVariants({ variant, size }),
			iconPosition === "right" && "flex-row-reverse",
			isLoading && "cursor-progress",
			className,
		);

		if (asChild) {
				if (!React.isValidElement(children)) {
					if (process.env.NODE_ENV !== "production") {
						console.error(
							"Button with `asChild` expects a single React element child.",
						);
				}

				return (
					<button
						ref={ref}
						type={type}
						data-slot="button"
						data-icon-position={iconPosition}
						data-loading={isLoading ? "" : undefined}
						className={baseClassName}
						aria-busy={isLoading || undefined}
						aria-live={isLoading ? "polite" : undefined}
						disabled={isDisabled}
						data-disabled={isDisabled ? "" : undefined}
						tabIndex={isDisabled ? -1 : tabIndex}
						{...rest}
					>
						{spinner}
						{children}
					</button>
				);
			}

				const child = React.Children.only(children) as React.ReactElement;
				const childChildren = child.props?.children;
				const mergedChildren = isLoading ? (
					<>
						{spinner}
						{childChildren}
					</>
				) : (
					childChildren
				);
				const childTabIndex =
					(child.props as { tabIndex?: number }).tabIndex ?? undefined;

				return (
					<Slot
						ref={ref as SlotElementRef}
						data-slot="button"
						data-icon-position={iconPosition}
						data-loading={isLoading ? "" : undefined}
					className={baseClassName}
					aria-busy={isLoading || undefined}
					aria-live={isLoading ? "polite" : undefined}
						data-disabled={isDisabled ? "" : undefined}
						aria-disabled={isDisabled || undefined}
						tabIndex={
							isDisabled
								? -1
								: tabIndex ?? childTabIndex ?? undefined
						}
						{...rest}
					>
						{React.cloneElement(child, {
							children: mergedChildren,
						})}
					</Slot>
				);
			}

		return (
			<button
				ref={ref}
				type={type}
				data-slot="button"
				data-icon-position={iconPosition}
				data-loading={isLoading ? "" : undefined}
				className={baseClassName}
				aria-busy={isLoading || undefined}
				aria-live={isLoading ? "polite" : undefined}
				disabled={isDisabled}
				data-disabled={isDisabled ? "" : undefined}
				tabIndex={tabIndex}
				{...rest}
			>
				{spinner}
				{children}
			</button>
		);
	},
);
Button.displayName = "Button";

export { Button, buttonVariants };

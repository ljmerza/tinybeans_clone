import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type StatusVariant = "info" | "success" | "warning" | "error";

interface StatusMessageProps {
    children: ReactNode;
    variant?: StatusVariant;
    align?: "left" | "center" | "right";
    className?: string;
    role?: "status" | "alert" | "log" | "marquee" | "timer" | "progressbar";
    ariaLive?: "off" | "polite" | "assertive";
}

const variantStyles: Record<StatusVariant, string> = {
    info: "text-blue-600",
    success: "text-green-600",
    warning: "text-yellow-700",
    error: "text-red-600",
};

const alignStyles: Record<NonNullable<StatusMessageProps["align"]>, string> = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
};

export function StatusMessage({
    children,
    variant = "info",
    align = "left",
    className,
    role,
    ariaLive,
}: StatusMessageProps) {
    const resolvedRole = role ?? (variant === "error" ? "alert" : "status");
    const resolvedAriaLive = ariaLive ?? (variant === "error" ? "assertive" : "polite");

    return (
        <p
            role={resolvedRole}
            aria-live={resolvedAriaLive}
            className={cn("text-sm", variantStyles[variant], alignStyles[align], className)}
        >
            {children}
        </p>
    );
}

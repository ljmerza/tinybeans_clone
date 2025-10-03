import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ButtonGroupProps {
    children: ReactNode;
    className?: string;
    align?: "start" | "center" | "end" | "between" | "around";
    wrap?: boolean;
}

const alignmentClasses: Record<Exclude<ButtonGroupProps["align"], undefined>, string> = {
    start: "justify-start",
    center: "justify-center",
    end: "justify-end",
    between: "justify-between",
    around: "justify-around",
};

export function ButtonGroup({ children, className, align = "start", wrap = false }: ButtonGroupProps) {
    return (
        <div
            className={cn(
                "flex gap-2",
                alignmentClasses[align],
                wrap && "flex-wrap",
                className,
            )}
        >
            {children}
        </div>
    );
}

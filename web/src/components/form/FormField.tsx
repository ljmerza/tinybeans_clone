import { Label } from "@radix-ui/react-label";
import type { ReactNode } from "react";

import { FieldError } from "@/components/FieldError";
import { cn } from "@/lib/utils";
import type { FormField as FormFieldApi } from "@/types";

interface FormFieldProps {
	field: FormFieldApi;
	label?: ReactNode;
	helperText?: ReactNode;
	error?: ReactNode;
	id?: string;
	className?: string;
	labelClassName?: string;
	children: (props: { id: string; field: FormFieldApi }) => ReactNode;
}

/**
 * Shared form field wrapper that wires labels, TanStack field errors,
 * optional helper text, and server-side error messages using a consistent layout.
 */
export function FormField({
	field,
	label,
	helperText,
	error,
	id,
	className,
	labelClassName,
	children,
}: FormFieldProps) {
	const inputId = id ?? field.name;

	return (
		<div className={cn("form-group", className)}>
			{label ? (
				<Label htmlFor={inputId} className={cn("form-label", labelClassName)}>
					{label}
				</Label>
			) : null}

			{children({ id: inputId, field })}

			<FieldError field={field} />

			{error ? <p className="form-error">{error}</p> : null}

			{helperText ? <p className="form-help">{helperText}</p> : null}
		</div>
	);
}

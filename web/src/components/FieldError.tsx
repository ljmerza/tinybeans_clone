/**
 * FieldError Component
 *
 * Displays field validation errors from TanStack Form
 * Shows error message only when field is touched and has errors
 */

import type { FormField } from "@/types";

interface FieldErrorProps {
	field: FormField;
}

export function FieldError({ field }: FieldErrorProps) {
	if (!field.state.meta.isTouched || !field.state.meta.errors?.[0]) {
		return null;
	}

	return <p className="form-error">{field.state.meta.errors[0]}</p>;
}

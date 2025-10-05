/**
 * FieldError Component
 *
 * Displays field validation errors from TanStack Form
 * Shows error message only when field is touched and has errors
 */

interface FieldErrorProps {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	field: any;
}

export function FieldError({ field }: FieldErrorProps) {
	if (!field.state.meta.isTouched || !field.state.meta.errors?.[0]) {
		return null;
	}

	return <p className="form-error">{field.state.meta.errors[0]}</p>;
}

/**
 * FieldError Component
 *
 * Displays field validation errors from TanStack Form
 * Shows error message only when field is touched and has errors
 */

import type { FormField } from "@/types";
import { useTranslation } from "react-i18next";

interface FieldErrorProps {
	field: FormField;
}

export function FieldError({ field }: FieldErrorProps) {
	const { t } = useTranslation();
	
	if (!field.state.meta.isTouched || !field.state.meta.errors?.[0]) {
		return null;
	}

	const errorMessage = field.state.meta.errors[0];
	// Translate the error message if it's a translation key
	const translatedMessage = t(errorMessage);

	return <p className="form-error">{translatedMessage}</p>;
}

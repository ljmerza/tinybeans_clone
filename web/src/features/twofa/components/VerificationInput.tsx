/**
 * Verification Input Component
 * 6-digit code input with auto-focus and paste support
 */

import { Input } from "@/components/ui/input";
import {
	type KeyboardEvent,
	useEffect,
	useId,
	useMemo,
	useRef,
	useState,
} from "react";
import { useTranslation } from "react-i18next";

interface VerificationInputProps {
	length?: number;
	value: string;
	onChange: (value: string) => void;
	onComplete?: (value: string) => void;
	autoFocus?: boolean;
	disabled?: boolean;
}

export function VerificationInput({
	length = 6,
	value,
	onChange,
	onComplete,
	autoFocus = true,
	disabled = false,
}: VerificationInputProps) {
	const [digits, setDigits] = useState<string[]>(Array(length).fill(""));
	const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
	const componentId = useId();
	const slotIndices = useMemo(
		() => Array.from({ length }, (_, index) => index),
		[length],
	);
 	const { t } = useTranslation();

	// Sync external value to internal digits
	useEffect(() => {
		const newDigits = value.padEnd(length, "").slice(0, length).split("");
		setDigits(newDigits);
	}, [value, length]);

	useEffect(() => {
		inputRefs.current = inputRefs.current.slice(0, length);
	}, [length]);

	// Auto-focus first input on mount
	useEffect(() => {
		if (autoFocus && inputRefs.current[0] && !disabled) {
			inputRefs.current[0].focus();
		}
	}, [autoFocus, disabled]);

	const handleChange = (index: number, digit: string) => {
		// Only allow digits
		if (digit && !/^\d$/.test(digit)) return;

		const newDigits = [...digits];
		newDigits[index] = digit;

		setDigits(newDigits);
		const newValue = newDigits.join("");
		onChange(newValue);

		// Auto-focus next input
		if (digit && index < length - 1) {
			inputRefs.current[index + 1]?.focus();
		}

		// Call onComplete when all digits entered
		if (newValue.length === length && onComplete) {
			onComplete(newValue);
		}
	};

	const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Backspace") {
			if (!digits[index] && index > 0) {
				// Move to previous input if current is empty
				inputRefs.current[index - 1]?.focus();
			} else {
				// Clear current input
				const newDigits = [...digits];
				newDigits[index] = "";
				setDigits(newDigits);
				onChange(newDigits.join(""));
			}
		} else if (e.key === "ArrowLeft" && index > 0) {
			inputRefs.current[index - 1]?.focus();
		} else if (e.key === "ArrowRight" && index < length - 1) {
			inputRefs.current[index + 1]?.focus();
		}
	};

	const handlePaste = (e: React.ClipboardEvent) => {
		e.preventDefault();
		const pastedData = e.clipboardData
			.getData("text")
			.replace(/\D/g, "")
			.slice(0, length);
		const newDigits = pastedData
			.split("")
			.concat(Array(length).fill(""))
			.slice(0, length);
		setDigits(newDigits);
		onChange(newDigits.join(""));

		// Focus last filled input or first empty
		const nextIndex = Math.min(pastedData.length, length - 1);
		inputRefs.current[nextIndex]?.focus();

		if (pastedData.length === length && onComplete) {
			onComplete(pastedData);
		}
	};

	return (
		<div className="flex gap-2 justify-center" onPaste={handlePaste}>
			{slotIndices.map((index) => (
				<Input
					key={`${componentId}-${index}`}
					ref={(el) => {
						inputRefs.current[index] = el;
					}}
					type="text"
					inputMode="numeric"
					maxLength={1}
					value={digits[index] || ""}
					onChange={(e) => handleChange(index, e.target.value)}
					onKeyDown={(e) => handleKeyDown(index, e)}
					disabled={disabled}
					className="w-12 h-12 text-center text-2xl font-semibold"
					aria-label={t("twofa.verify.digit_label", { index: index + 1 })}
				/>
			))}
		</div>
	);
}

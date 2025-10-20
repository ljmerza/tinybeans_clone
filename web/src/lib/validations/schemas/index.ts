/**
 * Validation Schema Library
 *
 * Import only what you need to keep bundles small:
 *
 * @example
 * // Login page only imports login schema
 * import { loginSchema } from '@/lib/validations/schemas/login'
 *
 * @example
 * // Signup page only imports signup schema
 * import { signupSchema } from '@/lib/validations/schemas/signup'
 *
 * @example
 * // If you need common fields across features
 * import { emailSchema, passwordSchema } from '@/lib/validations/schemas/common'
 */

// Re-export for convenience (but prefer direct imports for better tree-shaking)
export * from "./common";
export * from "./login";
export * from "./signup";
export * from "./magic-link";
export * from "./password-reset";
export * from "./twofa";

export * from "./circle";

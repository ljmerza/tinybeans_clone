import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { confirmPasswordSchema, passwordSchema } from "@/lib/validations";
import { Label } from "@radix-ui/react-label";
import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { z } from "zod";

import { usePasswordResetConfirm } from "../hooks";

type PasswordResetConfirmCardProps = {
  token?: string;
};

const schema = z
	.object({
		password: passwordSchema,
		password_confirm: confirmPasswordSchema,
	})
	.superRefine((values, ctx) => {
		if (values.password !== values.password_confirm) {
			ctx.addIssue({
				code: z.ZodIssueCode.custom,
				message: "Passwords do not match",
				path: ["password_confirm"],
			});
		}
	});

type PasswordResetConfirmValues = z.infer<typeof schema>;

export function PasswordResetConfirmCard({ token }: PasswordResetConfirmCardProps) {
  const confirmReset = usePasswordResetConfirm();
  const navigate = useNavigate();

	const form = useForm({
		defaultValues: {
			password: "",
			password_confirm: "",
		} satisfies PasswordResetConfirmValues,
    onSubmit: async ({ value }) => {
      if (!token) return;
      try {
        await confirmReset.mutateAsync({
          token,
          password: value.password,
          password_confirm: value.password_confirm,
        });
        form.reset();
        navigate({ to: "/login" });
      } catch (error) {
        console.error("Password reset confirm error:", error);
      }
    },
  });

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
          <h1 className="text-2xl font-semibold text-center">Invalid or expired link</h1>
          <p className="text-sm text-muted-foreground text-center">
            We could not find a valid password reset token. Please request a new reset link.
          </p>
          <div className="text-center">
            <Link to="/password/reset/request" className="font-semibold text-blue-600 hover:text-blue-800">
              Request a new link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-6 space-y-4">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-semibold">Set a new password</h1>
          <p className="text-sm text-muted-foreground">
            Choose a new password for your account.
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            form.handleSubmit();
          }}
          className="space-y-4"
        >
          <form.Field
            name="password"
            validators={{
              onBlur: ({ value }) => {
                const result = passwordSchema.safeParse(value);
                return result.success ? undefined : result.error.errors[0].message;
              },
            }}
          >
            {(field) => (
              <div className="form-group">
                <Label htmlFor={field.name}>New password</Label>
                <Input
                  id={field.name}
                  type="password"
                  autoComplete="new-password"
                  value={field.state.value}
                  onChange={(event) => field.handleChange(event.target.value)}
                  onBlur={field.handleBlur}
                  disabled={confirmReset.isPending}
                  required
                />
                {field.state.meta.isTouched && field.state.meta.errors?.[0] && (
                  <p className="form-error">{field.state.meta.errors[0]}</p>
                )}
              </div>
            )}
          </form.Field>

          <form.Field
            name="password_confirm"
            validators={{
              onBlur: ({ value, fieldApi }) => {
                if (value.length < 8) return "Confirm password";
                const password = fieldApi.form.getFieldValue("password");
                if (value !== password) {
                  return "Passwords do not match";
                }
                return undefined;
              },
            }}
          >
            {(field) => (
              <div className="form-group">
                <Label htmlFor={field.name}>Confirm password</Label>
                <Input
                  id={field.name}
                  type="password"
                  autoComplete="new-password"
                  value={field.state.value}
                  onChange={(event) => field.handleChange(event.target.value)}
                  onBlur={field.handleBlur}
                  disabled={confirmReset.isPending}
                  required
                />
                {field.state.meta.isTouched && field.state.meta.errors?.[0] && (
                  <p className="form-error">{field.state.meta.errors[0]}</p>
                )}
              </div>
            )}
          </form.Field>

          <Button type="submit" className="w-full" disabled={confirmReset.isPending}>
            {confirmReset.isPending ? "Updating…" : "Update password"}
          </Button>
        </form>

        <div className="text-center text-sm">
          <Link to="/login" className="font-semibold text-blue-600 hover:text-blue-800">
            Return to login
          </Link>
        </div>
      </div>
    </div>
  );
}

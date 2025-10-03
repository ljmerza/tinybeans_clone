import { useEffect, useState } from "react";

import { StatusMessage } from "@/components";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useNavigate } from "@tanstack/react-router";

import { useMagicLoginVerify } from "../hooks";

type MagicLoginHandlerProps = {
  token?: string;
};

export function MagicLoginHandler({ token }: MagicLoginHandlerProps) {
  const navigate = useNavigate();
  const magicLoginVerify = useMagicLoginVerify();
  const [status, setStatus] = useState<"verifying" | "success" | "error">(
    "verifying",
  );

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }

    magicLoginVerify
      .mutateAsync({ token })
      .then(() => {
        setStatus("success");
      })
      .catch(() => {
        setStatus("error");
      });
  }, [token, magicLoginVerify]);

  if (status === "verifying") {
    return (
      <div className="mx-auto max-w-sm p-6 space-y-4">
        <StatusMessage variant="info">
          Verifying your magic login link...
        </StatusMessage>
        <div className="flex justify-center">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="mx-auto max-w-sm p-6 space-y-4">
        <StatusMessage variant="success">
          Successfully logged in! Redirecting...
        </StatusMessage>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-sm p-6 space-y-4">
      <StatusMessage variant="error">
        {magicLoginVerify.error?.message ??
          "Invalid or expired magic login link. Please request a new one."}
      </StatusMessage>
      <Button onClick={() => navigate({ to: "/login" })} className="w-full">
        Return to Login
      </Button>
    </div>
  );
}

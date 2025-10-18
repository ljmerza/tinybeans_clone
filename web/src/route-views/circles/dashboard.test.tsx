import "@/i18n/config";
import { renderWithQueryClient } from "@/test-utils";
import { screen } from "@testing-library/react";
import { describe, it, vi, expect, beforeEach } from "vitest";

vi.mock("@/features/circles", async (importOriginal) => {
  const mod = await importOriginal();
  return {
    ...mod,
    useCircleMembers: vi.fn()
  };
});

import { useCircleMembers } from "@/features/circles";
import { CircleDashboard } from "./dashboard";

describe("CircleDashboard", () => {
  beforeEach(() => {
    (useCircleMembers as unknown as vi.Mock).mockReset();
  });

  it("renders without hook errors", () => {
    (useCircleMembers as unknown as vi.Mock)
      .mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        isFetching: false,
      })
      .mockReturnValue({
        data: {
          circle: { id: 3, name: "Family", member_count: 2 },
          members: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        isFetching: false,
      });

    renderWithQueryClient(<CircleDashboard circleId="3" />);
    expect(useCircleMembers).toHaveBeenCalled();
  });
});

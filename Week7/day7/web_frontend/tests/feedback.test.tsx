import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { FeedbackButtons } from "@/components/FeedbackButtons";
import { api } from "@/lib/api";

vi.mock("@/lib/api", async original => {
  const actual = await original<typeof import("@/lib/api")>();
  return { ...actual, api: { ...actual.api, recordInteraction: vi.fn() } };
});

beforeEach(() => vi.mocked(api.recordInteraction).mockReset());

it("prevents rapid duplicate feedback submission", async () => {
  let finish!: () => void;
  vi.mocked(api.recordInteraction).mockReturnValue(new Promise(resolve => { finish = () => resolve({ interaction_id: "i1" }); }));
  render(<FeedbackButtons customerId="c1" propertyId="p1" sessionId="r1" onBook={() => {}} />);
  fireEvent.click(screen.getByText("Like"));
  fireEvent.click(screen.getByText("Like"));
  expect(api.recordInteraction).toHaveBeenCalledTimes(1);
  expect(api.recordInteraction).toHaveBeenCalledWith("c1", "p1", "liked", "r1");
  finish();
  await waitFor(() => expect(screen.getByText("Liked ✓")).toBeInTheDocument());
});

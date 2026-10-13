import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LeadScoringPage from "@/app/ml/leads/page";
import { mlApi, type Week8Lead } from "@/lib/mlApi";

const mocks = vi.hoisted(() => ({
  session: {
    customer: { customer_id: "customer-1", full_name: "Verified Customer", phone: null as string | null },
  },
}));

vi.mock("@/components/SessionProvider", () => ({
  useSession: () => mocks.session,
}));

const demoLead: Week8Lead = {
  id: "lead-1",
  lead_id: "lead-1",
  name: "Ayesha Khan",
  phone: "+92 300 0000000",
  city: "Lahore",
  location: "DHA",
  preferred_city: "Lahore",
  preferred_location: "DHA",
  budget_pkr: 30000000,
  property_type: "House",
  purpose: "Buy",
  lead_source: "Call",
  calls: 3,
  number_of_calls: 3,
  duration_min: 15,
  total_call_duration_min: 15,
  response_time_minutes: 20,
  visit_booked: 1,
  days_since_first_contact: 3,
  objection_raised: "None",
  follow_up_count: 1,
  budget_match_ratio: 1,
  converted: 0,
  tier: "Warm",
  lead_score_pct: 65,
};

describe("lead pipeline labels", () => {
  beforeEach(() => {
    mocks.session.customer = {
      customer_id: "customer-1",
      full_name: "Verified Customer",
      phone: null,
    };
    vi.spyOn(mlApi, "getLeads").mockResolvedValue({ total: 1, leads: [demoLead] });
    vi.spyOn(mlApi, "getRealLeads").mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("uses neutral lead-pipeline wording", async () => {
    render(<LeadScoringPage />);

    expect(await screen.findAllByText("Lead Pipeline")).toHaveLength(2);
    expect(screen.getByText(/Priority suggestions are a guide/)).toBeInTheDocument();
    expect(screen.getByText("Ayesha Khan")).toBeInTheDocument();
    expect(screen.queryByText("Verified Customer")).not.toBeInTheDocument();
    expect(screen.queryByText(/Generated|Demo|Week 8/)).not.toBeInTheDocument();
  });

  it("uses the same neutral wording when lead services are unavailable", async () => {
    vi.mocked(mlApi.getLeads).mockRejectedValue(new Error("API unavailable"));

    render(<LeadScoringPage />);

    expect(await screen.findAllByText("Lead Pipeline")).toHaveLength(2);
    expect(screen.getByText(/Priority suggestions are a guide/)).toBeInTheDocument();
    expect(screen.queryByText("Verified Customer")).not.toBeInTheDocument();
  });
});

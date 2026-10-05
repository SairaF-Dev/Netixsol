import { describe, expect, it, vi, beforeEach } from "vitest";
import { mlApi, MlApiError } from "@/lib/mlApi";

describe("Week 8 ML API Client Integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls predictPrice with valid payload and returns structured response", async () => {
    const mockValuationResponse = {
      purpose: "For Sale",
      predicted_fair_price_pkr: 35000000.0,
      lower_bound_pkr: 31000000.0,
      upper_bound_pkr: 39000000.0,
      confidence_band_pkr: [31000000.0, 39000000.0],
      listed_price_pkr: 36000000.0,
      verdict: "Fair Market Value",
      deviation_percentage: 2.8,
      human_readable_summary: "Model estimates fair market price around 35,000,000 PKR.",
      inference_latency_ms: 12.5,
      model_version: "huber_v1.0",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockValuationResponse,
    } as Response);

    const result = await mlApi.predictPrice({
      purpose: "For Sale",
      property_type: "House",
      city: "Lahore",
      location: "DHA Defence Phase 5",
      area_marla: 10,
    });

    expect(result.predicted_fair_price_pkr).toBe(35000000.0);
    expect(result.verdict).toBe("Fair Market Value");
    expect(result.model_version).toBe("huber_v1.0");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/predict/price"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("calls scoreLead and returns probability, tier, and persona", async () => {
    const mockLeadResponse = {
      conversion_probability: 0.78,
      lead_score_pct: 78.0,
      tier: "Hot",
      priority_rank: 1,
      recommended_sla_action: "Immediate call within 15 minutes",
      customer_persona: "High-Net-Worth Investor",
      persona_cluster_id: 1,
      urdulish_explanation: "High budget and multiple calls indicate high conversion propensity.",
      inference_latency_ms: 8.2,
      model_version: "lgbm_optuna_v1.0",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockLeadResponse,
    } as Response);

    const result = await mlApi.scoreLead({
      lead_source: "Call",
      preferred_city: "Islamabad",
      preferred_location: "F-7",
      property_type: "House",
      purpose: "Buy",
      budget_pkr: 50000000,
    });

    expect(result.tier).toBe("Hot");
    expect(result.conversion_probability).toBe(0.78);
    expect(result.customer_persona).toBe("High-Net-Worth Investor");
  });

  it("calls explainLead and returns TreeSHAP feature attributions", async () => {
    const mockShapResponse = {
      conversion_probability: 0.78,
      tier: "Hot",
      top_positive_features: [
        { feature: "total_call_duration_min", shap_value: 0.35 },
        { feature: "visit_booked", shap_value: 0.28 },
      ],
      top_negative_features: [
        { feature: "days_since_first_contact", shap_value: -0.05 },
      ],
      urdulish_explanation: "TreeSHAP explanation",
      inference_latency_ms: 18.0,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockShapResponse,
    } as Response);

    const result = await mlApi.explainLead({
      lead_source: "Call",
      preferred_city: "Islamabad",
      preferred_location: "F-7",
      property_type: "House",
      purpose: "Buy",
      budget_pkr: 50000000,
    });

    expect(result.top_positive_features.length).toBe(2);
    expect(result.top_positive_features[0].feature).toBe("total_call_duration_min");
  });

  it("calls chatAssistant and returns LangGraph facts and guard status", async () => {
    const mockChatResponse = {
      response: "Model ke mutabiq DHA Lahore mein 10 marla house ki fair price 3.5 Crore PKR hai.",
      intent: "valuation",
      tool_calls: ["price_predictor_tool"],
      tool_results: { price_predictor_tool: { predicted_fair_price_pkr: 35000000.0 } },
      missing_fields: [],
      language: "urdulish",
      guard_triggered: false,
      inference_latency_ms: 120.0,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockChatResponse,
    } as Response);

    const result = await mlApi.chatAssistant("DHA Lahore mein 10 marla ghar kitne ka hai?");
    expect(result.intent).toBe("valuation");
    expect(result.guard_triggered).toBe(false);
    expect(result.tool_calls).toContain("price_predictor_tool");
  });

  it("handles offline backend error gracefully via MlApiError", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

    await expect(
      mlApi.predictPrice({
        purpose: "For Sale",
        property_type: "House",
        city: "Lahore",
        location: "DHA",
        area_marla: 10,
      })
    ).rejects.toThrow(MlApiError);
  });
});

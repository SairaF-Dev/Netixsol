"use client";

import React, { useState } from "react";
import {
  mlApi,
  MlApiError,
  type LeadScoringRequest,
  type LeadScoringResponse,
  type LeadExplanationResponse,
} from "@/lib/mlApi";
import { Loading, ErrorNotice } from "@/components/States";

const PRESET_LEADS = [
  {
    label: "🔥 High-Net-Worth Investor",
    data: {
      lead_source: "Call",
      preferred_city: "Lahore",
      preferred_location: "DHA Phase 5",
      property_type: "House",
      purpose: "For Sale",
      budget_pkr: 50_000_000,
      number_of_calls: 5,
      total_call_duration_min: 22,
      visit_booked: 1,
      response_time_minutes: 10,
    },
  },
  {
    label: "⏳ Warm Urban Buyer",
    data: {
      lead_source: "WhatsApp",
      preferred_city: "Islamabad",
      preferred_location: "F-10",
      property_type: "House",
      purpose: "For Sale",
      budget_pkr: 25_000_000,
      number_of_calls: 3,
      total_call_duration_min: 12,
      visit_booked: 0,
      response_time_minutes: 45,
    },
  },
  {
    label: "❄️ Cold Portal Inquiry",
    data: {
      lead_source: "Website",
      preferred_city: "Karachi",
      preferred_location: "Gulshan-e-Iqbal",
      property_type: "Flat",
      purpose: "For Rent",
      budget_pkr: 4_500_000,
      number_of_calls: 1,
      total_call_duration_min: 3,
      visit_booked: 0,
      response_time_minutes: 180,
    },
  },
];

function formatFeatureName(raw: string): string {
  const map: Record<string, string> = {
    visit_booked: "Site Visit Booked",
    budget_pkr: "Client Budget (PKR)",
    number_of_calls: "Call Engagement Frequency",
    total_call_duration_min: "Total Call Duration",
    response_time_minutes: "Response Time Latency",
    lead_source: "Acquisition Channel",
    preferred_city: "Preferred Metro",
    location_frequency: "Locality Popularity Index",
    property_type: "Property Type Match",
  };
  return map[raw] || raw.replaceAll("_", " ");
}

export default function LeadScoringStudio() {
  const [formData, setFormData] = useState<LeadScoringRequest>({
    lead_source: "Call",
    preferred_city: "Lahore",
    preferred_location: "DHA Phase 5",
    property_type: "House",
    purpose: "For Sale",
    budget_pkr: 40_000_000,
    number_of_calls: 4,
    total_call_duration_min: 18,
    visit_booked: 1,
    response_time_minutes: 15,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scoreResult, setScoreResult] = useState<LeadScoringResponse | null>(null);
  const [shapResult, setShapResult] = useState<LeadExplanationResponse | null>(null);

  const applyPreset = (preset: (typeof PRESET_LEADS)[0]) => {
    setFormData(preset.data);
    setScoreResult(null);
    setShapResult(null);
    setError(null);
  };

  const handleScoreAndExplain = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setScoreResult(null);
    setShapResult(null);

    try {
      const [scoreRes, shapRes] = await Promise.all([
        mlApi.scoreLead(formData),
        mlApi.explainLead(formData),
      ]);
      setScoreResult(scoreRes);
      setShapResult(shapRes);
    } catch (err: any) {
      setError(
        err instanceof MlApiError
          ? err.message
          : "Could not create a lead-priority suggestion. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const maxAbsShap = Math.max(
    ...(shapResult?.top_positive_features?.map((f) => Math.abs(f.shap_value)) || [1]),
    ...(shapResult?.top_negative_features?.map((f) => Math.abs(f.shap_value)) || [1]),
    0.1
  );

  return (
    <div style={{ display: "grid", gap: "24px" }}>
      <div>
        <span className="eyebrow">LEAD FOLLOW-UP</span>
        <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "clamp(2rem, 3.5vw, 2.7rem)", margin: "4px 0 8px" }}>
          Lead Priority & Follow-Up Factors
        </h1>
        <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.95rem" }}>
          Review the details that contribute to a lead-priority suggestion.
        </p>
      </div>

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Quick Select:
        </span>
        {PRESET_LEADS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => applyPreset(p)}
            style={{
              padding: "6px 14px",
              fontSize: "0.8rem",
              fontWeight: 600,
              borderRadius: "8px",
              border: "1px solid var(--line)",
              background: "#ffffff",
              color: "var(--ink)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
          gap: "24px",
          alignItems: "start",
        }}
      >
        <div className="panel" style={{ padding: "26px" }}>
          <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", marginTop: 0, marginBottom: "18px" }}>
            Lead Profile & Signals
          </h2>

          <form onSubmit={handleScoreAndExplain} style={{ display: "grid", gap: "14px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label>
                Metro City
                <select
                  value={formData.preferred_city}
                  onChange={(e) => setFormData({ ...formData, preferred_city: e.target.value })}
                >
                  {["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>

              <label>
                Locality / Area
                <input
                  value={formData.preferred_location}
                  onChange={(e) => setFormData({ ...formData, preferred_location: e.target.value })}
                  placeholder="e.g. DHA Phase 5"
                  required
                />
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label>
                Property Type
                <select
                  value={formData.property_type}
                  onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
                >
                  {["House", "Flat", "Upper Portion", "Lower Portion", "Farm House", "Penthouse", "Room"].map((t) => (
                    <option key={t} value={t}>{t === "Flat" ? "Flat / Apartment" : t}</option>
                  ))}
                </select>
              </label>

              <label>
                Purpose
                <select
                  value={formData.purpose}
                  onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                >
                  <option value="For Sale">For Sale (Purchase)</option>
                  <option value="For Rent">For Rent</option>
                </select>
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <label>
                Lead Source
                <select
                  value={formData.lead_source}
                  onChange={(e) => setFormData({ ...formData, lead_source: e.target.value })}
                >
                  {["Call", "WhatsApp", "Website", "Walk-in", "Referral", "Facebook"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>

              <label>
                Budget (PKR)
                <input
                  type="number"
                  min="0"
                  step="500000"
                  value={formData.budget_pkr}
                  onChange={(e) => setFormData({ ...formData, budget_pkr: Number(e.target.value) })}
                  required
                />
              </label>
            </div>

            <div style={{ background: "#f8faf9", padding: "16px", borderRadius: "10px", border: "1px solid #edf1ee", display: "grid", gap: "12px" }}>
              <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--forest)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Engagement & Intent Signals
              </span>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <label>
                  Number of Calls ({formData.number_of_calls || 1})
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={formData.number_of_calls || 1}
                    onChange={(e) => setFormData({ ...formData, number_of_calls: Number(e.target.value) })}
                  />
                </label>

                <label>
                  Total Call Duration ({formData.total_call_duration_min || 5} min)
                  <input
                    type="range"
                    min="1"
                    max="60"
                    value={formData.total_call_duration_min || 5}
                    onChange={(e) => setFormData({ ...formData, total_call_duration_min: Number(e.target.value) })}
                  />
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "4px" }}>
                <span style={{ fontSize: "0.82rem", fontWeight: 600 }}>Site Visit Booked?</span>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, visit_booked: 1 })}
                    style={{
                      padding: "5px 12px",
                      borderRadius: "6px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      border: "none",
                      cursor: "pointer",
                      background: formData.visit_booked === 1 ? "#214e43" : "#e0e6e3",
                      color: formData.visit_booked === 1 ? "#ffffff" : "#4a5a54",
                    }}
                  >
                    Yes (Booked)
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, visit_booked: 0 })}
                    style={{
                      padding: "5px 12px",
                      borderRadius: "6px",
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      border: "none",
                      cursor: "pointer",
                      background: formData.visit_booked === 0 ? "#214e43" : "#e0e6e3",
                      color: formData.visit_booked === 0 ? "#ffffff" : "#4a5a54",
                    }}
                  >
                    No
                  </button>
                </div>
              </div>
            </div>

            {error && <ErrorNotice message={error} />}

            <button type="submit" className="button primary" disabled={loading} style={{ padding: "12px", marginTop: "4px" }}>
              {loading ? "Preparing suggestion…" : "Show Lead Suggestion"}
            </button>
          </form>
        </div>

        <div style={{ display: "grid", gap: "20px" }}>
          {loading && <Loading label="Preparing lead-priority suggestion…" />}

          {!loading && !scoreResult && (
            <div className="panel" style={{ textAlign: "center", padding: "60px 24px", color: "var(--muted)" }}>
              <span style={{ fontSize: "3rem" }}>🎯</span>
              <h3 style={{ fontFamily: "Playfair Display, serif", color: "var(--ink)", margin: "14px 0 6px" }}>
                Ready to Review Lead
              </h3>
              <p style={{ margin: "auto", maxWidth: "340px", fontSize: "0.88rem" }}>
                Enter lead details or choose a quick option to see what may affect its suggested priority.
              </p>
            </div>
          )}

          {scoreResult && (
            <div className="panel" style={{ padding: "26px", display: "grid", gap: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <span className="eyebrow">LEAD PRIORITY</span>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
                    <span style={{ fontFamily: "Playfair Display, serif", fontSize: "2.8rem", fontWeight: 700, color: "var(--ink)" }}>
                      {scoreResult.lead_score_pct.toFixed(0)}/100
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: "right", display: "grid", gap: "4px" }}>
                  <span
                    className={
                      scoreResult.tier === "Hot"
                        ? "badge-hot"
                        : scoreResult.tier === "Warm"
                        ? "badge-warm"
                        : "badge-cold"
                    }
                    style={{ fontSize: "0.85rem", padding: "5px 14px", alignSelf: "flex-end" }}
                  >
                    {scoreResult.tier.toUpperCase()} TIER
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>
                    Priority Rank #{scoreResult.priority_rank}
                  </span>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={{ background: "#f8faf9", padding: "14px", borderRadius: "10px", border: "1px solid #edf1ee" }}>
                  <span style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)", fontWeight: 700 }}>
                    Buyer Profile
                  </span>
                  <div style={{ fontWeight: 700, color: "var(--ink)", fontSize: "0.95rem", marginTop: "4px" }}>
                    {scoreResult.customer_persona || "Urban Homebuyer"}
                  </div>
                </div>

                <div style={{ background: "#fdf8f0", padding: "14px", borderRadius: "10px", border: "1px solid #faeedb" }}>
                  <span style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--gold)", fontWeight: 700 }}>
                    Recommended Follow-Up
                  </span>
                  <div style={{ fontWeight: 700, color: "#854d0e", fontSize: "0.95rem", marginTop: "4px" }}>
                    {scoreResult.recommended_sla_action}
                  </div>
                </div>
              </div>

              {scoreResult.urdulish_explanation && (
                <div style={{ background: "#f0f7f4", padding: "14px 16px", borderRadius: "8px", border: "1px solid #d8eae1", fontSize: "0.88rem", color: "#17332d", lineHeight: 1.5 }}>
                  <span style={{ fontWeight: 700, display: "block", marginBottom: "4px", fontSize: "0.75rem", textTransform: "uppercase", color: "var(--forest)" }}>
                    💡 Why this suggestion
                  </span>
                  {scoreResult.urdulish_explanation}
                </div>
              )}

              {shapResult && (
                <div style={{ marginTop: "4px", display: "grid", gap: "14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className="eyebrow">FACTORS BEHIND THIS SUGGESTION</span>
                  </div>

                  <div style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "#166534" }}>
                      ▲ Factors that raise the priority
                    </span>
                    {shapResult.top_positive_features?.map((item) => {
                      const widthPct = Math.min(100, Math.round((Math.abs(item.shap_value) / maxAbsShap) * 100));
                      return (
                        <div key={item.feature} style={{ display: "grid", gap: "3px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                            <span>{formatFeatureName(item.feature)}</span>
                            <strong style={{ color: "#166534" }}>Raises priority</strong>
                          </div>
                          <div style={{ height: "6px", background: "#e8edea", borderRadius: "3px", overflow: "hidden" }}>
                            <div style={{ width: `${widthPct}%`, height: "100%", background: "#16a34a", borderRadius: "3px" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {shapResult.top_negative_features && shapResult.top_negative_features.length > 0 && (
                    <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                      <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "#991b1b" }}>
                        ▼ Factors that lower the priority
                      </span>
                      {shapResult.top_negative_features.map((item) => {
                        const widthPct = Math.min(100, Math.round((Math.abs(item.shap_value) / maxAbsShap) * 100));
                        return (
                          <div key={item.feature} style={{ display: "grid", gap: "3px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                              <span>{formatFeatureName(item.feature)}</span>
                              <strong style={{ color: "#dc2626" }}>Lowers priority</strong>
                            </div>
                            <div style={{ height: "6px", background: "#fef2f2", borderRadius: "3px", overflow: "hidden" }}>
                              <div style={{ width: `${widthPct}%`, height: "100%", background: "#ef4444", borderRadius: "3px" }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

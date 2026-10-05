"use client";

import React, { useEffect, useState } from "react";
import {
  mlApi,
  MlApiError,
  type MarketInsightsResponse,
  type MarketStatItem,
} from "@/lib/mlApi";
import { Loading, ErrorNotice } from "@/components/States";

const POPULAR_SOCIETIES = [
  { city: "Lahore", location: "DHA", label: "📍 DHA Lahore" },
  { city: "Karachi", location: "Clifton", label: "📍 Clifton Karachi" },
  { city: "Islamabad", location: "F-10", label: "📍 F-10 Islamabad" },
  { city: "Lahore", location: "Bahria Town", label: "📍 Bahria Town LHE" },
  { city: "Lahore", location: "Gulberg", label: "📍 Gulberg Lahore" },
  { city: "Rawalpindi", location: "Bahria Town", label: "📍 Bahria RWP" },
];

function formatPkr(val: number): string {
  if (!val || isNaN(val)) return "PKR 0";
  if (val >= 10_000_000) {
    return `PKR ${(val / 10_000_000).toFixed(2)} Crore`;
  }
  if (val >= 100_000) {
    return `PKR ${(val / 100_000).toFixed(2)} Lakh`;
  }
  return `PKR ${Math.round(val).toLocaleString()}`;
}

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<"market" | "models" | "society">("market");

  const [insights, setInsights] = useState<MarketInsightsResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedCity, setSelectedCity] = useState("Lahore");
  const [selectedLocation, setSelectedLocation] = useState("DHA");
  const [selectedPurpose, setSelectedPurpose] = useState("For Sale");
  const [lookupResult, setLookupResult] = useState<MarketStatItem | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  useEffect(() => {
    async function loadAllAnalytics() {
      setLoading(true);
      setError(null);
      try {
        const [insightsRes, infoRes] = await Promise.allSettled([
          mlApi.getMarketInsights(),
          mlApi.getModelInfo(),
        ]);

        if (insightsRes.status === "fulfilled") {
          setInsights(insightsRes.value);
        }
        if (infoRes.status === "fulfilled") {
          setModelInfo(infoRes.value?.models || null);
        }

        const dhaStats = await mlApi.getMarketStats("Lahore", "DHA", "For Sale");
        setLookupResult(dhaStats);
      } catch (err: any) {
        setError(err instanceof MlApiError ? err.message : "Failed to load analytics data from backend.");
      } finally {
        setLoading(false);
      }
    }
    loadAllAnalytics();
  }, []);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLookupLoading(true);
    try {
      const res = await mlApi.getMarketStats(selectedCity, selectedLocation, selectedPurpose);
      setLookupResult(res);
    } catch {
      // Handled gracefully
    } finally {
      setLookupLoading(false);
    }
  };

  const handlePresetSociety = (s: { city: string; location: string }) => {
    setSelectedCity(s.city);
    setSelectedLocation(s.location);
    setLookupLoading(true);
    mlApi.getMarketStats(s.city, s.location, selectedPurpose).then(setLookupResult).finally(() => setLookupLoading(false));
  };

  if (loading) {
    return <Loading label="Loading real estate analytics & verified model performance…" />;
  }

  return (
    <div style={{ display: "grid", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <span className="eyebrow">DATA INTELLIGENCE & MODEL METRICS</span>
          <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "clamp(2rem, 3.5vw, 2.7rem)", margin: "4px 0 8px" }}>
            Real Estate & ML Analytics
          </h1>
          <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.95rem" }}>
            Empirical valuations, metropolitan price benchmarks, rental yields, and verified machine learning validation metrics.
          </p>
        </div>

        <div style={{ display: "flex", background: "#e8edea", borderRadius: "8px", padding: "3px", gap: "4px" }}>
          {[
            { id: "market", label: "Metropolitan Market" },
            { id: "society", label: "Society Benchmarks" },
            { id: "models", label: "ML Model Verification" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: "6px 14px",
                fontSize: "0.8rem",
                fontWeight: 700,
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                background: activeTab === tab.id ? "#214e43" : "transparent",
                color: activeTab === tab.id ? "#ffffff" : "#4a5e56",
                transition: "all 0.15s ease",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorNotice message={error} />}

      {activeTab === "market" && insights && (
        <div style={{ display: "grid", gap: "22px" }}>
          <div className="panel" style={{ padding: "24px", overflowX: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <span className="eyebrow">ACROSS 5 MAJOR METROS</span>
                <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.35rem", margin: "4px 0" }}>
                  Capital Values & Rental Yield Matrix
                </h2>
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                Source: {insights.total_dataset_records?.toLocaleString()} clean listings
              </span>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.86rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e1e7e4", color: "var(--muted)", fontSize: "0.74rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  <th style={{ padding: "12px 14px" }}>Metro City</th>
                  <th style={{ padding: "12px 14px" }}>Verified Listings</th>
                  <th style={{ padding: "12px 14px" }}>Avg Sale Price / Marla</th>
                  <th style={{ padding: "12px 14px" }}>Median Sale / Marla</th>
                  <th style={{ padding: "12px 14px" }}>Avg Monthly Rent / Marla</th>
                  <th style={{ padding: "12px 14px" }}>Gross Rental Yield</th>
                </tr>
              </thead>
              <tbody>
                {insights.cities.map((city) => {
                  const sale = insights.sale_by_city.find((c) => c.city.toLowerCase() === city.toLowerCase());
                  const rent = insights.rent_by_city.find((c) => c.city.toLowerCase() === city.toLowerCase());

                  const salePerMarla = sale?.avg_price_per_marla_pkr || 1;
                  const rentPerMarla = rent?.avg_price_per_marla_pkr || 0;
                  const yieldPct = salePerMarla > 0 && rentPerMarla > 0 ? ((rentPerMarla * 12) / salePerMarla) * 100 : 0;

                  return (
                    <tr key={city} style={{ borderBottom: "1px solid #edf1ee" }}>
                      <td style={{ padding: "14px", fontWeight: 700, color: "var(--ink)" }}>{city}</td>
                      <td style={{ padding: "14px", color: "var(--muted)" }}>{sale?.total_listings_matched?.toLocaleString() || 0}</td>
                      <td style={{ padding: "14px", fontWeight: 600 }}>{formatPkr(sale?.avg_price_per_marla_pkr || 0)}</td>
                      <td style={{ padding: "14px", color: "var(--muted)" }}>{formatPkr(sale?.median_price_per_marla_pkr || 0)}</td>
                      <td style={{ padding: "14px", color: "var(--forest)", fontWeight: 600 }}>{formatPkr(rent?.avg_price_per_marla_pkr || 0)}</td>
                      <td style={{ padding: "14px" }}>
                        <span
                          style={{
                            background: yieldPct >= 4 ? "#e6f4ea" : "#f1f3f1",
                            color: yieldPct >= 4 ? "#137333" : "#5f6368",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontWeight: 700,
                            fontSize: "0.78rem",
                          }}
                        >
                          {yieldPct.toFixed(2)}% / yr
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "society" && (
        <div style={{ display: "grid", gap: "22px" }}>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Popular Societies:
            </span>
            {POPULAR_SOCIETIES.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={() => handlePresetSociety(s)}
                style={{
                  padding: "5px 12px",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  borderRadius: "20px",
                  border: "1px solid var(--line)",
                  background: selectedCity === s.city && selectedLocation === s.location ? "var(--forest)" : "#ffffff",
                  color: selectedCity === s.city && selectedLocation === s.location ? "#ffffff" : "var(--ink)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {s.label}
              </button>
            ))}
          </div>

          <form
            onSubmit={handleLookup}
            style={{
              background: "var(--cream)",
              padding: "16px 20px",
              borderRadius: "12px",
              border: "1px solid var(--line)",
              display: "grid",
              gridTemplateColumns: "1fr 1.5fr 1fr auto",
              gap: "12px",
              alignItems: "center",
            }}
          >
            <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)} style={{ background: "#ffffff" }}>
              {["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            <input
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              placeholder="Society / Sector (e.g. DHA, Clifton, F-10)"
              style={{ background: "#ffffff" }}
              required
            />

            <select value={selectedPurpose} onChange={(e) => setSelectedPurpose(e.target.value)} style={{ background: "#ffffff" }}>
              <option value="For Sale">For Sale</option>
              <option value="For Rent">For Rent</option>
            </select>

            <button type="submit" className="button primary" disabled={lookupLoading} style={{ padding: "11px 20px" }}>
              {lookupLoading ? "Querying..." : "Analyze Society"}
            </button>
          </form>

          {lookupResult && (
            <div className="panel" style={{ padding: "26px", borderLeft: "5px solid var(--forest)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <span className="eyebrow">{lookupResult.purpose.toUpperCase()} INTELLIGENCE DOSSIER</span>
                  <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.8rem", margin: "4px 0" }}>
                    {selectedLocation}, {selectedCity}
                  </h2>
                  <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                    Based on {lookupResult.total_listings_matched?.toLocaleString()} catalog listings in dataset
                  </span>
                </div>

                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--muted)", textTransform: "uppercase" }}>Average Rate</span>
                  <div style={{ fontFamily: "Playfair Display, serif", fontSize: "1.6rem", fontWeight: 700, color: "var(--forest)" }}>
                    {formatPkr(lookupResult.avg_price_per_marla_pkr)} / Marla
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px", marginTop: "20px" }}>
                <div style={{ background: "#f8faf9", padding: "16px", borderRadius: "10px", border: "1px solid #edf1ee" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontWeight: 700 }}>5 MARLA ESTIMATE</span>
                  <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--ink)", marginTop: "4px" }}>
                    {formatPkr(lookupResult.avg_price_per_marla_pkr * 5)}
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "16px", borderRadius: "10px", border: "1px solid #edf1ee" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontWeight: 700 }}>10 MARLA ESTIMATE</span>
                  <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--ink)", marginTop: "4px" }}>
                    {formatPkr(lookupResult.avg_price_per_marla_pkr * 10)}
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "16px", borderRadius: "10px", border: "1px solid #edf1ee" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontWeight: 700 }}>1 KANAL (20M) ESTIMATE</span>
                  <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--ink)", marginTop: "4px" }}>
                    {formatPkr(lookupResult.avg_price_per_marla_pkr * 20)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "models" && modelInfo && (
        <div style={{ display: "grid", gap: "22px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "20px" }}>
            <div className="panel" style={{ padding: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <span className="eyebrow">DUAL-REGRESSION HUBER</span>
                  <h3 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", margin: "4px 0" }}>
                    Sale Valuation Model
                  </h3>
                </div>
                <span style={{ fontSize: "0.72rem", background: "#e8f5e9", color: "#2e7d32", padding: "3px 8px", borderRadius: "6px", fontWeight: 700 }}>
                  {modelInfo.sale_valuation?.version}
                </span>
              </div>

              <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: "0 0 16px" }}>
                LightGBM with Huber objective (alpha=0.9) to resist extreme market outliers.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST MAPE</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--forest)" }}>
                    {modelInfo.sale_valuation?.locked_test_metrics?.mape}%
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST MdAPE</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--forest)" }}>
                    {modelInfo.sale_valuation?.locked_test_metrics?.mdape}%
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST R² SCORE</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--ink)" }}>
                    {modelInfo.sale_valuation?.locked_test_metrics?.r2}
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST MAE</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--ink)" }}>
                    {formatPkr(modelInfo.sale_valuation?.locked_test_metrics?.mae_pkr)}
                  </div>
                </div>
              </div>
            </div>

            <div className="panel" style={{ padding: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <span className="eyebrow">OPTUNA BAYESIAN OPTIMIZED</span>
                  <h3 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", margin: "4px 0" }}>
                    Lead Scoring Classifier
                  </h3>
                </div>
                <span style={{ fontSize: "0.72rem", background: "#fef3c7", color: "#92400e", padding: "3px 8px", borderRadius: "6px", fontWeight: 700 }}>
                  {modelInfo.lead_scoring?.version}
                </span>
              </div>

              <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: "0 0 16px" }}>
                LightGBM binary classifier tuned for imbalanced conversion prioritization.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST ROC-AUC</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#166534" }}>
                    {modelInfo.lead_scoring?.locked_test_metrics?.roc_auc}
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TEST PR-AUC</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#166534" }}>
                    {modelInfo.lead_scoring?.locked_test_metrics?.pr_auc}
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TOP 20% LIFT</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#c28b4b" }}>
                    {modelInfo.lead_scoring?.locked_test_metrics?.top_20_lift}x
                  </div>
                </div>

                <div style={{ background: "#f8faf9", padding: "12px", borderRadius: "8px" }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--muted)", fontWeight: 700 }}>TOP 20 PRECISION</span>
                  <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--ink)" }}>
                    {modelInfo.lead_scoring?.locked_test_metrics?.precision_at_top_20}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

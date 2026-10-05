"use client";

import { useState } from "react";
import {
  mlApi,
  MlApiError,
  type PricePredictionResponse,
  type PriceExplanationResponse,
} from "@/lib/mlApi";

const PRESET_PROPERTIES = [
  {
    label: "🏡 10 Marla DHA Lahore",
    city: "Lahore",
    location: "DHA Defence Phase 5",
    propertyType: "House",
    areaMarla: 10,
    bedrooms: 3,
    baths: 3,
    purpose: "For Sale" as const,
    asking: "20000000",
  },
  {
    label: "🏢 3 Bed Clifton Karachi",
    city: "Karachi",
    location: "Clifton",
    propertyType: "Flat",
    areaMarla: 8,
    bedrooms: 3,
    baths: 3,
    purpose: "For Sale" as const,
    asking: "25000000",
  },
  {
    label: "🏡 5 Marla Bahria Town",
    city: "Lahore",
    location: "Bahria Town",
    propertyType: "House",
    areaMarla: 5,
    bedrooms: 3,
    baths: 3,
    purpose: "For Sale" as const,
    asking: "14000000",
  },
  {
    label: "💎 1 Kanal F-10 Islamabad",
    city: "Islamabad",
    location: "F-10",
    propertyType: "House",
    areaMarla: 20,
    bedrooms: 5,
    baths: 5,
    purpose: "For Sale" as const,
    asking: "95000000",
  },
];

export default function PriceValuationPage() {
  const [purpose, setPurpose] = useState<"For Sale" | "For Rent">("For Sale");
  const [city, setCity] = useState("Lahore");
  const [location, setLocation] = useState("DHA Defence Phase 5");
  const [propertyType, setPropertyType] = useState("House");
  const [areaMarla, setAreaMarla] = useState<number>(10);
  const [bedrooms, setBedrooms] = useState<number>(3);
  const [baths, setBaths] = useState<number>(3);
  const [askingPrice, setAskingPrice] = useState<string>("20000000");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PricePredictionResponse | null>(null);

  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<PriceExplanationResponse | null>(null);

  const formatPkr = (val: number) => {
    if (!val) return "PKR 0";
    if (val >= 10_000_000) {
      return `${(val / 10_000_000).toFixed(2)} Crore`;
    }
    if (val >= 100_000) {
      return `${(val / 100_000).toFixed(2)} Lac`;
    }
    return `${val.toLocaleString()} PKR`;
  };

  function applyPreset(p: (typeof PRESET_PROPERTIES)[0]) {
    setPurpose(p.purpose);
    setCity(p.city);
    setLocation(p.location);
    setPropertyType(p.propertyType);
    setAreaMarla(p.areaMarla);
    setBedrooms(p.bedrooms);
    setBaths(p.baths);
    setAskingPrice(p.asking);
    setResult(null);
    setExplanation(null);
    setError(null);
  }

  async function handlePredict(e: React.FormEvent) {
    e.preventDefault();
    if (areaMarla <= 0) {
      setError("Property area must be greater than 0 Marlas.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    setExplanation(null);

    try {
      const payload = {
        purpose,
        city,
        location: location.trim() || "Unknown",
        property_type: propertyType,
        area_marla: Number(areaMarla),
        bedrooms: Number(bedrooms),
        baths: Number(baths),
        ...(askingPrice ? { price: Number(askingPrice) } : {}),
      };

      const res = await mlApi.predictPrice(payload);
      setResult(res);
    } catch (err: any) {
      setError(err instanceof MlApiError ? err.message : "Failed to obtain price valuation from valuation engine.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFetchExplanation() {
    if (!result) return;
    setExplaining(true);
    try {
      const payload = {
        purpose,
        city,
        location: location.trim() || "Unknown",
        property_type: propertyType,
        area_marla: Number(areaMarla),
        bedrooms: Number(bedrooms),
        baths: Number(baths),
      };
      const res = await mlApi.explainPrice(payload);
      setExplanation(res);
    } catch (err: any) {
      setError(err instanceof MlApiError ? err.message : "Could not fetch explanation.");
    } finally {
      setExplaining(false);
    }
  }

  return (
    <section className="ml-valuation-page">
      {/* Executive Header */}
      <div className="page-title row" style={{ marginBottom: "26px" }}>
        <div>
          <span className="eyebrow" style={{ color: "#c28b4b", fontWeight: 700, letterSpacing: "0.14em" }}>
            SMART PROPERTY VALUATION & APPRAISAL
          </span>
          <h1 style={{ margin: "10px 0 12px", fontFamily: "Playfair Display" }}>
            Property Price Valuation Engine
          </h1>
          <p style={{ maxWidth: "620px", color: "var(--muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>
            Instant fair-market valuation, realistic price ranges, and deal verifications backed by verified historical transaction intelligence across major Pakistani metropolitan hubs.
          </p>
        </div>
        <div
          style={{
            background: "#e6f4ea",
            color: "#137333",
            border: "1px solid #ceead6",
            padding: "8px 16px",
            borderRadius: "20px",
            fontWeight: 600,
            fontSize: "0.82rem",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <span style={{ fontSize: "0.6rem" }}>●</span> Verified Valuation Index (Active)
        </div>
      </div>

      {/* Preset Quick Select Chips */}
      <div
        style={{
          background: "white",
          border: "1px solid #e2ded5",
          borderRadius: "12px",
          padding: "14px 18px",
          marginBottom: "26px",
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          boxShadow: "0 2px 10px rgba(23, 51, 45, 0.03)",
        }}
      >
        <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "#c28b4b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Sample Presets:
        </span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {PRESET_PROPERTIES.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applyPreset(p)}
              style={{
                fontSize: "0.75rem",
                padding: "5px 12px",
                borderRadius: "20px",
                border: "1px solid #dce2dc",
                background: location === p.location && city === p.city ? "#17332d" : "#faf9f6",
                color: location === p.location && city === p.city ? "white" : "#17332d",
                cursor: "pointer",
                fontWeight: 600,
                transition: "all 0.15s ease",
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "28px", alignItems: "start" }}>
        {/* Valuation Form */}
        <div className="panel" style={{ padding: "26px", borderRadius: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
            <h3 style={{ fontFamily: "Playfair Display", margin: 0, fontSize: "1.25rem" }}>
              Property Specifications
            </h3>
            <span style={{ fontSize: "0.72rem", background: "var(--cream)", padding: "4px 8px", borderRadius: "4px", color: "var(--muted)", fontWeight: 600 }}>
              Step 1: Input Specs
            </span>
          </div>

          <form onSubmit={handlePredict}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <label>
                Purpose
                <select value={purpose} onChange={(e) => setPurpose(e.target.value as any)}>
                  <option value="For Sale">For Sale</option>
                  <option value="For Rent">For Rent</option>
                </select>
              </label>

              <label>
                Property Type
                <select value={propertyType} onChange={(e) => setPropertyType(e.target.value)}>
                  <option value="House">House</option>
                  <option value="Flat">Flat / Apartment</option>
                  <option value="Upper Portion">Upper Portion</option>
                  <option value="Lower Portion">Lower Portion</option>
                  <option value="Penthouse">Penthouse</option>
                  <option value="Farm House">Farm House</option>
                  <option value="Room">Room</option>
                </select>
              </label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <label>
                City
                <select value={city} onChange={(e) => setCity(e.target.value)}>
                  <option value="Lahore">Lahore</option>
                  <option value="Karachi">Karachi</option>
                  <option value="Islamabad">Islamabad</option>
                  <option value="Rawalpindi">Rawalpindi</option>
                  <option value="Faisalabad">Faisalabad</option>
                </select>
              </label>

              <label>
                Area (Marla)
                <input
                  type="number"
                  min="0.5"
                  step="0.5"
                  value={areaMarla}
                  onChange={(e) => setAreaMarla(Number(e.target.value))}
                  required
                />
              </label>
            </div>

            <label>
              Location / Society
              <input
                type="text"
                placeholder="e.g. DHA Defence Phase 5, Bahria Town, Clifton"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
              />
            </label>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <label>
                Bedrooms
                <input
                  type="number"
                  min="0"
                  value={bedrooms}
                  onChange={(e) => setBedrooms(Number(e.target.value))}
                />
              </label>

              <label>
                Bathrooms
                <input
                  type="number"
                  min="0"
                  value={baths}
                  onChange={(e) => setBaths(Number(e.target.value))}
                />
              </label>
            </div>

            <label>
              Listed Asking Price (PKR, Optional)
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter asking price to evaluate market deal verdict"
                value={askingPrice}
                onChange={(e) => setAskingPrice(e.target.value)}
              />
            </label>

            {error && <div className="notice error">{error}</div>}

            <button type="submit" className="primary" disabled={loading} style={{ marginTop: "10px" }}>
              {loading ? "Calculating Fair Price…" : "Calculate Fair Market Price"}
            </button>
          </form>
        </div>

        {/* Prediction Results Display */}
        <div>
          {loading && (
            <div className="panel" style={{ textAlign: "center", padding: "50px 20px", borderRadius: "14px" }}>
              <div className="spinner" style={{ margin: "auto" }}></div>
              <p style={{ marginTop: "16px", color: "var(--muted)", fontSize: "0.92rem" }}>
                Analyzing comparable historical transactions & market factors…
              </p>
            </div>
          )}

          {!loading && !result && !error && (
            <div className="panel" style={{ textAlign: "center", padding: "50px 24px", borderRadius: "14px" }}>
              <span style={{ fontSize: "2.6rem" }}>🏡</span>
              <h3 style={{ fontFamily: "Playfair Display", margin: "16px 0 8px", fontSize: "1.3rem" }}>
                Instant Market Appraisal Ready
              </h3>
              <p style={{ color: "var(--muted)", maxWidth: "340px", margin: "auto", fontSize: "0.88rem", lineHeight: 1.5 }}>
                Fill in the specifications on the left or select a sample preset above to generate an authentic fair market valuation and deal verdict.
              </p>
            </div>
          )}

          {result && (
            <div
              className="panel"
              style={{
                borderLeft: "5px solid var(--forest)",
                padding: "26px",
                borderRadius: "14px",
                background: "white",
                boxShadow: "0 8px 24px rgba(23, 51, 45, 0.06)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "10px" }}>
                <div>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      letterSpacing: "0.14em",
                      fontWeight: 700,
                      color: "#c28b4b",
                      textTransform: "uppercase",
                    }}
                  >
                    {result.purpose} APPRAISAL
                  </span>
                  <h2 style={{ fontFamily: "Playfair Display", margin: "8px 0 2px", fontSize: "2rem", color: "var(--ink)" }}>
                    {formatPkr(result.predicted_fair_price_pkr)}
                  </h2>
                  <small style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                    PKR {result.predicted_fair_price_pkr.toLocaleString()}
                  </small>
                </div>

                {result.verdict && (
                  <span
                    style={{
                      padding: "6px 14px",
                      borderRadius: "20px",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      backgroundColor:
                        result.verdict === "Overpriced"
                          ? "#ffebee"
                          : result.verdict === "Underpriced"
                          ? "#e8f5e9"
                          : "var(--mint)",
                      color:
                        result.verdict === "Overpriced"
                          ? "#c62828"
                          : result.verdict === "Underpriced"
                          ? "#2e7d32"
                          : "var(--forest)",
                      border: `1px solid ${
                        result.verdict === "Overpriced"
                          ? "#ffcdd2"
                          : result.verdict === "Underpriced"
                          ? "#c8e6c9"
                          : "#c2dac8"
                      }`,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {result.verdict === "Overpriced"
                      ? `Overpriced (+${Math.abs(result.deviation_percentage || 0).toFixed(1)}%)`
                      : result.verdict === "Underpriced"
                      ? `Underpriced Deal (-${Math.abs(result.deviation_percentage || 0).toFixed(1)}%)`
                      : `Fair Market Price (${result.deviation_percentage ? result.deviation_percentage.toFixed(1) + "%" : "Fair"})`}
                  </span>
                )}
              </div>

              {/* Price Range Spectrum */}
              <div
                style={{
                  background: "#fbf9f5",
                  border: "1px solid #ede8de",
                  padding: "16px 18px",
                  borderRadius: "10px",
                  margin: "20px 0 16px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: "8px" }}>
                  <span style={{ color: "var(--muted)" }}>Conservative Valuation (Lower Bound)</span>
                  <strong>{formatPkr(result.lower_bound_pkr)}</strong>
                </div>
                <div style={{ height: "6px", background: "#e5ede8", borderRadius: "4px", overflow: "hidden", margin: "6px 0 10px" }}>
                  <div
                    style={{
                      height: "100%",
                      width: "60%",
                      background: "linear-gradient(90deg, #17332d 0%, #2e7d32 100%)",
                      borderRadius: "4px",
                    }}
                  ></div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem" }}>
                  <span style={{ color: "var(--muted)" }}>Premium Market Valuation (Upper Bound)</span>
                  <strong>{formatPkr(result.upper_bound_pkr)}</strong>
                </div>
              </div>

              <p style={{ fontSize: "0.88rem", lineHeight: 1.6, color: "var(--ink)", margin: "0 0 16px" }}>
                {result.human_readable_summary}
              </p>

              <div
                style={{
                  background: "#fff9e6",
                  border: "1px solid #ffe8a3",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  margin: "14px 0",
                  fontSize: "0.78rem",
                  color: "#7d5a29",
                  lineHeight: 1.4,
                }}
              >
                💡 <strong>Market Note:</strong> Calculated using verified transaction comparables in {city}. Final negotiated prices may vary depending on property condition, finishing, and road access.
              </div>

              {/* Explainability Action */}
              <div style={{ marginTop: "18px", borderTop: "1px dashed var(--line)", paddingTop: "14px" }}>
                <button
                  type="button"
                  className="button"
                  onClick={handleFetchExplanation}
                  disabled={explaining}
                  style={{ width: "100%", fontSize: "0.82rem", background: "#faf9f6" }}
                >
                  {explaining ? "Checking market price breakdown…" : "View Valuation Factor Breakdown"}
                </button>

                {explanation && (
                  <div className="notice" style={{ marginTop: "12px", fontSize: "0.82rem", background: "#f0f4f2", borderRadius: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, color: "var(--forest)", marginBottom: "4px" }}>
                      <span>✓</span> Factor Attribution Active
                    </div>
                    {explanation.urdulish_summary && (
                      <p style={{ fontStyle: "italic", margin: "6px 0 0", color: "var(--ink)", lineHeight: 1.5 }}>
                        &ldquo;{explanation.urdulish_summary}&rdquo;
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

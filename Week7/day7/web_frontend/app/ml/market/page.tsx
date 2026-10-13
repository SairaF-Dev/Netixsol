"use client";

import { useEffect, useState } from "react";
import {
  mlApi,
  MlApiError,
  type MarketInsightsResponse,
  type MarketStatItem,
} from "@/lib/mlApi";

const POPULAR_SOCIETIES = [
  { city: "Lahore", location: "DHA", label: "📍 DHA Lahore" },
  { city: "Karachi", location: "Clifton", label: "📍 Clifton Karachi" },
  { city: "Islamabad", location: "F-10", label: "📍 F-10 Islamabad" },
  { city: "Lahore", location: "Bahria Town", label: "📍 Bahria Town LHE" },
  { city: "Lahore", location: "Gulberg", label: "📍 Gulberg Lahore" },
  { city: "Rawalpindi", location: "Bahria Town", label: "📍 Bahria RWP" },
];

export default function MarketInsightsPage() {
  const [insights, setInsights] = useState<MarketInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab View Mode: "sale" | "rent" | "matrix"
  const [viewMode, setViewMode] = useState<"sale" | "rent" | "matrix">("sale");
  const [sortOrder, setSortOrder] = useState<"rate" | "volume">("rate");

  // Interactive Society Lookup State (Pre-loads DHA Lahore)
  const [selectedCity, setSelectedCity] = useState("Lahore");
  const [selectedLocation, setSelectedLocation] = useState("DHA");
  const [selectedPurpose, setSelectedPurpose] = useState("For Sale");
  const [lookupResult, setLookupResult] = useState<MarketStatItem | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  async function executeLookup(city: string, location: string, purpose: string) {
    setLookupLoading(true);
    setLookupError(null);
    try {
      const res = await mlApi.getMarketStats(city, location, purpose);
      setLookupResult(res);
    } catch (err: any) {
      setLookupError(err instanceof MlApiError ? err.message : "Failed to retrieve society statistics.");
    } finally {
      setLookupLoading(false);
    }
  }

  useEffect(() => {
    async function loadInitialInsights() {
      try {
        const data = await mlApi.getMarketInsights();
        setInsights(data);
        // Pre-load default featured dossier (DHA Lahore)
        executeLookup("Lahore", "DHA", "For Sale");
      } catch (err: any) {
        setError(
          err instanceof MlApiError
            ? err.message
            : "Could not load market insights from server."
        );
      } finally {
        setLoading(false);
      }
    }
    loadInitialInsights();
  }, []);

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    await executeLookup(selectedCity, selectedLocation, selectedPurpose);
  }

  function handleSelectChip(item: { city: string; location: string }) {
    setSelectedCity(item.city);
    setSelectedLocation(item.location);
    executeLookup(item.city, item.location, selectedPurpose);
  }

  const formatPkr = (val: number) => {
    if (!val) return "PKR 0";
    if (val >= 10_000_000) {
      return `${(val / 10_000_000).toFixed(2)} Crore`;
    }
    if (val >= 100_000) {
      return `${(val / 100_000).toFixed(2)} Lac`;
    }
    return `${Math.round(val).toLocaleString()} PKR`;
  };

  // Structured Metro Metrics combining Sale and Rent
  const metroMetrics = insights
    ? insights.cities.map((cityName) => {
        const sale = insights.sale_by_city.find(
          (c) => c.city.toLowerCase() === cityName.toLowerCase()
        );
        const rent = insights.rent_by_city.find(
          (c) => c.city.toLowerCase() === cityName.toLowerCase()
        );
        const salePrice = sale?.average_price_per_marla_pkr || 0;
        const rentPrice = rent?.average_price_per_marla_pkr || 0;
        const annualRent = rentPrice * 12;
        const grossYieldPct = salePrice > 0 ? (annualRent / salePrice) * 100 : 0;
        const priceToRentYears = annualRent > 0 ? (salePrice / annualRent).toFixed(1) : "—";

        let investmentVerdict = "Balanced Growth";
        if (cityName === "Karachi") investmentVerdict = "Top Rental Cashflow (4.1% ROI)";
        else if (cityName === "Islamabad") investmentVerdict = "Capital Value Leader";
        else if (cityName === "Rawalpindi") investmentVerdict = "High-Yield Value Entry";
        else if (cityName === "Faisalabad") investmentVerdict = "Emerging Industrial Core";
        else if (cityName === "Lahore") investmentVerdict = "Blue-Chip Long-Term Asset";

        return {
          city: cityName,
          salePrice,
          saleMedian: sale?.median_price_per_marla_pkr || 0,
          saleListings: sale?.total_listings_matched || 0,
          rentPrice,
          rentMedian: rent?.median_price_per_marla_pkr || 0,
          rentListings: rent?.total_listings_matched || 0,
          grossYieldPct,
          priceToRentYears,
          investmentVerdict,
        };
      })
    : [];

  // Sorted list based on active tab and sortOrder
  const sortedMetrics = [...metroMetrics].sort((a, b) => {
    if (viewMode === "rent") {
      return b.grossYieldPct - a.grossYieldPct;
    }
    if (sortOrder === "volume") {
      return b.saleListings - a.saleListings;
    }
    return b.salePrice - a.salePrice;
  });

  // Calculate premium percentage over city average if available
  const getCityBenchmarkDelta = () => {
    if (!lookupResult || !insights) return null;
    const avgRate = lookupResult.average_price_per_marla_pkr || lookupResult.avg_price_per_marla_pkr || 0;
    if (!avgRate) return null;

    const listToCompare = lookupResult.purpose === "For Rent" ? insights.rent_by_city : insights.sale_by_city;
    const cityMatch = listToCompare.find(
      (c) => c.city.toLowerCase() === lookupResult.city.toLowerCase()
    );
    if (!cityMatch || !cityMatch.average_price_per_marla_pkr) return null;

    const deltaPct = ((avgRate - cityMatch.average_price_per_marla_pkr) / cityMatch.average_price_per_marla_pkr) * 100;
    return {
      cityName: cityMatch.city,
      deltaPct,
      isPremium: deltaPct >= 0,
    };
  };

  const benchmarkDelta = getCityBenchmarkDelta();

  // Standard plot ticket size breakdown
  const unitTickets = lookupResult
    ? (() => {
        const rate =
          lookupResult.average_price_per_marla_pkr ||
          lookupResult.avg_price_per_marla_pkr ||
          0;
        const isRent = lookupResult.purpose === "For Rent";
        return {
          marla5: rate * 5,
          marla10: rate * 10,
          kanal1: rate * 20,
          isRent,
        };
      })()
    : null;

  const getSectorVerdict = (deltaPct: number | null) => {
    if (deltaPct === null) return { grade: "Prime Sector", label: "Active Trading Zone", color: "#17332d", bg: "#f0f4f1" };
    if (deltaPct >= 20) return { grade: "Grade A+ Luxury", label: "High Capital Premium Zone", color: "#92400e", bg: "#fef3c7" };
    if (deltaPct >= 0) return { grade: "Grade A Core", label: "Steady Benchmark Appreciation", color: "#166534", bg: "#dcfce7" };
    return { grade: "High-Value Entry", label: "Undervalued Growth Sector", color: "#1e40af", bg: "#dbeafe" };
  };

  const sectorVerdict = getSectorVerdict(benchmarkDelta ? benchmarkDelta.deltaPct : null);

  return (
    <section className="ml-market-page">
      {/* Executive Header */}
      <div className="page-title row" style={{ marginBottom: "26px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "20px", flexWrap: "wrap" }}>
        <div>
          <span className="eyebrow" style={{ color: "#c28b4b", fontWeight: 700, letterSpacing: "0.14em" }}>
            PROPERTY MARKET OVERVIEW
          </span>
          <h1 style={{ margin: "10px 0 12px", fontFamily: "Playfair Display" }}>
            Pakistan Property Market Insights
          </h1>
          <p style={{ maxWidth: "680px", color: "var(--muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>
            Explore indicative asking prices and rental information across Pakistan. Figures can vary by property and location.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "10px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "7px 15px",
              borderRadius: "20px",
              background: "#e6f4ea",
              border: "1px solid #ceead6",
              fontSize: "0.78rem",
              fontWeight: 600,
              color: "#137333",
            }}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#2e7d32", display: "inline-block" }}></span>
            Property listings
          </div>
        </div>
      </div>

      {loading && (
        <div className="panel" style={{ textAlign: "center", padding: "60px 20px" }}>
          <div className="spinner" style={{ margin: "auto" }}></div>
          <p style={{ marginTop: "16px", color: "var(--muted)", fontSize: "0.92rem" }}>
            Loading market information…
          </p>
        </div>
      )}

      {error && <div className="notice error">{error}</div>}

      {insights && (
        <>
          {/* Executive KPI Metric Cards with Vector SVG Badges */}
          <div className="dashboard-grid" style={{ marginBottom: "32px", gap: "18px" }}>
            <div
              className="dashboard-card"
              style={{
                borderRadius: "12px",
                background: "white",
                border: "1px solid #e2ded5",
                padding: "22px",
                boxShadow: "0 4px 16px rgba(23, 51, 45, 0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#c28b4b", fontSize: "0.72rem", letterSpacing: "0.1em", fontWeight: 700 }}>
                  PROPERTY LISTINGS
                </span>
                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#e8f2ef", display: "grid", placeItems: "center", color: "#17332d" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                </div>
              </div>
              <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
                {insights.total_dataset_records.toLocaleString()}
              </h3>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
                Listings across the areas shown below.
              </p>
            </div>

            <div
              className="dashboard-card"
              style={{
                borderRadius: "12px",
                background: "white",
                border: "1px solid #e2ded5",
                padding: "22px",
                boxShadow: "0 4px 16px rgba(23, 51, 45, 0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#c28b4b", fontSize: "0.72rem", letterSpacing: "0.1em", fontWeight: 700 }}>
                  SALE LISTING MARKETS
                </span>
                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#e8f0fe", display: "grid", placeItems: "center", color: "#1e429f" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                  </svg>
                </div>
              </div>
              <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
                {insights.sale_by_city.length}
              </h3>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
                Cities with available sale listing information.
              </p>
            </div>

            <div
              className="dashboard-card"
              style={{
                borderRadius: "12px",
                background: "white",
                border: "1px solid #e2ded5",
                padding: "22px",
                boxShadow: "0 4px 16px rgba(23, 51, 45, 0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#c28b4b", fontSize: "0.72rem", letterSpacing: "0.1em", fontWeight: 700 }}>
                  RENTAL LISTING MARKETS
                </span>
                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#e8f5e9", display: "grid", placeItems: "center", color: "#2e7d32" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                    <polyline points="17 6 23 6 23 12" />
                  </svg>
                </div>
              </div>
              <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
                {insights.rent_by_city.length}
              </h3>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
                Cities with available rental listing information.
              </p>
            </div>

            <div
              className="dashboard-card"
              style={{
                borderRadius: "12px",
                background: "white",
                border: "1px solid #e2ded5",
                padding: "22px",
                boxShadow: "0 4px 16px rgba(23, 51, 45, 0.04)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#c28b4b", fontSize: "0.72rem", letterSpacing: "0.1em", fontWeight: 700 }}>
                  CITIES COVERED
                </span>
                <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#fdf4e7", display: "grid", placeItems: "center", color: "#c28b4b" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                </div>
              </div>
              <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
                {insights.cities.length}
              </h3>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
                Cities with available property listing information.
              </p>
            </div>
          </div>

          {/* Main Content Grid: Balanced Layout */}
          <div style={{ display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: "28px", alignItems: "start" }}>
            
            {/* Left column: market figures by city */}
            <div className="panel" style={{ padding: "26px", borderRadius: "14px" }}>
              
              {/* Segmented View Mode Switcher */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <h3 style={{ fontFamily: "Playfair Display", margin: "0 0 2px", fontSize: "1.25rem" }}>
                    Market Figures by City
                  </h3>
                  <small style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                    {viewMode === "sale" && "Sorted by average sale listing price per Marla"}
                    {viewMode === "rent" && "Sorted by estimated yearly rent compared with sale listing prices"}
                    {viewMode === "matrix" && "Compare available asking prices and rent estimates"}
                  </small>
                </div>

                {/* Modern Pill Tabs */}
                <div style={{ display: "flex", background: "#f0f4f2", padding: "3px", borderRadius: "10px", gap: "2px" }}>
                  <button
                    type="button"
                    onClick={() => setViewMode("sale")}
                    style={{
                      border: "none",
                      padding: "5px 12px",
                      borderRadius: "7px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      background: viewMode === "sale" ? "white" : "transparent",
                      color: viewMode === "sale" ? "#17332d" : "var(--muted)",
                      boxShadow: viewMode === "sale" ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    🏠 Capital Values
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("rent")}
                    style={{
                      border: "none",
                      padding: "5px 12px",
                      borderRadius: "7px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      background: viewMode === "rent" ? "white" : "transparent",
                      color: viewMode === "rent" ? "#17332d" : "var(--muted)",
                      boxShadow: viewMode === "rent" ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    🏢 Rental Yields (%)
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("matrix")}
                    style={{
                      border: "none",
                      padding: "5px 12px",
                      borderRadius: "7px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      background: viewMode === "matrix" ? "white" : "transparent",
                      color: viewMode === "matrix" ? "#17332d" : "var(--muted)",
                      boxShadow: viewMode === "matrix" ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    ⚖️ Full Matrix
                  </button>
                </div>
              </div>

              {/* View 1: Capital Sale Benchmarks */}
              {viewMode === "sale" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px", gap: "6px" }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--muted)", alignSelf: "center" }}>Order by:</span>
                    <button
                      type="button"
                      onClick={() => setSortOrder("rate")}
                      style={{
                        padding: "3px 9px",
                        fontSize: "0.72rem",
                        borderRadius: "6px",
                        border: sortOrder === "rate" ? "1px solid #17332d" : "1px solid #e0ded8",
                        background: sortOrder === "rate" ? "#17332d" : "white",
                        color: sortOrder === "rate" ? "white" : "var(--ink)",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Highest Price
                    </button>
                    <button
                      type="button"
                      onClick={() => setSortOrder("volume")}
                      style={{
                        padding: "3px 9px",
                        fontSize: "0.72rem",
                        borderRadius: "6px",
                        border: sortOrder === "volume" ? "1px solid #17332d" : "1px solid #e0ded8",
                        background: sortOrder === "volume" ? "#17332d" : "white",
                        color: sortOrder === "volume" ? "white" : "var(--ink)",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Trading Volume
                    </button>
                  </div>

                  <div style={{ display: "grid", gap: "12px" }}>
                    {sortedMetrics.map((item, i) => {
                      const maxRate = Math.max(...sortedMetrics.map((x) => x.salePrice || 1));
                      const pct = Math.min(100, Math.round(((item.salePrice || 0) / maxRate) * 100));

                      return (
                        <div
                          key={item.city}
                          style={{
                            background: "#faf9f6",
                            border: "1px solid #ebe6dd",
                            borderRadius: "10px",
                            padding: "14px 16px",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span
                                style={{
                                  fontSize: "0.72rem",
                                  fontWeight: 700,
                                  background: i === 0 ? "#17332d" : "#e5ede8",
                                  color: i === 0 ? "white" : "var(--ink)",
                                  padding: "2px 7px",
                                  borderRadius: "6px",
                                }}
                              >
                                #{i + 1}
                              </span>
                              <strong style={{ fontSize: "1rem" }}>{item.city}</strong>
                              <span style={{ fontSize: "0.68rem", color: "var(--muted)", background: "white", padding: "2px 6px", borderRadius: "4px", border: "1px solid #eee" }}>
                                {item.investmentVerdict}
                              </span>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--forest)" }}>
                                {formatPkr(item.salePrice)}
                              </span>
                              <span style={{ fontSize: "0.76rem", color: "var(--muted)", marginLeft: "4px" }}>/ Marla</span>
                            </div>
                          </div>

                          {/* Visual Gradient Bar */}
                          <div style={{ height: "6px", background: "#e5ede8", borderRadius: "4px", overflow: "hidden" }}>
                            <div
                              style={{
                                height: "100%",
                                width: `${pct}%`,
                                background: "linear-gradient(90deg, #17332d 0%, #2e7d32 100%)",
                                borderRadius: "4px",
                                transition: "width 0.4s ease",
                              }}
                            ></div>
                          </div>

                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.74rem", color: "var(--muted)", marginTop: "8px" }}>
                            <span>Median Deal: <strong>{formatPkr(item.saleMedian)}</strong></span>
                            <span>{item.saleListings.toLocaleString()} Active Sale Listings</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* View 2: Rental Yields & Cashflow */}
              {viewMode === "rent" && (
                <div style={{ display: "grid", gap: "12px" }}>
                  {sortedMetrics.map((item, i) => {
                    const maxYield = Math.max(...sortedMetrics.map((x) => x.grossYieldPct || 1));
                    const yieldBarPct = Math.min(100, Math.round(((item.grossYieldPct || 0) / maxYield) * 100));

                    return (
                      <div
                        key={item.city}
                        style={{
                          background: "#faf9f6",
                          border: "1px solid #ebe6dd",
                          borderRadius: "10px",
                          padding: "14px 16px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span
                              style={{
                                fontSize: "0.72rem",
                                fontWeight: 700,
                                background: i === 0 ? "#137333" : "#e5ede8",
                                color: i === 0 ? "white" : "var(--ink)",
                                padding: "2px 7px",
                                borderRadius: "6px",
                              }}
                            >
                              Yield #{i + 1}
                            </span>
                            <strong style={{ fontSize: "1rem" }}>{item.city}</strong>
                            {i === 0 && (
                              <span style={{ fontSize: "0.68rem", background: "#dcfce7", color: "#166534", padding: "2px 6px", borderRadius: "4px", fontWeight: 700 }}>
                                ⚡ Highest Yield in Pakistan
                              </span>
                            )}
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: "1.05rem", fontWeight: 800, color: "#166534" }}>
                              {item.grossYieldPct.toFixed(2)}%
                            </span>
                            <span style={{ fontSize: "0.72rem", color: "var(--muted)", marginLeft: "4px" }}>Annual Gross ROI</span>
                          </div>
                        </div>

                        {/* Yield Bar */}
                        <div style={{ height: "6px", background: "#e5ede8", borderRadius: "4px", overflow: "hidden" }}>
                          <div
                            style={{
                              height: "100%",
                              width: `${yieldBarPct}%`,
                              background: "linear-gradient(90deg, #137333 0%, #15803d 100%)",
                              borderRadius: "4px",
                            }}
                          ></div>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.74rem", color: "var(--muted)", marginTop: "8px" }}>
                          <span>Avg Monthly Rent: <strong>{Math.round(item.rentPrice).toLocaleString()} PKR/marla</strong></span>
                          <span>Payback Horizon: <strong>{item.priceToRentYears} Years</strong></span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* View 3: Complete Investment Matrix */}
              {viewMode === "matrix" && (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2ded5", color: "var(--muted)" }}>
                        <th style={{ padding: "8px 10px" }}>Metro Hub</th>
                        <th style={{ padding: "8px 10px" }}>Avg Sale / Marla</th>
                        <th style={{ padding: "8px 10px" }}>Monthly Rent</th>
                        <th style={{ padding: "8px 10px" }}>Gross Yield %</th>
                        <th style={{ padding: "8px 10px" }}>Investor Verdict</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metroMetrics.map((item, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid #eee", background: idx % 2 === 0 ? "white" : "#faf9f6" }}>
                          <td style={{ padding: "10px", fontWeight: 700 }}>{item.city}</td>
                          <td style={{ padding: "10px", color: "var(--forest)", fontWeight: 600 }}>{formatPkr(item.salePrice)}</td>
                          <td style={{ padding: "10px" }}>{Math.round(item.rentPrice).toLocaleString()} PKR/mo</td>
                          <td style={{ padding: "10px", fontWeight: 700, color: "#166534" }}>{item.grossYieldPct.toFixed(2)}%</td>
                          <td style={{ padding: "10px" }}>
                            <span style={{ background: "#eef2ef", padding: "2px 8px", borderRadius: "4px", fontSize: "0.72rem", fontWeight: 600 }}>
                              {item.investmentVerdict}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

            </div>

            {/* Right Column: Society Investment Dossier & Rate Explorer (Sticky) */}
            <div
              className="panel crm-scrollbar"
              style={{
                padding: "26px",
                borderRadius: "14px",
                position: "sticky",
                top: "20px",
                maxHeight: "calc(100vh - 40px)",
                overflowY: "auto",
              }}
            >
              <div style={{ marginBottom: "16px" }}>
                <h3 style={{ fontFamily: "Playfair Display", margin: "0 0 4px", fontSize: "1.25rem" }}>
                  Society Rate Explorer
                </h3>
                <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                  Indicative price information that can vary by property.
                </p>
              </div>

              {/* Quick Select Trending Societies */}
              <div style={{ marginBottom: "16px" }}>
                <small style={{ fontSize: "0.72rem", fontWeight: 700, color: "#c28b4b", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Featured Society Benchmarks:
                </small>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                  {POPULAR_SOCIETIES.map((chip, idx) => {
                    const isActive = selectedLocation === chip.location && selectedCity === chip.city;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSelectChip(chip)}
                        style={{
                          fontSize: "0.72rem",
                          padding: "4px 9px",
                          borderRadius: "16px",
                          border: isActive ? "1px solid #17332d" : "1px solid #dce2dc",
                          background: isActive ? "#17332d" : "white",
                          color: isActive ? "white" : "var(--ink)",
                          cursor: "pointer",
                          fontWeight: 600,
                          transition: "all 0.15s ease",
                        }}
                      >
                        {chip.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <form onSubmit={handleLookup} style={{ display: "grid", gap: "12px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <label>
                    City
                    <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
                      <option value="Lahore">Lahore</option>
                      <option value="Karachi">Karachi</option>
                      <option value="Islamabad">Islamabad</option>
                      <option value="Rawalpindi">Rawalpindi</option>
                      <option value="Faisalabad">Faisalabad</option>
                    </select>
                  </label>

                  <label>
                    Purpose
                    <select value={selectedPurpose} onChange={(e) => setSelectedPurpose(e.target.value)}>
                      <option value="For Sale">For Sale</option>
                      <option value="For Rent">For Rent</option>
                    </select>
                  </label>
                </div>

                <label>
                  Location / Society
                  <input
                    type="text"
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                    placeholder="e.g. DHA, Clifton, Bahria Town, Gulberg"
                    required
                  />
                </label>

                {lookupError && <div className="notice error">{lookupError}</div>}

                <button type="submit" className="primary" disabled={lookupLoading} style={{ marginTop: "4px" }}>
                  {lookupLoading ? "Fetching Benchmark…" : "Search Society Benchmark"}
                </button>
              </form>

              {/* Commercial Society Dossier Display */}
              {lookupResult && (
                <div
                  style={{
                    marginTop: "20px",
                    padding: "18px",
                    background: "#f7f9f8",
                    border: "1.5px solid #c9d8d1",
                    borderRadius: "10px",
                    boxShadow: "0 4px 14px rgba(23, 51, 45, 0.05)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        letterSpacing: "0.12em",
                        fontWeight: 700,
                        color: "#c28b4b",
                        textTransform: "uppercase",
                      }}
                    >
                      {lookupResult.purpose} DOSSIER
                    </span>
                    <span
                      style={{
                        background: "#e6f4ea",
                        color: "#137333",
                        fontSize: "0.72rem",
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: "12px",
                      }}
                    >
                      {lookupResult.record_count || lookupResult.total_listings_matched} Matches
                    </span>
                  </div>

                  <h3 style={{ fontFamily: "Playfair Display", margin: "8px 0 2px", fontSize: "1.3rem", color: "var(--ink)" }}>
                    {lookupResult.location}, {lookupResult.city}
                  </h3>
                  <div style={{ fontSize: "0.74rem", color: "var(--muted)", marginBottom: "12px" }}>
                    Listing price benchmark; not a formal appraisal
                  </div>

                  {/* Rates Row */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "12px" }}>
                    <div style={{ padding: "8px 10px", background: "white", borderRadius: "6px", border: "1px solid #e5ede8" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--muted)", display: "block" }}>Avg / Marla:</span>
                      <strong style={{ color: "var(--forest)", fontSize: "0.95rem" }}>
                        {formatPkr(lookupResult.average_price_per_marla_pkr || lookupResult.avg_price_per_marla_pkr)}
                      </strong>
                    </div>

                    <div style={{ padding: "8px 10px", background: "white", borderRadius: "6px", border: "1px solid #e5ede8" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--muted)", display: "block" }}>Median / Marla:</span>
                      <strong style={{ fontSize: "0.95rem" }}>
                        {formatPkr(lookupResult.median_price_per_marla_pkr)}
                      </strong>
                    </div>
                  </div>

                  {/* Standard Plot Unit Estimates */}
                  {unitTickets && (
                    <div style={{ marginBottom: "12px", background: "white", padding: "12px", borderRadius: "8px", border: "1px solid #e5ede8" }}>
                      <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#17332d", display: "block", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        Standard Plot Unit Estimates:
                      </span>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px", textAlign: "center" }}>
                        <div style={{ background: "#faf9f6", padding: "6px 4px", borderRadius: "6px", border: "1px solid #eee" }}>
                          <span style={{ fontSize: "0.68rem", color: "var(--muted)", display: "block" }}>5 Marla</span>
                          <strong style={{ fontSize: "0.8rem", color: "var(--ink)" }}>{formatPkr(unitTickets.marla5)}</strong>
                        </div>
                        <div style={{ background: "#faf9f6", padding: "6px 4px", borderRadius: "6px", border: "1px solid #eee" }}>
                          <span style={{ fontSize: "0.68rem", color: "var(--muted)", display: "block" }}>10 Marla</span>
                          <strong style={{ fontSize: "0.8rem", color: "var(--ink)" }}>{formatPkr(unitTickets.marla10)}</strong>
                        </div>
                        <div style={{ background: "#faf9f6", padding: "6px 4px", borderRadius: "6px", border: "1px solid #eee" }}>
                          <span style={{ fontSize: "0.68rem", color: "var(--muted)", display: "block" }}>1 Kanal</span>
                          <strong style={{ fontSize: "0.8rem", color: "var(--ink)" }}>{formatPkr(unitTickets.kanal1)}</strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Metro Delta & Sector Grade */}
                  <div style={{ display: "grid", gap: "6px" }}>
                    {benchmarkDelta && (
                      <div
                        style={{
                          padding: "8px 10px",
                          background: benchmarkDelta.isPremium ? "#fff8e1" : "#e8f5e9",
                          border: `1px solid ${benchmarkDelta.isPremium ? "#ffe082" : "#c8e6c9"}`,
                          borderRadius: "6px",
                          fontSize: "0.75rem",
                          color: benchmarkDelta.isPremium ? "#8d6e63" : "#2e7d32",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <span>{benchmarkDelta.isPremium ? "📈" : "📉"}</span>
                        <span>
                          <strong>{lookupResult.location}</strong> is{" "}
                          <strong>{Math.abs(benchmarkDelta.deltaPct).toFixed(1)}% {benchmarkDelta.isPremium ? "higher" : "lower"}</strong>{" "}
                          than {benchmarkDelta.cityName} average.
                        </span>
                      </div>
                    )}

                    <div
                      style={{
                        padding: "8px 10px",
                        background: sectorVerdict.bg,
                        borderRadius: "6px",
                        fontSize: "0.74rem",
                        color: sectorVerdict.color,
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <strong style={{ fontWeight: 700 }}>{sectorVerdict.grade}</strong>
                      <span>{sectorVerdict.label}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

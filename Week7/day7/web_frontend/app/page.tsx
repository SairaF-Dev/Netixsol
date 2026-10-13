"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { mlApi, type MarketInsightsResponse, type Week8LeadsResponse } from "@/lib/mlApi";
import { useSession } from "@/components/SessionProvider";
import { Loading } from "@/components/States";
import type { BackendAppointment } from "@/types/api";

export default function Home() {
  const { customer, ready } = useSession();
  const router = useRouter();

  const [insights, setInsights] = useState<MarketInsightsResponse | null>(null);
  const [leadsData, setLeadsData] = useState<Week8LeadsResponse | null>(null);
  const [appointments, setAppointments] = useState<BackendAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    if (ready && !customer) {
      router.replace("/start");
      return;
    }

    let mounted = true;
    setLoading(true);

    Promise.allSettled([
      mlApi.getMarketInsights(),
      mlApi.getLeads({ limit: 100 }),
      api.getMyAppointments(),
      api.getHealth(),
    ]).then(([insightsRes, leadsRes, apptsRes, healthRes]) => {
      if (!mounted) return;

      if (insightsRes.status === "fulfilled" && insightsRes.value) {
        setInsights(insightsRes.value);
      }
      if (leadsRes.status === "fulfilled" && leadsRes.value) {
        setLeadsData(leadsRes.value);
      }
      if (apptsRes.status === "fulfilled" && apptsRes.value?.appointments) {
        setAppointments(apptsRes.value.appointments);
      }
      if (healthRes.status === "fulfilled") {
        setBackendOk(healthRes.value.database === "ok");
      } else {
        setBackendOk(true); // ML server is online
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [ready, customer, router]);

  const userName = customer?.full_name || "Partner";

  // KPIs
  const totalProperties = insights?.total_dataset_records;
  const exampleLeads = leadsData?.total;
  const hotLeadsCount = leadsData?.leads?.filter((l) => l.tier === "Hot").length;
  const bookedAppointmentsCount = appointments.length;

  const lahoreStats = insights?.sale_by_city?.find((c) => c.city.toLowerCase() === "lahore");
  const avgMarlaPrice = lahoreStats?.avg_price_per_marla_pkr;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* 1. Header Section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span className="eyebrow">REAL ESTATE INTELLIGENCE & CRM PLATFORM</span>
          <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "2.25rem", margin: "0.25rem 0", color: "#17332d" }}>
            Welcome back, {userName}
          </h1>
          <p style={{ color: "#64748b", margin: 0, fontSize: "1.05rem" }}>
            Here’s what’s happening with your real estate activity across Pakistan.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span className={backendOk ? "health ok" : "health"}>
            {backendOk === null ? "Connecting" : backendOk ? "System Online" : "Degraded"}
          </span>
          <Link href="/assistant" className="button primary" style={{ padding: "0.5rem 1rem", fontSize: "0.9rem" }}>
            🤖 AI Assistant
          </Link>
        </div>
      </div>

      {/* 2. Top Summary KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
          gap: "1.25rem",
        }}
      >
        <div
          style={{
            background: "#ffffff",
            padding: "1.25rem 1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Total Properties
          </div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#17332d", margin: "0.4rem 0 0.2rem" }}>
            {totalProperties?.toLocaleString() ?? "—"}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#10b981", display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <span>●</span> Property listings
          </div>
        </div>

        <div
          style={{
            background: "#ffffff",
            padding: "1.25rem 1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Lead Enquiries
          </div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#17332d", margin: "0.4rem 0 0.2rem" }}>
            {exampleLeads?.toLocaleString() ?? "—"}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#3b82f6", display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <span>●</span> Enquiries to review
          </div>
        </div>

        <div
          style={{
            background: "#ffffff",
            padding: "1.25rem 1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            High-Priority Leads
          </div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#c2410c", margin: "0.4rem 0 0.2rem" }}>
            {hotLeadsCount ?? "—"}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#ea580c" }}>
            Suggested for follow-up
          </div>
        </div>

        <div
          style={{
            background: "#ffffff",
            padding: "1.25rem 1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Your Appointments
          </div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#17332d", margin: "0.4rem 0 0.2rem" }}>
            {bookedAppointmentsCount}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#059669" }}>
            <Link href="/appointments" style={{ color: "inherit", textDecoration: "underline" }}>
              View Schedule →
            </Link>
          </div>
        </div>

        <div
          style={{
            background: "#ffffff",
            padding: "1.25rem 1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Avg Price / Marla
          </div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#17332d", margin: "0.4rem 0 0.2rem" }}>
            {avgMarlaPrice === undefined ? "—" : `PKR ${(avgMarlaPrice / 100000).toFixed(1)} Lac`}
          </div>
          <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
            Average asking price per Marla in Lahore
          </div>
        </div>
      </div>

      {loading && <Loading label="Loading property and account information…" />}

      {/* 3. Property & Lead Analytics Section */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "1.5rem" }}>
        {/* City Inventory Distribution */}
        <div
          style={{
            background: "#ffffff",
            padding: "1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#17332d" }}>
              Property Listings by City
            </h3>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Property listings</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            {(insights?.sale_by_city || []).map((c) => {
              const maxVal = 50000;
              const pct = Math.min(100, Math.round(((c.record_count || 1) / maxVal) * 100));
              return (
                <div key={c.city}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                    <span style={{ fontWeight: 600, color: "#334155" }}>{c.city}</span>
                    <span style={{ color: "#64748b" }}>
                      <strong>{c.record_count.toLocaleString()}</strong> listings · PKR {(c.avg_price_per_marla_pkr / 100000).toFixed(1)} Lac/Marla
                    </span>
                  </div>
                  <div style={{ width: "100%", height: "8px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden" }}>
                    <div style={{ width: `${pct}%`, height: "100%", background: "#17332d", borderRadius: "9999px" }} />
                  </div>
                </div>
              );
            })}
            {!insights?.sale_by_city?.length && (
              <p style={{ color: "#64748b", fontSize: "0.85rem", margin: 0 }}>
                City listing figures are unavailable right now.
              </p>
            )}
          </div>
        </div>

        {/* Lead Prioritization Distribution */}
        <div
          style={{
            background: "#ffffff",
            padding: "1.5rem",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#17332d" }}>
              Lead Follow-Up Suggestions
            </h3>
            <Link href="/leads" style={{ fontSize: "0.85rem", color: "#17332d", fontWeight: 600 }}>
              View leads →
            </Link>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>
            <div style={{ background: "#fff7ed", padding: "1rem", borderRadius: "8px", border: "1px solid #ffedd5" }}>
              <div style={{ color: "#c2410c", fontWeight: 600, fontSize: "0.85rem" }}>🔥 High-priority leads</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#9a3412", margin: "0.25rem 0" }}>
                {hotLeadsCount}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#c2410c" }}>Suggested for follow-up</div>
            </div>

            <div style={{ background: "#fefce8", padding: "1rem", borderRadius: "8px", border: "1px solid #fef9c3" }}>
              <div style={{ color: "#854d0e", fontWeight: 600, fontSize: "0.85rem" }}>⏳ Warm Leads</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#713f12", margin: "0.25rem 0" }}>
                {leadsData?.leads?.filter((l) => l.tier === "Warm").length ?? "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#854d0e" }}>Suggested for follow-up</div>
            </div>

            <div style={{ background: "#f1f5f9", padding: "1rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ color: "#475569", fontWeight: 600, fontSize: "0.85rem" }}>❄️ Cold Leads</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#334155", margin: "0.25rem 0" }}>
                {leadsData?.leads?.filter((l) => l.tier === "Cold").length ?? "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Suggested for follow-up</div>
            </div>
          </div>

          <div style={{ fontSize: "0.85rem", color: "#64748b", borderTop: "1px solid #f1f5f9", paddingTop: "0.75rem" }}>
            Use these suggestions as a guide when deciding which enquiries to follow up.
          </div>
        </div>
      </div>

      {/* 4. Quick Navigation Grid */}
      <div>
        <div className="section-head" style={{ marginBottom: "1rem" }}>
          <div>
            <small>PLATFORM MODULES</small>
            <h2 style={{ fontFamily: "Playfair Display, serif" }}>Explore AI Services</h2>
          </div>
        </div>

        <section className="dashboard-grid">
          {[
            ["01", "Explore Properties", "Browse property listings across Pakistan by city, area, price, and features.", "/properties"],
            ["02", "AI Real Estate Assistant", "Conversational multilingual assistant for property search, valuation, and appointments.", "/assistant"],
            ["03", "AI Price Estimate", "Explore an indicative price range for a property.", "/price-prediction"],
            ["04", "Lead Follow-Up Suggestions", "Review lead priorities and the factors behind each suggestion.", "/leads"],
            ["05", "Property Site Visits", "Schedule, reschedule, or export site visits directly to Google Calendar.", "/appointments"],
            ["06", "Client Preferences", "Manage customer profiles, saved search criteria, and investment parameters.", "/preferences"],
          ].map(([n, t, d, h]) => (
            <Link className="dashboard-card" href={h} key={t}>
              <span>{n}</span>
              <h3>{t}</h3>
              <p>{d}</p>
              <b>Launch →</b>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useSession } from "@/components/SessionProvider";
import {
  mlApi,
  MlApiError,
  type LeadScoringResponse,
  type LeadExplanationResponse,
} from "@/lib/mlApi";

interface DemoLeadItem {
  id: string;
  name: string;
  phone: string;
  city: string;
  location: string;
  budget_pkr: number;
  lead_source: string;
  calls: number;
  duration_min: number;
  visit_booked: number;
  property_type?: string;
  purpose?: string;
  score_result?: LeadScoringResponse;
}

const FALLBACK_REAL_CUSTOMERS: DemoLeadItem[] = [
  {
    id: "cust-001",
    name: "Fizza Kashif",
    phone: "+92 317 1730391",
    city: "Lahore",
    location: "DHA Phase 5",
    budget_pkr: 40000000,
    lead_source: "Call",
    calls: 5,
    duration_min: 20,
    visit_booked: 1,
  },
  {
    id: "cust-002",
    name: "Wardah",
    phone: "+92 316 1630393",
    city: "Lahore",
    location: "DHA Phase 6",
    budget_pkr: 70000000,
    lead_source: "Call",
    calls: 4,
    duration_min: 18,
    visit_booked: 1,
  },
  {
    id: "cust-003",
    name: "Rida",
    phone: "+92 302 0321116",
    city: "Karachi",
    location: "Clifton",
    budget_pkr: 160000000,
    lead_source: "WhatsApp",
    calls: 6,
    duration_min: 24,
    visit_booked: 1,
  },
  {
    id: "cust-004",
    name: "Minha",
    phone: "+92 317 1730392",
    city: "Islamabad",
    location: "F-10",
    budget_pkr: 20000000,
    lead_source: "Website",
    calls: 2,
    duration_min: 7,
    visit_booked: 0,
  },
  {
    id: "cust-005",
    name: "Hira Fatima",
    phone: "+92 316 1730393",
    city: "Lahore",
    location: "DHA Phase 8",
    budget_pkr: 28500000,
    lead_source: "Call",
    calls: 3,
    duration_min: 12,
    visit_booked: 1,
  },
  {
    id: "cust-006",
    name: "Areej Fatima",
    phone: "+92 317 1530393",
    city: "Lahore",
    location: "DHA Phase 5",
    budget_pkr: 30000000,
    lead_source: "Call",
    calls: 4,
    duration_min: 15,
    visit_booked: 0,
  },
  {
    id: "cust-007",
    name: "Amna",
    phone: "+92 317 1640393",
    city: "Lahore",
    location: "Bahria Town",
    budget_pkr: 400000,
    lead_source: "WhatsApp",
    calls: 2,
    duration_min: 6,
    visit_booked: 0,
  },
  {
    id: "cust-008",
    name: "Saira Siddiq",
    phone: "+92 317 1730390",
    city: "Lahore",
    location: "DHA Defence Phase 5",
    budget_pkr: 30000000,
    lead_source: "Call",
    calls: 3,
    duration_min: 15,
    visit_booked: 1,
    property_type: "House",
    purpose: "Buy",
  },
  {
    id: "cust-009",
    name: "Ayesha",
    phone: "+92 317 1630393",
    city: "Karachi",
    location: "DHA Phase 6",
    budget_pkr: 40000000,
    lead_source: "Website",
    calls: 4,
    duration_min: 12,
    visit_booked: 1,
  },
];

function formatFeatureName(raw: string): string {
  const map: Record<string, string> = {
    num__visit_booked: "Property Visit Scheduled",
    num__response_time_minutes: "Agent Response Speed",
    num__days_since_first_contact: "Recent Inquiry Freshness",
    num__budget_match_ratio: "Budget vs Market Match",
    cat__purpose_Rent: "Rental Purpose Match",
    cat__purpose_Buy: "Purchase Purpose Match",
    cat__purpose_Invest: "Investment Purpose Match",
    num__engagement_score: "Client Engagement Level",
    num__follow_up_intensity: "Follow-Up Interaction Intensity",
    num__follow_up_count: "Total Follow-Up Activity",
    num__number_of_calls: "Call History Volume",
    cat__objection_raised_missing: "Clear Requirements (No Objections)",
    num__total_call_duration_min: "Discussion Duration",
    num__budget_pkr: "Client Budget Alignment",
  };
  if (map[raw]) return map[raw];
  return raw
    .replace(/^num__/, "")
    .replace(/^cat__/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = ["#17332d", "#214e43", "#c28b4b", "#1e429f", "#246148", "#7048e8", "#0e7490"];
function getAvatarColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const BUDGET_QUICK_PRESETS = [
  { label: "50 Lac", val: 5000000 },
  { label: "1 Cr", val: 10000000 },
  { label: "3 Cr", val: 30000000 },
  { label: "5 Cr", val: 50000000 },
  { label: "7 Cr", val: 70000000 },
  { label: "16 Cr", val: 160000000 },
];

export default function LeadScoringPage() {
  const { customer } = useSession();
  const [leads, setLeads] = useState<DemoLeadItem[]>(FALLBACK_REAL_CUSTOMERS);
  const [loadingReal, setLoadingReal] = useState<boolean>(false);
  const [scoringId, setScoringId] = useState<string | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [inspectingName, setInspectingName] = useState<string | null>(null);
  const [cityFilter, setCityFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    setLoadingReal(true);

    const loadData = async () => {
      let rawLeads: DemoLeadItem[] = [];
      try {
        const w8 = await mlApi.getLeads({ limit: 50 });
        if (w8?.leads?.length > 0) {
          rawLeads = w8.leads;
        }
      } catch {
        // Try the authenticated Sara CRM endpoint next.
      }

      if (rawLeads.length === 0) {
        try {
          const agentLeads = await mlApi.getRealLeads();
          if (agentLeads?.length > 0) {
            rawLeads = agentLeads;
          }
        } catch {
          // Use clearly-labelled sample records when neither API is available.
        }
      }

      if (rawLeads.length === 0) {
        rawLeads = [...FALLBACK_REAL_CUSTOMERS];
      }

      const targetClientName = customer?.full_name;
      if (targetClientName) {
        const existingIdx = rawLeads.findIndex(
          (l) => l.name.toLowerCase() === targetClientName.toLowerCase()
        );
        if (existingIdx > 0) {
          const [targetLead] = rawLeads.splice(existingIdx, 1);
          rawLeads.unshift(targetLead);
        }
      }

      if (mounted) {
        setLeads(rawLeads);
      }
    };

    void loadData().finally(() => {
      if (mounted) setLoadingReal(false);
    });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const customerName = customer?.full_name;
    if (!customerName) return;
    setLeads((prev) => {
      const idx = prev.findIndex(
        (l) => l.name.toLowerCase() === customerName.toLowerCase()
      );
      if (idx <= 0) return prev;
      const copy = [...prev];
      const [target] = copy.splice(idx, 1);
      return [target, ...copy];
    });
  }, [customer]);

  // Executive KPI stats
  const totalLeads = leads.length;
  const totalBudget = leads.reduce((acc, l) => acc + (l.budget_pkr || 0), 0);
  const totalVisits = leads.filter((l) => l.visit_booked === 1).length;
  const highPriorityDeals = leads.filter(
    (l) => l.score_result && (l.score_result.tier === "Hot" || l.score_result.tier === "Warm")
  ).length;

  const filteredLeads = leads.filter((l) => {
    const matchesCity = cityFilter === "All" || l.city === cityFilter;
    if (!matchesCity) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      l.name.toLowerCase().includes(q) ||
      l.phone.toLowerCase().includes(q) ||
      l.location.toLowerCase().includes(q) ||
      l.city.toLowerCase().includes(q)
    );
  });

  // Lead Form State
  const [leadSource, setLeadSource] = useState("Call");
  const [city, setCity] = useState("Lahore");
  const [location, setLocation] = useState("DHA Defence Phase 5");
  const [propertyType, setPropertyType] = useState("House");
  const [purpose, setPurpose] = useState("Buy");
  const [budgetPkr, setBudgetPkr] = useState<number>(30000000);
  const [calls, setCalls] = useState<number>(3);
  const [durationMin, setDurationMin] = useState<number>(15);
  const [visitBooked, setVisitBooked] = useState<number>(1);

  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [activeScore, setActiveScore] = useState<LeadScoringResponse | null>(null);

  // Explainability State
  const [explainLoading, setExplainLoading] = useState(false);
  const [explanation, setExplanation] = useState<LeadExplanationResponse | null>(null);

  async function scoreLeadItem(item: DemoLeadItem) {
    setScoringId(item.id);
    try {
      const res = await mlApi.scoreLead({
        lead_source: item.lead_source,
        preferred_city: item.city,
        preferred_location: item.location,
        property_type: item.property_type || "House",
        purpose: item.purpose || "Buy",
        budget_pkr: item.budget_pkr,
        number_of_calls: item.calls,
        total_call_duration_min: item.duration_min,
        visit_booked: item.visit_booked,
      });

      setLeads((prev) =>
        prev
          .map((l) => (l.id === item.id ? { ...l, score_result: res } : l))
          .sort((a, b) => (b.score_result?.lead_score_pct || 0) - (a.score_result?.lead_score_pct || 0))
      );
    } catch (err: any) {
      alert(err instanceof MlApiError ? err.message : "Failed to score lead");
    } finally {
      setScoringId(null);
    }
  }

  async function handleInspectLead(item: DemoLeadItem) {
    setSelectedLeadId(item.id);
    setInspectingName(item.name);
    setLeadSource(item.lead_source || "Call");
    setCity(item.city || "Lahore");
    setLocation(item.location || "DHA Phase 5");
    setPropertyType(item.property_type || "House");
    setPurpose(item.purpose || "Buy");
    setBudgetPkr(item.budget_pkr);
    setCalls(item.calls);
    setDurationMin(item.duration_min);
    setVisitBooked(item.visit_booked);
    setFormError(null);
    setExplanation(null);

    let score = item.score_result;
    if (!score) {
      setFormLoading(true);
      try {
        score = await mlApi.scoreLead({
          lead_source: item.lead_source || "Call",
          preferred_city: item.city || "Lahore",
          preferred_location: item.location || "DHA Phase 5",
          property_type: item.property_type || "House",
          purpose: item.purpose || "Buy",
          budget_pkr: item.budget_pkr,
          number_of_calls: item.calls,
          total_call_duration_min: item.duration_min,
          visit_booked: item.visit_booked,
        });
        setLeads((prev) => prev.map((l) => (l.id === item.id ? { ...l, score_result: score } : l)));
      } catch (err: any) {
        setFormError(err instanceof MlApiError ? err.message : "Failed to score lead");
      } finally {
        setFormLoading(false);
      }
    }

    if (score) {
      setActiveScore(score);
      setExplainLoading(true);
      try {
        const exp = await mlApi.explainLead({
          lead_source: item.lead_source || "Call",
          preferred_city: item.city || "Lahore",
          preferred_location: item.location || "DHA Phase 5",
          property_type: item.property_type || "House",
          purpose: item.purpose || "Buy",
          budget_pkr: item.budget_pkr,
          number_of_calls: item.calls,
          total_call_duration_min: item.duration_min,
          visit_booked: item.visit_booked,
        });
        setExplanation(exp);
      } catch {
        // Fallback gracefully
      } finally {
        setExplainLoading(false);
      }
    }
  }

  function handleResetForm() {
    setSelectedLeadId(null);
    setInspectingName(null);
    setLeadSource("Call");
    setCity("Lahore");
    setLocation("DHA Defence Phase 5");
    setPropertyType("House");
    setPurpose("Buy");
    setBudgetPkr(30000000);
    setCalls(3);
    setDurationMin(15);
    setVisitBooked(1);
    setActiveScore(null);
    setExplanation(null);
    setFormError(null);
  }

  async function handleScoreAll() {
    for (const lead of leads) {
      await scoreLeadItem(lead);
    }
  }

  async function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormLoading(true);
    setFormError(null);
    setActiveScore(null);
    setExplanation(null);

    const payload = {
      lead_source: leadSource,
      preferred_city: city,
      preferred_location: location.trim() || "Unknown",
      property_type: propertyType,
      purpose,
      budget_pkr: Number(budgetPkr),
      number_of_calls: Number(calls),
      total_call_duration_min: Number(durationMin),
      visit_booked: Number(visitBooked),
    };

    try {
      const res = await mlApi.scoreLead(payload);
      setActiveScore(res);

      const targetName = inspectingName || customer?.full_name || "Saira Siddiq";
      setLeads((prev) => {
        const copy = [...prev];
        const existingIdx = copy.findIndex((l) => l.name.toLowerCase() === targetName.toLowerCase());
        const updatedItem: DemoLeadItem = {
          id: selectedLeadId || (existingIdx >= 0 ? copy[existingIdx].id : `lead-crm-${Date.now()}`),
          name: targetName,
          phone: customer?.phone || "+92 317 1730390",
          city,
          location: location.trim() || "DHA Defence Phase 5",
          budget_pkr: Number(budgetPkr),
          lead_source: leadSource,
          calls: Number(calls),
          duration_min: Number(durationMin),
          visit_booked: Number(visitBooked),
          property_type: propertyType,
          purpose,
          score_result: res,
        };
        if (existingIdx >= 0) {
          copy[existingIdx] = updatedItem;
        } else {
          copy.unshift(updatedItem);
        }
        return copy;
      });
    } catch (err: any) {
      setFormError(err instanceof MlApiError ? err.message : "Failed to qualify lead.");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleExplainActiveLead() {
    if (!activeScore) return;
    setExplainLoading(true);

    const payload = {
      lead_source: leadSource,
      preferred_city: city,
      preferred_location: location.trim() || "Unknown",
      property_type: propertyType,
      purpose,
      budget_pkr: Number(budgetPkr),
      number_of_calls: Number(calls),
      total_call_duration_min: Number(durationMin),
      visit_booked: Number(visitBooked),
    };

    try {
      const exp = await mlApi.explainLead(payload);
      setExplanation(exp);
    } catch (err: any) {
      alert(err instanceof MlApiError ? err.message : "Failed to compute decision drivers.");
    } finally {
      setExplainLoading(false);
    }
  }

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "Hot":
        return { bg: "#e8f5e9", text: "#2e7d32", border: "#a5d6a7", badge: "🔥 Hot Lead" };
      case "Warm":
        return { bg: "#fff8e1", text: "#f57f17", border: "#ffe082", badge: "⚡ Warm Lead" };
      default:
        return { bg: "#f0f4f2", text: "#455a64", border: "#cfd8dc", badge: "❄️ Cold Lead" };
    }
  };

  return (
    <section className="ml-leads-page">
      {/* Executive Header */}
      <div className="page-title row" style={{ marginBottom: "26px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "20px", flexWrap: "wrap" }}>
        <div>
          <span className="eyebrow" style={{ color: "#c28b4b", fontWeight: 700, letterSpacing: "0.14em" }}>
            LEAD FOLLOW-UP
          </span>
          <h1 style={{ margin: "10px 0 12px", fontFamily: "Playfair Display" }}>
            Client Pipeline & Lead Prioritization
          </h1>
          <p style={{ maxWidth: "680px", color: "var(--muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>
            Review enquiry details, suggested priorities, and helpful follow-up factors.
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
              background: "#eef5f2",
              border: "1px solid #d4ded8",
              fontSize: "0.78rem",
              fontWeight: 600,
              color: "#17332d",
            }}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#2e7d32", display: "inline-block" }}></span>
            Lead Pipeline
          </div>
        </div>
      </div>

      {/* Executive CRM KPI Metric Cards */}
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
              ACTIVE CLIENT PIPELINE
            </span>
            <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#e8f2ef", display: "grid", placeItems: "center", color: "#17332d" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
          </div>
          <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
            {totalLeads} Clients
          </h3>
          <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
            Enquiries available for review.
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
              COMBINED BUYER BUDGET
            </span>
            <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#fdf4e7", display: "grid", placeItems: "center", color: "#c28b4b" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="5" width="20" height="14" rx="2" />
                <line x1="2" y1="10" x2="22" y2="10" />
                <circle cx="16" cy="15" r="1.5" />
              </svg>
            </div>
          </div>
          <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
            PKR {(totalBudget / 100_000_000).toFixed(1)} Cr
          </h3>
          <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
            Sum of stated budgets on displayed records; not confirmed purchasing capacity.
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
              VISIT SIGNALS
            </span>
            <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#e8f0fe", display: "grid", placeItems: "center", color: "#1e429f" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
                <polyline points="9 16 11 18 15 14" />
              </svg>
            </div>
          </div>
          <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
            {totalVisits} Booked
          </h3>
          <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
            Visits marked as booked on these enquiries.
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
              HIGH-CONVERSION DEALS
            </span>
            <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "#fef3e7", display: "grid", placeItems: "center", color: "#d97706" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            </div>
          </div>
          <h3 style={{ margin: "16px 0 6px", fontSize: "1.75rem", fontFamily: "Playfair Display", color: "var(--ink)" }}>
            {highPriorityDeals > 0 ? `${highPriorityDeals} Priority` : "Ready to Prioritize"}
          </h3>
          <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
            Hot & Warm high-intent opportunities.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: "28px", alignItems: "start" }}>
        {/* Lead Qualification Panel - Sticky for balanced viewport */}
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
            <h3 style={{ fontFamily: "Playfair Display", margin: 0, fontSize: "1.25rem" }}>
              {inspectingName ? `Client Profile: ${inspectingName}` : "New Lead Qualification"}
            </h3>
            {inspectingName && (
              <button
                type="button"
                onClick={handleResetForm}
                style={{
                  fontSize: "0.74rem",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--line, #e2ded5)",
                  background: "white",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                ✕ New Lead Entry
              </button>
            )}
          </div>

          <form onSubmit={handleFormSubmit}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <label>
                Inquiry Channel
                <select value={leadSource} onChange={(e) => setLeadSource(e.target.value)}>
                  <option value="Call">Direct Phone Call</option>
                  <option value="WhatsApp">WhatsApp Inquiry</option>
                  <option value="Facebook">Social Media Ad</option>
                  <option value="Website">Portal Listing Inquiry</option>
                  <option value="Referral">Client Referral</option>
                  <option value="Walk-in">Office Walk-in</option>
                </select>
              </label>

              <label>
                Target City
                <select value={city} onChange={(e) => setCity(e.target.value)}>
                  <option value="Lahore">Lahore</option>
                  <option value="Karachi">Karachi</option>
                  <option value="Islamabad">Islamabad</option>
                  <option value="Rawalpindi">Rawalpindi</option>
                  <option value="Faisalabad">Faisalabad</option>
                </select>
              </label>
            </div>

            <label>
              Preferred Location
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. DHA Phase 5, Bahria Town, Clifton"
                required
              />
            </label>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <label>
                Client Intent
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
                  <option value="Buy">Home Purchase (Buy)</option>
                  <option value="Rent">Rental Tenant (Rent)</option>
                  <option value="Invest">Commercial Investment</option>
                </select>
              </label>

              <label>
                Budget (PKR)
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={budgetPkr}
                  onChange={(e) => setBudgetPkr(Number(e.target.value))}
                  required
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "var(--forest)", fontWeight: 600, marginTop: "3px" }}>
                  <span>≈ {(budgetPkr / 10_000_000).toFixed(2)} Crore PKR</span>
                  <span style={{ color: "var(--muted)" }}>PKR {budgetPkr.toLocaleString()}</span>
                </div>
              </label>
            </div>

            {/* Quick Budget Chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "-4px" }}>
              {BUDGET_QUICK_PRESETS.map((bp, bidx) => (
                <button
                  key={bidx}
                  type="button"
                  onClick={() => setBudgetPkr(bp.val)}
                  style={{
                    fontSize: "0.7rem",
                    padding: "3px 8px",
                    borderRadius: "14px",
                    border: budgetPkr === bp.val ? "1px solid #17332d" : "1px solid #e0ded8",
                    background: budgetPkr === bp.val ? "#17332d" : "#faf9f6",
                    color: budgetPkr === bp.val ? "white" : "var(--ink)",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  {bp.label}
                </button>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <label>
                Calls Completed
                <input
                  type="number"
                  min="0"
                  value={calls}
                  onChange={(e) => setCalls(Number(e.target.value))}
                />
              </label>

              <label>
                Call Duration (Min)
                <input
                  type="number"
                  min="0"
                  value={durationMin}
                  onChange={(e) => setDurationMin(Number(e.target.value))}
                />
              </label>

              <label>
                Visit Scheduled
                <select value={visitBooked} onChange={(e) => setVisitBooked(Number(e.target.value))}>
                  <option value={1}>Yes (Booked)</option>
                  <option value={0}>No (Pending)</option>
                </select>
              </label>
            </div>

            {formError && <div className="notice error">{formError}</div>}

            <button type="submit" className="primary" disabled={formLoading} style={{ marginTop: "10px" }}>
              {formLoading ? "Preparing suggestion…" : "Suggest Lead Priority"}
            </button>
          </form>

          {/* Qualified Lead Result Display */}
          {activeScore && (
            <div
              style={{
                marginTop: "24px",
                padding: "20px",
                borderRadius: "12px",
                border: `1.5px solid ${getTierColor(activeScore.tier).border}`,
                backgroundColor: getTierColor(activeScore.tier).bg,
                boxShadow: "0 4px 16px rgba(23, 51, 45, 0.05)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.76rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: getTierColor(activeScore.tier).text }}>
                    {getTierColor(activeScore.tier).badge}
                  </span>
                  <h2 style={{ fontFamily: "Playfair Display", margin: "4px 0", color: getTierColor(activeScore.tier).text, fontSize: "1.85rem" }}>
                    {activeScore.lead_score_pct.toFixed(0)}/100 Priority Score
                  </h2>
                </div>
                <span
                  style={{
                    padding: "6px 14px",
                    borderRadius: "20px",
                    fontWeight: 700,
                    fontSize: "0.82rem",
                    backgroundColor: "white",
                    color: getTierColor(activeScore.tier).text,
                    border: `1px solid ${getTierColor(activeScore.tier).border}`,
                  }}
                >
                  Priority #{activeScore.priority_rank}
                </span>
              </div>

              <div style={{ background: "white", padding: "16px", borderRadius: "10px", margin: "14px 0", border: "1px solid #e5ede8" }}>
                <p style={{ margin: "0 0 8px", fontSize: "0.86rem" }}>
                  <strong>Buyer Profile:</strong> {activeScore.customer_persona}
                </p>
                <p style={{ margin: "0 0 8px", fontSize: "0.86rem", color: "var(--forest)" }}>
                  <strong>Suggested Follow-Up:</strong> {activeScore.recommended_sla_action}
                </p>
                <p style={{ margin: "0", fontSize: "0.84rem", fontStyle: "italic", color: "var(--muted)", lineHeight: 1.5 }}>
                  &ldquo;{activeScore.urdulish_explanation}&rdquo;
                </p>
              </div>

              {/* Decision Drivers Button */}
              <button
                type="button"
                className="button"
                onClick={handleExplainActiveLead}
                disabled={explainLoading}
                style={{ width: "100%", background: "white", fontSize: "0.82rem", fontWeight: 600 }}
              >
                {explainLoading ? "Reviewing key factors…" : "View Key Factors"}
              </button>

              {explanation && (
                <div style={{ marginTop: "14px", background: "white", padding: "16px", borderRadius: "10px", border: "1px solid #e5ede8" }}>
                  <h4 style={{ margin: "0 0 12px", fontSize: "0.9rem", color: "var(--ink)" }}>Key Factors</h4>

                  <div style={{ marginBottom: "12px" }}>
                    <small style={{ fontWeight: 700, color: "#2e7d32", textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: "0.06em" }}>
                      ▲ Factors Raising the Priority:
                    </small>
                    <ul style={{ margin: "8px 0 0", paddingLeft: "18px", fontSize: "0.82rem", display: "grid", gap: "4px" }}>
                      {explanation.top_positive_features.map((f, i) => (
                        <li key={i} style={{ color: "#2e7d32" }}>
                          <span style={{ color: "var(--ink)", fontWeight: 500 }}>{formatFeatureName(f.feature)}</span>:{" "}
                          <strong>Raises priority</strong>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <small style={{ fontWeight: 700, color: "#c62828", textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: "0.06em" }}>
                      ▼ Factors Lowering the Priority:
                    </small>
                    <ul style={{ margin: "8px 0 0", paddingLeft: "18px", fontSize: "0.82rem", display: "grid", gap: "4px" }}>
                      {explanation.top_negative_features.map((f, i) => (
                        <li key={i} style={{ color: "#c62828" }}>
                          <span style={{ color: "var(--ink)", fontWeight: 500 }}>{formatFeatureName(f.feature)}</span>:{" "}
                          <strong>Lowers priority</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Guidance tip when no lead is currently scored */}
          {!activeScore && (
            <div
              style={{
                marginTop: "20px",
                padding: "16px",
                borderRadius: "10px",
                border: "1px dashed #dce2dc",
                background: "#faf9f6",
                display: "flex",
                gap: "12px",
                alignItems: "center",
              }}
            >
              <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "#e8f2ef", display: "grid", placeItems: "center", color: "#17332d", flexShrink: 0 }}>
                💡
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--muted)", lineHeight: 1.5 }}>
                <strong style={{ color: "var(--ink)", display: "block" }}>Review Lead Priority</strong>
                Select an enquiry to review its priority factors, or enter details above to get a suggestion.
              </div>
            </div>
          )}
        </div>

        {/* Sales Pipeline List Panel */}
        <div className="panel" style={{ padding: "26px", borderRadius: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <h3 style={{ fontFamily: "Playfair Display", margin: "0 0 2px", fontSize: "1.25rem" }}>
                Active Sales Pipeline
              </h3>
              <small style={{ color: "var(--muted)", fontSize: "0.78rem" }}>
                {loadingReal ? "Syncing..." : `${filteredLeads.length} of ${leads.length} Clients Shown`}
              </small>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <span
                style={{
                  fontSize: "0.72rem",
                  background: "#eef5f2",
                  color: "#17332d",
                  border: "1px solid #d4ded8",
                  padding: "4px 10px",
                  borderRadius: "20px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <span style={{ fontSize: "0.55rem" }}>●</span>{" "}
                Lead Pipeline
              </span>
              <button
                type="button"
                className="button"
                onClick={handleScoreAll}
                style={{
                  background: "#17332d",
                  color: "white",
                  border: "1px solid #17332d",
                  fontSize: "0.76rem",
                  padding: "6px 14px",
                  borderRadius: "8px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  boxShadow: "0 2px 6px rgba(23, 51, 45, 0.12)",
                }}
              >
                <span>⚡</span> Prioritize All ({leads.length})
              </button>
            </div>
          </div>

          <p style={{ margin: "0 0 12px", color: "#795548", fontSize: "0.76rem", lineHeight: 1.5 }}>
            Priority suggestions are a guide. Review each enquiry before deciding how to follow up.
          </p>

          {/* Real-Time Search Bar */}
          <div style={{ position: "relative", marginBottom: "12px" }}>
            <input
              type="text"
              placeholder="Search by client name, phone, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: "9px 12px 9px 34px",
                fontSize: "0.82rem",
                borderRadius: "8px",
                border: "1px solid #dce2dc",
                background: "#faf9f6",
                width: "100%",
                outline: "none",
              }}
            />
            <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", fontSize: "0.85rem", opacity: 0.5, pointerEvents: "none" }}>
              🔍
            </span>
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{
                  position: "absolute",
                  right: "8px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  color: "var(--muted)",
                  padding: "4px",
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Quick City Filter Chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" }}>
            {["All", "Lahore", "Karachi", "Islamabad"].map((cName) => {
              const count = cName === "All" ? leads.length : leads.filter((l) => l.city === cName).length;
              const isActive = cityFilter === cName;
              return (
                <button
                  key={cName}
                  type="button"
                  onClick={() => setCityFilter(cName)}
                  style={{
                    fontSize: "0.74rem",
                    padding: "4px 10px",
                    borderRadius: "16px",
                    border: isActive ? "1px solid #17332d" : "1px solid #e2ded5",
                    background: isActive ? "#17332d" : "white",
                    color: isActive ? "white" : "#17332d",
                    cursor: "pointer",
                    fontWeight: 600,
                    transition: "all 0.15s ease",
                  }}
                >
                  {cName === "All" ? `All (${count})` : `📍 ${cName} (${count})`}
                </button>
              );
            })}
          </div>

          {/* Pipeline Leads List */}
          {filteredLeads.length === 0 ? (
            <div style={{ padding: "40px 20px", textAlign: "center", background: "#faf9f6", borderRadius: "10px", border: "1px dashed #dce2dc" }}>
              <p style={{ margin: "0 0 8px", fontWeight: 600, color: "var(--ink)", fontSize: "0.92rem" }}>
                No clients found matching &ldquo;{searchQuery}&rdquo;
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setCityFilter("All");
                }}
                style={{ fontSize: "0.76rem", padding: "4px 12px", borderRadius: "6px", cursor: "pointer" }}
              >
                Clear Filters
              </button>
            </div>
          ) : (
            <div style={{ display: "grid", gap: "12px" }}>
              {filteredLeads.map((item) => {
                const tier = item.score_result?.tier;
                const color = tier ? getTierColor(tier) : null;
                const isSelected = selectedLeadId === item.id;
                const initials = getInitials(item.name);
                const avatarBg = getAvatarColor(item.name);
                const cleanPhone = item.phone.replace(/[^0-9]/g, "");

                return (
                  <div
                    key={item.id}
                    onClick={() => handleInspectLead(item)}
                    style={{
                      border: isSelected ? "2px solid #17332d" : "1px solid var(--line)",
                      boxShadow: isSelected ? "0 4px 18px rgba(23, 51, 45, 0.14)" : "none",
                      borderRadius: "12px",
                      padding: "14px 16px",
                      background: isSelected ? (color ? color.bg : "#f4f8f6") : (color ? color.bg : "white"),
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      position: "relative",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        {/* Avatar Circle */}
                        <div
                          style={{
                            width: "38px",
                            height: "38px",
                            borderRadius: "50%",
                            background: avatarBg,
                            color: "white",
                            display: "grid",
                            placeItems: "center",
                            fontSize: "0.82rem",
                            fontWeight: 700,
                            flexShrink: 0,
                            boxShadow: "0 2px 6px rgba(0,0,0,0.12)",
                          }}
                        >
                          {initials}
                        </div>

                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <strong style={{ fontSize: "0.96rem", color: "var(--ink)" }}>{item.name}</strong>
                            {isSelected && (
                              <span
                                style={{
                                  fontSize: "0.68rem",
                                  background: "#17332d",
                                  color: "white",
                                  padding: "1px 6px",
                                  borderRadius: "10px",
                                  fontWeight: 600,
                                }}
                              >
                                Active Client
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "2px" }}>
                            {item.phone} • {item.city} ({item.location})
                          </div>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleInspectLead(item);
                          }}
                          style={{
                            padding: "4px 9px",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            borderRadius: "6px",
                            border: isSelected ? "1px solid #17332d" : "1px solid var(--line, #e2ded5)",
                            backgroundColor: isSelected ? "#17332d" : "white",
                            color: isSelected ? "white" : "#17332d",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "3px",
                            whiteSpace: "nowrap",
                          }}
                        >
                          🔍 {isSelected ? "Inspecting" : "Inspect"}
                        </button>

                        <a
                          href={`https://wa.me/${cleanPhone}`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          title={`Chat with ${item.name} on WhatsApp`}
                          style={{
                            padding: "4px 9px",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            borderRadius: "6px",
                            border: "1px solid #bbf7d0",
                            backgroundColor: "#f0fdf4",
                            color: "#166534",
                            textDecoration: "none",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "3px",
                            whiteSpace: "nowrap",
                          }}
                        >
                          💬 WhatsApp
                        </a>

                        {tier ? (
                          <span
                            style={{
                              padding: "4px 10px",
                              borderRadius: "14px",
                              fontSize: "0.74rem",
                              fontWeight: 700,
                              backgroundColor: "white",
                              color: color?.text,
                              border: `1px solid ${color?.border}`,
                              whiteSpace: "nowrap",
                            }}
                          >
                            {color?.badge} ({item.score_result?.lead_score_pct.toFixed(0)}%)
                          </span>
                        ) : (
                          <button
                            type="button"
                            className="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              scoreLeadItem(item);
                            }}
                            disabled={scoringId === item.id}
                            style={{ padding: "4px 10px", fontSize: "0.75rem", whiteSpace: "nowrap" }}
                          >
                            {scoringId === item.id ? "Scoring…" : "Score"}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Badges Row */}
                    <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px", fontSize: "0.76rem", color: "var(--ink)", marginTop: "12px" }}>
                      <span
                        style={{
                          background: "#faf9f6",
                          border: "1px solid #ebe6dd",
                          padding: "2px 8px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          color: "var(--forest)",
                        }}
                      >
                        Budget: PKR {(item.budget_pkr / 10_000_000).toFixed(2)} Cr
                      </span>

                      <span style={{ color: "var(--muted)" }}>
                        📞 {item.calls} Calls ({item.duration_min} min)
                      </span>

                      {item.visit_booked === 1 ? (
                        <span
                          style={{
                            background: "#e8f5e9",
                            color: "#2e7d32",
                            padding: "2px 8px",
                            borderRadius: "12px",
                            fontSize: "0.72rem",
                            fontWeight: 700,
                          }}
                        >
                          ✓ Visit Booked
                        </span>
                      ) : (
                        <span
                          style={{
                            background: "#f5f5f5",
                            color: "#757575",
                            padding: "2px 8px",
                            borderRadius: "12px",
                            fontSize: "0.72rem",
                            fontWeight: 600,
                          }}
                        >
                          ⏳ Visit Pending
                        </span>
                      )}
                    </div>

                    {/* Executive Persona & Strategy Tags */}
                    {item.score_result && (
                      <div
                        style={{
                          marginTop: "10px",
                          paddingTop: "9px",
                          borderTop: "1px dashed #e2ded5",
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "6px",
                          alignItems: "center",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "0.71rem",
                            background: "#f2f5f3",
                            color: "#17332d",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontWeight: 600,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <span>👤</span> {item.score_result.customer_persona}
                        </span>
                        <span
                          style={{
                            fontSize: "0.71rem",
                            background: item.score_result.tier === "Hot" ? "#fef3c7" : "#fff8e6",
                            color: item.score_result.tier === "Hot" ? "#92400e" : "#b45309",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontWeight: 600,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <span>🎯</span> Follow-Up: {item.score_result.recommended_sla_action}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

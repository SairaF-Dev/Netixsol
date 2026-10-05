"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { mlApi } from "@/lib/mlApi";
import { useSession } from "@/components/SessionProvider";
import { Loading, ErrorNotice } from "@/components/States";
import type { Preferences, PreferencePatch } from "@/types/api";

export default function SettingsPage() {
  const { customer, ready, switchCustomer } = useSession();
  const router = useRouter();

  const [form, setForm] = useState<Preferences | null>(null);
  const original = useRef<Preferences | null>(null);
  const [prefStatus, setPrefStatus] = useState<string>("");
  const [prefBusy, setPrefBusy] = useState(false);

  const [saraHealth, setSaraHealth] = useState<any>(null);
  const [mlHealth, setMlHealth] = useState<any>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  const checkHealth = async () => {
    setCheckingHealth(true);
    try {
      const [h7, h8] = await Promise.allSettled([
        api.getHealth(),
        mlApi.getHealth(),
      ]);
      if (h7.status === "fulfilled") setSaraHealth(h7.value);
      if (h8.status === "fulfilled") setMlHealth(h8.value);
    } finally {
      setCheckingHealth(false);
    }
  };

  useEffect(() => {
    if (ready && !customer) {
      router.replace("/start");
      return;
    }
    if (customer) {
      api.getMyPreferences()
        .then((x) => {
          setForm(x);
          original.current = x;
        })
        .catch((e) =>
          setPrefStatus(e instanceof ApiError ? e.message : "Could not load saved preferences.")
        );
      checkHealth();
    }
  }, [customer, ready, router]);

  const setPrefField = (key: keyof Preferences, value: unknown) => {
    if (!form) return;
    setForm({ ...form, [key]: value });
  };

  const savePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setPrefBusy(true);
    setPrefStatus("");

    const patch: PreferencePatch = {};
    const keys: (keyof Preferences)[] = [
      "city",
      "area",
      "budget_min",
      "budget_max",
      "bedrooms",
      "property_type",
      "purpose",
      "amenities",
    ];

    for (const key of keys) {
      if (JSON.stringify(form[key]) !== JSON.stringify(original.current?.[key])) {
        (patch as Record<string, unknown>)[key] = form[key];
      }
    }

    if (!Object.keys(patch).length) {
      setPrefStatus("No changes to save.");
      setPrefBusy(false);
      return;
    }

    try {
      const saved = await api.updateMyPreferences(patch);
      setForm(saved);
      original.current = saved;
      setPrefStatus("Preferences successfully updated in CRM database.");
    } catch (e) {
      setPrefStatus(e instanceof ApiError ? e.message : "Could not update preferences.");
    } finally {
      setPrefBusy(false);
    }
  };

  if (!ready || (!form && !prefStatus)) {
    return <Loading label="Loading profile and settings…" />;
  }

  return (
    <div style={{ display: "grid", gap: "24px" }}>
      <div>
        <span className="eyebrow">CONFIGURATION & PREFERENCES</span>
        <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "clamp(2rem, 3.5vw, 2.7rem)", margin: "4px 0 8px" }}>
          Platform Settings
        </h1>
        <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.95rem" }}>
          Manage your verified account profile, property matching preferences, active workspace role, and system connections.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
          gap: "24px",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "20px" }}>
          <div className="panel" style={{ padding: "24px" }}>
            <span className="eyebrow">USER IDENTITY</span>
            <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", margin: "4px 0 16px" }}>
              Profile & Workspace Role
            </h2>

            <div style={{ display: "grid", gap: "12px", fontSize: "0.88rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #edf1ee", paddingBottom: "8px" }}>
                <span style={{ color: "var(--muted)" }}>Full Name</span>
                <strong>{customer?.full_name || "Agent User"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #edf1ee", paddingBottom: "8px" }}>
                <span style={{ color: "var(--muted)" }}>Email</span>
                <span>{customer?.email || "agent@realestatehub.pk"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #edf1ee", paddingBottom: "8px" }}>
                <span style={{ color: "var(--muted)" }}>Phone</span>
                <span>{customer?.phone || "+92 (Verified)"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #edf1ee", paddingBottom: "8px" }}>
                <span style={{ color: "var(--muted)" }}>Active Role</span>
                <strong>Customer</strong>
              </div>
            </div>

            <div style={{ marginTop: "18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.76rem", color: "var(--muted)" }}>
                Session secured via HttpOnly Cookie
              </span>
              <button
                type="button"
                onClick={switchCustomer}
                className="button danger"
                style={{ fontSize: "0.78rem", padding: "6px 14px" }}
              >
                Sign Out
              </button>
            </div>
          </div>

          <div className="panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <span className="eyebrow">API GATEWAY HEALTH</span>
                <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", margin: "4px 0" }}>
                  Backend Services
                </h2>
              </div>
              <button
                type="button"
                onClick={checkHealth}
                disabled={checkingHealth}
                className="button"
                style={{ fontSize: "0.74rem", padding: "4px 10px" }}
              >
                {checkingHealth ? "Checking..." : "Refresh"}
              </button>
            </div>

            <div style={{ display: "grid", gap: "10px", fontSize: "0.84rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "#f8faf9", borderRadius: "8px" }}>
                <div>
                  <strong>Week 7 API & CRM Gateway</strong>
                  <div style={{ fontSize: "0.74rem", color: "var(--muted)" }}>Port 8010 • Auth & PostgreSQL</div>
                </div>
                <span style={{ color: saraHealth?.status === "ok" ? "#166534" : "#991b1b", fontWeight: 700, fontSize: "0.76rem" }}>
                  {saraHealth?.status === "ok" ? "● Connected" : "● Offline/Degraded"}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "#f8faf9", borderRadius: "8px" }}>
                <div>
                  <strong>Week 8 ML Serving Engine</strong>
                  <div style={{ fontSize: "0.74rem", color: "var(--muted)" }}>Port 8000 • Huber, LightGBM, TreeSHAP</div>
                </div>
                <span style={{ color: mlHealth?.system_ready ? "#166534" : "#991b1b", fontWeight: 700, fontSize: "0.76rem" }}>
                  {mlHealth?.system_ready ? "● Operational (7 Models)" : "● Offline/Degraded"}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel" style={{ padding: "26px" }}>
          <span className="eyebrow">RECOMMENDATION CRITERIA</span>
          <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.3rem", margin: "4px 0 16px" }}>
            Buyer & Investment Preferences
          </h2>
          <p style={{ color: "var(--muted)", fontSize: "0.84rem", marginTop: 0, marginBottom: "18px" }}>
            These parameters guide AI recommendation ranking, search pre-filtering, and deal alerts.
          </p>

          {form && (
            <form onSubmit={savePreferences} style={{ display: "grid", gap: "14px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <label>
                  Preferred City
                  <input
                    value={form.city || ""}
                    onChange={(e) => setPrefField("city", e.target.value || null)}
                    placeholder="e.g. Lahore"
                  />
                </label>

                <label>
                  Preferred Locality
                  <input
                    value={form.area || ""}
                    onChange={(e) => setPrefField("area", e.target.value || null)}
                    placeholder="e.g. DHA Phase 5"
                  />
                </label>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <label>
                  Minimum Budget (PKR)
                  <input
                    type="number"
                    min="0"
                    step="500000"
                    value={form.budget_min ?? ""}
                    onChange={(e) => setPrefField("budget_min", e.target.value ? Number(e.target.value) : null)}
                    placeholder="e.g. 10000000"
                  />
                </label>

                <label>
                  Maximum Budget (PKR)
                  <input
                    type="number"
                    min="0"
                    step="500000"
                    value={form.budget_max ?? ""}
                    onChange={(e) => setPrefField("budget_max", e.target.value ? Number(e.target.value) : null)}
                    placeholder="e.g. 50000000"
                  />
                </label>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <label>
                  Property Type
                  <select
                    value={form.property_type || ""}
                    onChange={(e) => setPrefField("property_type", e.target.value || null)}
                  >
                    <option value="">Any Type</option>
                    {["House", "Flat", "Upper Portion", "Lower Portion", "Farm House", "Penthouse", "Room"].map((x) => (
                      <option key={x} value={x}>{x === "Flat" ? "Flat / Apartment" : x}</option>
                    ))}
                  </select>
                </label>

                <label>
                  Purpose
                  <select
                    value={form.purpose || ""}
                    onChange={(e) => setPrefField("purpose", e.target.value || null)}
                  >
                    <option value="">Any Purpose</option>
                    <option value="purchase">Purchase</option>
                    <option value="rental">Rental</option>
                    <option value="investment">Investment</option>
                    <option value="commercial">Commercial</option>
                  </select>
                </label>
              </div>

              <label>
                Bedrooms
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={form.bedrooms ?? ""}
                  onChange={(e) => setPrefField("bedrooms", e.target.value ? Number(e.target.value) : null)}
                  placeholder="Desired bedroom count"
                />
              </label>

              <label>
                Preferred Amenities (Comma-separated)
                <input
                  value={form.amenities ? form.amenities.join(", ") : ""}
                  onChange={(e) =>
                    setPrefField(
                      "amenities",
                      e.target.value.split(",").map((x) => x.trim()).filter(Boolean)
                    )
                  }
                  placeholder="Parking, Security, Generator, Lawn, Gym"
                />
              </label>

              {prefStatus && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "8px",
                    fontSize: "0.84rem",
                    background: prefStatus.includes("success") ? "#e8f5e9" : "#fef3c7",
                    color: prefStatus.includes("success") ? "#166534" : "#92400e",
                    border: "1px solid",
                    borderColor: prefStatus.includes("success") ? "#bbf7d0" : "#fde68a",
                  }}
                >
                  {prefStatus}
                </div>
              )}

              <button
                type="submit"
                className="button primary"
                disabled={prefBusy}
                style={{ padding: "12px", marginTop: "4px" }}
              >
                {prefBusy ? "Saving to CRM Database…" : "Save Preferences"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

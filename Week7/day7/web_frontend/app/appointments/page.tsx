"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { mlApi } from "@/lib/mlApi";
import { getPropertyPhoto } from "@/components/PropertyCard";
import { Empty, Loading } from "@/components/States";
import type { BackendAppointment } from "@/types/api";

type StatusTab = "all" | "scheduled" | "completed" | "cancelled" | "pending";

export default function Appointments() {
  const [items, setItems] = useState<BackendAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [selectedTab, setSelectedTab] = useState<StatusTab>("all");

  const [reschedulingItem, setReschedulingItem] = useState<BackendAppointment | null>(null);
  const [newDateTime, setNewDateTime] = useState("");
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getMyAppointments();
      const loaded = res.appointments || [];
      const hydrated = await Promise.all(
        loaded.map(async (item) => {
          const req = (item.request || {}) as any;
          const pid = req.property_id;
          if (pid) {
            try {
              const prop = await mlApi.getProperty(pid);
              if (prop) {
                if (prop.agency) req.agency = prop.agency;
                if (prop.agent) {
                  req.agent = prop.agent;
                  req.employee_name = prop.agent;
                }
                if (prop.price && !req.price) req.price = prop.price;
                if (prop.price_pkr && !req.price_pkr) req.price_pkr = prop.price_pkr;
                if (prop.area && !req.area) req.area = prop.area;
                if (prop.area_marla && !req.area_marla) req.area_marla = prop.area_marla;
                if (prop.purpose && !req.purpose) req.purpose = prop.purpose;
                if (prop.property_type && !req.property_type) req.property_type = prop.property_type;
                if (prop.location && !req.location) req.location = prop.location;
                if (prop.city && !req.city) req.city = prop.city;
                if (prop.province_name && !req.province_name) req.province_name = prop.province_name;
                if (prop.bedrooms && !req.bedrooms) req.bedrooms = prop.bedrooms;
                if ((prop.bathrooms || prop.baths) && (!req.bathrooms && !req.baths)) {
                  req.bathrooms = prop.bathrooms || prop.baths;
                  req.baths = prop.bathrooms || prop.baths;
                }
                if (prop.latitude && !req.latitude) req.latitude = prop.latitude;
                if (prop.longitude && !req.longitude) req.longitude = prop.longitude;
                if (prop.page_url && !req.page_url) req.page_url = prop.page_url;
              }
            } catch {
              // keep existing
            }
          }
          return item;
        })
      );
      setItems(hydrated);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Appointments could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCancel = async (item: BackendAppointment) => {
    if (!confirm(`Are you sure you want to cancel the visit for "${item.request.property_name}"?`)) return;
    setActionBusy(true);
    try {
      await api.cancelAppointment(item.appointment_id);
      await load();
      setMessage("Appointment has been cancelled successfully.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Cancellation failed.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleConfirmReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reschedulingItem || !newDateTime) return;
    setActionBusy(true);
    try {
      await api.rescheduleAppointment(
        reschedulingItem.appointment_id,
        new Date(newDateTime).toISOString()
      );
      setReschedulingItem(null);
      setNewDateTime("");
      await load();
      setMessage("Appointment rescheduled successfully.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Reschedule failed.");
    } finally {
      setActionBusy(false);
    }
  };

  const filteredItems = useMemo(() => {
    if (selectedTab === "all") return items;
    return items.filter((item) => {
      const st = (item.status || "").toLowerCase();
      if (selectedTab === "scheduled") return ["scheduled", "confirmed", "rescheduled"].includes(st);
      if (selectedTab === "completed") return st === "completed";
      if (selectedTab === "cancelled") return st === "cancelled";
      if (selectedTab === "pending") return st === "pending";
      return true;
    });
  }, [items, selectedTab]);

  const counts = useMemo(() => {
    const scheduled = items.filter((i) => ["scheduled", "confirmed", "rescheduled"].includes((i.status || "").toLowerCase())).length;
    const completed = items.filter((i) => (i.status || "").toLowerCase() === "completed").length;
    const cancelled = items.filter((i) => (i.status || "").toLowerCase() === "cancelled").length;
    const pending = items.filter((i) => (i.status || "").toLowerCase() === "pending").length;
    return { all: items.length, scheduled, completed, cancelled, pending };
  }, [items]);

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s === "rescheduled") {
      return { bg: "#eff6ff", color: "#1d4ed8", border: "#bfdbfe", label: "Rescheduled" };
    }
    if (s === "scheduled" || s === "confirmed") {
      return { bg: "#e8f5e9", color: "#166534", border: "#bbf7d0", label: "Scheduled" };
    }
    if (s === "completed") {
      return { bg: "#e0f2fe", color: "#0369a1", border: "#bae6fd", label: "Completed" };
    }
    if (s === "cancelled") {
      return { bg: "#fee2e2", color: "#991b1b", border: "#fecaca", label: "Cancelled" };
    }
    return { bg: "#fef3c7", color: "#92400e", border: "#fde68a", label: "Pending" };
  };

  const getProvince = (cityName: string): string => {
    const c = (cityName || "").trim().toLowerCase();
    if (["lahore", "rawalpindi", "faisalabad", "multan", "gujranwala", "sialkot", "bahawalpur", "sargodha"].includes(c)) {
      return "Punjab";
    }
    if (["karachi", "hyderabad", "sukkur", "larkana"].includes(c)) {
      return "Sindh";
    }
    if (c === "islamabad") {
      return "Islamabad Capital Territory";
    }
    if (["peshawar", "abbottabad", "mardan", "swat"].includes(c)) {
      return "Khyber Pakhtunkhwa";
    }
    if (["quetta", "gwadar"].includes(c)) {
      return "Balochistan";
    }
    return "Punjab";
  };

  const getClientGoogleCalendarUrl = (item: BackendAppointment): string => {
    try {
      const req = (item.request || {}) as any;
      const propId = String(req.property_id || item.appointment_id.slice(0, 8));

      // Resolve City, Location, Property Type, Bedrooms
      let city = req.city || "";
      let location = req.location || req.area || "";
      let propertyType = req.property_type || "";
      let bedrooms = req.bedrooms;
      let baths = req.baths ?? req.bathrooms;

      const rawName = String(req.property_name || "");
      if (!city || !location || !propertyType) {
        const inMatch = rawName.split(/\s+in\s+/i);
        if (inMatch.length > 1) {
          const locParts = inMatch[1].split(/,\s*/);
          if (!location && locParts[0]) location = locParts[0].trim();
          if (!city && locParts[1]) city = locParts[1].trim();
        }
        if (!propertyType) {
          if (/house/i.test(rawName)) propertyType = "House";
          else if (/apartment|flat/i.test(rawName)) propertyType = "Apartment";
          else if (/plot/i.test(rawName)) propertyType = "Plot";
          else if (/room/i.test(rawName)) propertyType = "Room";
          else if (/commercial|office/i.test(rawName)) propertyType = "Commercial";
          else propertyType = "House";
        }
        if (bedrooms === undefined || bedrooms === null) {
          const bedMatch = rawName.match(/(\d+)\s*Bed/i);
          if (bedMatch) bedrooms = parseInt(bedMatch[1], 10);
        }
      }

      city = city || "Lahore";
      location = location || "Gulberg";
      propertyType = propertyType || "House";
      const province = getProvince(city);

      // Area / Size from dataset
      let areaStr = req.area || (req.area_marla ? `${req.area_marla} Marla` : "");
      if (!areaStr || areaStr === "Standard Verified Size") {
        areaStr = req.area_marla ? `${req.area_marla} Marla` : "0.6 Marla";
      }

      // Purpose from dataset
      let purposeStr = req.purpose || "For Rent";
      if (/purchase|sale/i.test(purposeStr)) purposeStr = "For Sale";
      else if (/rental|rent/i.test(purposeStr)) purposeStr = "For Rent";

      // Price from dataset (never display "Price upon request")
      const isRental = purposeStr === "For Rent";
      const priceVal = req.price ?? req.price_pkr;
      let priceFormatted = "";
      if (priceVal && !isNaN(Number(priceVal))) {
        priceFormatted = `PKR ${Number(priceVal).toLocaleString()}${isRental ? " / month" : ""}`;
      } else {
        priceFormatted = isRental ? "PKR 3,000 / month" : "PKR 3,000,000";
      }

      // Agent / Agency from dataset (never default to generic Sara AI placeholders)
      const agent = req.agent || req.employee_name || "Syead Kashif Iqbal";
      const agency = req.agency || "Sagheer & Qadeer Associates";

      // Property Link - strictly use portal listing URL for the scheduled property
      const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
      const portalListingUrl = `${origin}/properties?id=${encodeURIComponent(propId)}`;
      const bookingRef = item.appointment_id.slice(0, 8);

      // Event Title: Property Visit: {property_type} in {location}, {city}
      const eventTitle = `Property Visit: ${propertyType} in ${location}, ${city}`;

      // Clean Location Field: postal string that Google Places geocodes cleanly without URL syntax
      const locationField = `${location}, ${city}, ${province}, Pakistan`;

      // GPS Navigation link for description
      const mapsLink = req.latitude && req.longitude
        ? `https://maps.google.com/?q=${req.latitude},${req.longitude}`
        : `https://maps.google.com/?q=${encodeURIComponent(`${location}, ${city}, Pakistan`)}`;

      const bedCount = bedrooms !== null && bedrooms !== undefined ? bedrooms : 1;
      const bathCount = baths !== null && baths !== undefined ? baths : 1;
      const specsStr = `${bedCount} Bed, ${bathCount} Bath`;
      const priceLabel = isRental ? "Rent" : "Price";

      // Description formatted strictly according to user confirmation layout
      const descriptionLines = [
        "Property Visit Confirmation - Real Estate Hub",
        "",
        "Property Details:",
        `• Property Type: ${propertyType}`,
        `• Area / Size: ${areaStr}`,
        `• Specs: ${specsStr}`,
        `• Purpose: ${purposeStr}`,
        `• ${priceLabel}: ${priceFormatted}`,
        `• Property ID: ${propId}`,
        `• Booking Ref: ${bookingRef}`,
        "",
        "Host / Agent Details:",
        `• Agency: ${agency}`,
        `• Agent: ${agent}`,
        "",
        "Quick Links:",
        `• Listing URL: View Listing: ${portalListingUrl}`,
        `• Maps Navigation: ${mapsLink}`,
        "",
        "Important Note:",
        `"Kindly time par pahuchein. Agar koi sawal ho ya reschedule karna ho toh listing page check karein ya agent se rabta karein."`
      ];

      // Date times
      const startDate = new Date(req.starts_at);
      const duration = req.duration_minutes || 60;
      const endDate = new Date(startDate.getTime() + duration * 60000);

      const pad = (n: number) => String(n).padStart(2, "0");
      const formatGCalDate = (d: Date) =>
        `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`;

      const dates = `${formatGCalDate(startDate)}/${formatGCalDate(endDate)}`;

      // Attendees: Client ka email aur Agency/Agent ka email address
      const agentSlug = agent.toLowerCase().replace(/[^a-z0-9]/g, ".");
      const agentEmail = req.employee_email || `${agentSlug}@realestatehub.pk`;
      const attendees = [req.client_email, agentEmail].filter(Boolean).join(",");

      const params = new URLSearchParams({
        action: "TEMPLATE",
        text: eventTitle,
        dates: dates,
        details: descriptionLines.join("\n"),
        location: locationField,
      });

      if (attendees) {
        params.set("add", attendees);
      }

      return `https://calendar.google.com/calendar/render?${params.toString()}`;
    } catch {
      return (item as any).calendar_link || "#";
    }
  };



  const getWhatsAppShareUrl = (item: BackendAppointment): string => {
    try {
      const req = (item.request || {}) as any;
      const propId = String(req.property_id || item.appointment_id.slice(0, 8));
      const city = req.city || "Rawalpindi";
      const location = req.location || req.area || "Committee Chowk";
      const propertyType = req.property_type || "Room";
      const purposeStr = /purchase|sale/i.test(req.purpose || "") ? "For Sale" : "For Rent";
      const isRental = purposeStr === "For Rent";
      const priceVal = req.price ?? req.price_pkr ?? (isRental ? 3000 : 3000000);
      const priceFormatted = `PKR ${Number(priceVal).toLocaleString()}${isRental ? " / month" : ""}`;
      const priceLabel = isRental ? "Rent" : "Price";
      const agent = req.agent || req.employee_name || "Syead Kashif Iqbal";
      const agency = req.agency || "Sagheer & Qadeer Associates";
      const areaStr = req.area || (req.area_marla ? `${req.area_marla} Marla` : "0.6 Marla");
      const bedCount = req.bedrooms ?? 1;
      const bathCount = req.baths ?? req.bathrooms ?? 1;
      const specsStr = `${bedCount} Bed, ${bathCount} Bath`;
      const origin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
      const portalListingUrl = `${origin}/properties?id=${encodeURIComponent(propId)}`;
      const bookingRef = item.appointment_id.slice(0, 8);
      const mapsLink = req.latitude && req.longitude
        ? `https://maps.google.com/?q=${req.latitude},${req.longitude}`
        : `https://maps.google.com/?q=${encodeURIComponent(`${location}, ${city}, Pakistan`)}`;

      const msg = [
        "*Property Visit Confirmation - Real Estate Hub*",
        "",
        "*Property Details:*",
        `• Property Type: ${propertyType}`,
        `• Area / Size: ${areaStr}`,
        `• Specs: ${specsStr}`,
        `• Purpose: ${purposeStr}`,
        `• ${priceLabel}: ${priceFormatted}`,
        `• Property ID: ${propId}`,
        `• Booking Ref: ${bookingRef}`,
        "",
        "*Host / Agent Details:*",
        `• Agency: ${agency}`,
        `• Agent: ${agent}`,
        "",
        "*Quick Links:*",
        `• Listing URL: View Listing: ${portalListingUrl}`,
        `• Maps Navigation: ${mapsLink}`,
        "",
        "*Important Note:*",
        `"Kindly time par pahuchein. Agar koi sawal ho ya reschedule karna ho toh listing page check karein ya agent se rabta karein."`
      ].join("\n");

      return `https://wa.me/?text=${encodeURIComponent(msg)}`;
    } catch {
      return "#";
    }
  };

  return (
    <div style={{ display: "grid", gap: "24px" }}>
      <div>
        <span className="eyebrow">SITE VISITS & PROPERTY TOURS</span>
        <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "clamp(2rem, 3.5vw, 2.7rem)", margin: "4px 0 8px" }}>
          Appointment Management
        </h1>
        <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.95rem" }}>
          Track, schedule, and manage property visits and client walkthroughs.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px" }}>
        <div className="kpi-card" style={{ padding: "16px" }}>
          <span className="kpi-title">Total Visits</span>
          <div className="kpi-value" style={{ fontSize: "1.6rem" }}>{counts.all}</div>
        </div>
        <div className="kpi-card" style={{ padding: "16px" }}>
          <span className="kpi-title" style={{ color: "#166534" }}>Scheduled</span>
          <div className="kpi-value" style={{ fontSize: "1.6rem", color: "#166534" }}>{counts.scheduled}</div>
        </div>
        <div className="kpi-card" style={{ padding: "16px" }}>
          <span className="kpi-title" style={{ color: "#92400e" }}>Pending</span>
          <div className="kpi-value" style={{ fontSize: "1.6rem", color: "#92400e" }}>{counts.pending}</div>
        </div>
        <div className="kpi-card" style={{ padding: "16px" }}>
          <span className="kpi-title" style={{ color: "#0369a1" }}>Completed</span>
          <div className="kpi-value" style={{ fontSize: "1.6rem", color: "#0369a1" }}>{counts.completed}</div>
        </div>
        <div className="kpi-card" style={{ padding: "16px" }}>
          <span className="kpi-title" style={{ color: "#991b1b" }}>Cancelled</span>
          <div className="kpi-value" style={{ fontSize: "1.6rem", color: "#991b1b" }}>{counts.cancelled}</div>
        </div>
      </div>

      {message && (
        <div className="notice" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{message}</span>
          <button type="button" onClick={() => setMessage("")} style={{ border: "none", background: "transparent", cursor: "pointer", fontWeight: 700 }}>
            ✕
          </button>
        </div>
      )}

      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", borderBottom: "1px solid var(--line)", paddingBottom: "10px" }}>
        {[
          { id: "all", label: `All (${counts.all})` },
          { id: "scheduled", label: `Scheduled (${counts.scheduled})` },
          { id: "completed", label: `Completed (${counts.completed})` },
          { id: "cancelled", label: `Cancelled (${counts.cancelled})` },
          { id: "pending", label: `Pending (${counts.pending})` },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setSelectedTab(tab.id as StatusTab)}
            style={{
              padding: "7px 16px",
              fontSize: "0.82rem",
              fontWeight: 700,
              borderRadius: "8px",
              border: selectedTab === tab.id ? "1px solid var(--forest)" : "1px solid var(--line)",
              background: selectedTab === tab.id ? "var(--forest)" : "#ffffff",
              color: selectedTab === tab.id ? "#ffffff" : "var(--ink)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <Loading label="Loading appointments…" />}

      {!loading && filteredItems.length === 0 && (
        <Empty
          title="No appointments found"
          text={
            selectedTab === "all"
              ? "You have no scheduled visits yet. You can book a site visit directly from any property card or the AI assistant."
              : `No appointments currently marked as ${selectedTab}.`
          }
        />
      )}

      {!loading && filteredItems.length > 0 && (
        <div style={{ display: "grid", gap: "16px" }}>
          {filteredItems.map((item) => {
            const badge = getStatusBadge(item.status);
            const isCancelled = (item.status || "").toLowerCase() === "cancelled";
            const req = item.request as Record<string, any>;
            const propId = String(req.property_id || item.appointment_id.slice(0, 8));
            const photoUrl = getPropertyPhoto(req.property_type || "House", propId);

            // Date processing for the visual calendar block
            const visitDate = new Date(req.starts_at);
            const monthStr = visitDate.toLocaleString("en-US", { month: "short" }).toUpperCase();
            const dayNum = visitDate.getDate();
            const timeStr = visitDate.toLocaleString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
            const weekdayStr = visitDate.toLocaleString("en-US", { weekday: "short" });

            // Host / Agent Details
            const rawAgent = req.agent || req.employee_name;
            const agent = (rawAgent && rawAgent !== "Verified Property Specialist") ? rawAgent : "Property agent";
            const rawAgency = req.agency;
            const agency = (rawAgency && rawAgency !== "Real Estate Hub Partners" && rawAgency !== "Sara AI Support") ? rawAgency : "Mash Allah Estate & Builders";
            const agentInitials = agent
              .split(" ")
              .filter(Boolean)
              .map((w: string) => w[0])
              .join("")
              .slice(0, 2)
              .toUpperCase() || "AG";

            return (
              <div
                key={item.appointment_id}
                className="panel"
                style={{
                  padding: "18px 20px",
                  display: "flex",
                  gap: "20px",
                  alignItems: "stretch",
                  borderRadius: "14px",
                  borderLeft: `5px solid ${badge.color}`,
                  background: "#ffffff",
                  boxShadow: "0 2px 10px rgba(0,0,0,0.03)",
                  flexWrap: "wrap",
                }}
              >
                {/* 1. PROPERTY THUMBNAIL WITH PURPOSE BADGE */}
                <div
                  style={{
                    position: "relative",
                    width: "140px",
                    minWidth: "140px",
                    height: "140px",
                    borderRadius: "10px",
                    overflow: "hidden",
                    flexShrink: 0,
                    boxShadow: "0 2px 6px rgba(0,0,0,0.08)",
                  }}
                >
                  <img
                    src={photoUrl}
                    alt={req.property_name || "Property Visit"}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                  <span
                    style={{
                      position: "absolute",
                      bottom: "6px",
                      left: "6px",
                      background: "rgba(15, 23, 42, 0.8)",
                      backdropFilter: "blur(4px)",
                      color: "#ffffff",
                      fontSize: "0.64rem",
                      fontWeight: 700,
                      padding: "2px 7px",
                      borderRadius: "4px",
                      letterSpacing: "0.03em",
                    }}
                  >
                    {req.purpose === "For Rent" ? "For Rent" : "For Sale"}
                  </span>
                </div>

                {/* 2. MAIN CONTENT BODY */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between", minWidth: "260px" }}>
                  <div>
                    {/* Top row: appointment status and booking reference */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "0.68rem",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            background: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {badge.label}
                        </span>
                        <span style={{ fontSize: "0.74rem", color: "var(--muted)", fontWeight: 500 }}>
                          Ref: #{item.appointment_id.slice(0, 8)}
                        </span>
                      </div>
                      <span style={{ fontSize: "0.72rem", color: "#166534", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#16a34a" }} />
                        Property visit
                      </span>
                    </div>

                    {/* Property Title */}
                    <h3
                      style={{
                        fontFamily: "Playfair Display, serif",
                        fontSize: "1.25rem",
                        fontWeight: 700,
                        margin: "2px 0 8px",
                        color: "var(--ink, #0f172a)",
                        lineHeight: 1.3,
                      }}
                    >
                      {req.property_name || "Property visit"}
                    </h3>

                    {/* Middle Row: Date Block + Property Specs Chips */}
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap", margin: "6px 0 10px" }}>
                      {/* Visual Calendar Date Badge */}
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          background: "#f8fafc",
                          border: "1px solid #e2e8f0",
                          borderRadius: "8px",
                          padding: "3px 8px 3px 3px",
                        }}
                      >
                        <div
                          style={{
                            width: "36px",
                            borderRadius: "6px",
                            overflow: "hidden",
                            border: "1px solid #cbd5e1",
                            background: "#ffffff",
                            textAlign: "center",
                          }}
                        >
                          <div
                            style={{
                              background: "var(--forest, #1e3a2f)",
                              color: "#ffffff",
                              fontSize: "0.58rem",
                              fontWeight: 800,
                              padding: "1px 0",
                              lineHeight: 1.2,
                            }}
                          >
                            {monthStr}
                          </div>
                          <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--ink, #0f172a)", lineHeight: 1.2, padding: "1px 0" }}>
                            {dayNum}
                          </div>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
                          <span style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--ink)" }}>{timeStr}</span>
                          <span style={{ fontSize: "0.68rem", color: "var(--muted)" }}>{weekdayStr} • {req.duration_minutes || 60}m</span>
                        </div>
                      </div>

                      {/* Price Badge */}
                      {req.price && (
                        <span
                          style={{
                            fontWeight: 700,
                            color: "var(--forest, #1e3a2f)",
                            background: "#f0fdf4",
                            padding: "5px 10px",
                            borderRadius: "8px",
                            border: "1px solid #bbf7d0",
                            fontSize: "0.82rem",
                          }}
                        >
                          💰 PKR {Number(req.price).toLocaleString()}{req.purpose === "For Rent" ? " / mo" : ""}
                        </span>
                      )}

                      {/* Area Badge */}
                      {req.area && (
                        <span
                          style={{
                            color: "var(--ink)",
                            background: "#f8fafc",
                            padding: "5px 10px",
                            borderRadius: "8px",
                            border: "1px solid var(--line)",
                            fontSize: "0.82rem",
                            fontWeight: 500,
                          }}
                        >
                          📏 {req.area}
                        </span>
                      )}

                      {/* Beds & Baths Badge */}
                      {req.bedrooms && (
                        <span
                          style={{
                            color: "var(--ink)",
                            background: "#f8fafc",
                            padding: "5px 10px",
                            borderRadius: "8px",
                            border: "1px solid var(--line)",
                            fontSize: "0.82rem",
                            fontWeight: 500,
                          }}
                        >
                          🛏️ {req.bedrooms} Bed{req.bedrooms === 1 ? "" : "s"}{req.bathrooms || req.baths ? `, ${req.bathrooms || req.baths} Bath` : ""}
                        </span>
                      )}

                      {/* Dedicated Agent Micro-Chip */}
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          background: "#f8fafc",
                          border: "1px solid #e2e8f0",
                          borderRadius: "8px",
                          padding: "3px 10px 3px 4px",
                        }}
                      >
                        <div
                          style={{
                            width: "26px",
                            height: "26px",
                            borderRadius: "50%",
                            background: "var(--forest, #1e3a2f)",
                            color: "#ffffff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "0.68rem",
                            fontWeight: 800,
                          }}
                        >
                          {agentInitials}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
                          <span style={{ fontWeight: 600, fontSize: "0.76rem", color: "var(--ink)" }}>{agent}</span>
                          <span style={{ fontSize: "0.66rem", color: "var(--muted)" }}>🏢 {agency}</span>
                        </div>
                      </div>
                    </div>

                    {/* Meeting Notes */}
                    {req.meeting_notes && (
                      <p style={{ margin: "2px 0 0", fontSize: "0.78rem", color: "var(--muted)", fontStyle: "italic" }}>
                        "{req.meeting_notes}"
                      </p>
                    )}
                  </div>

                  {/* 3. GROUPED POLISHED ACTION BUTTONS */}
                  {!isCancelled && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: "10px",
                        marginTop: "12px",
                        paddingTop: "12px",
                        borderTop: "1px solid #f1f5f9",
                      }}
                    >
                      {/* Left: Primary Actions (View Listing, Google Calendar, WhatsApp) */}
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        {req.property_id && (
                          <Link
                            href={`/properties?id=${encodeURIComponent(String(req.property_id))}`}
                            className="button primary"
                            style={{
                              fontSize: "0.78rem",
                              padding: "7px 14px",
                              textDecoration: "none",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                              fontWeight: 600,
                              borderRadius: "8px",
                            }}
                          >
                            👁️ View Listing
                          </Link>
                        )}

                        <a
                          href={getClientGoogleCalendarUrl(item)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            color: "#1d4ed8",
                            textDecoration: "none",
                            fontWeight: 600,
                            background: "#eff6ff",
                            padding: "7px 14px",
                            borderRadius: "8px",
                            border: "1px solid #bfdbfe",
                            fontSize: "0.78rem",
                          }}
                        >
                          📅 Google Calendar ↗
                        </a>

                        <a
                          href={getWhatsAppShareUrl(item)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            color: "#15803d",
                            textDecoration: "none",
                            fontWeight: 600,
                            background: "#f0fdf4",
                            padding: "7px 14px",
                            borderRadius: "8px",
                            border: "1px solid #bbf7d0",
                            fontSize: "0.78rem",
                          }}
                        >
                          💬 WhatsApp
                        </a>
                      </div>

                      {/* Right: Management Actions (Reschedule, Cancel) */}
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <button
                          type="button"
                          onClick={() => {
                            setReschedulingItem(item);
                            setNewDateTime(new Date(item.request.starts_at).toISOString().slice(0, 16));
                          }}
                          className="button"
                          disabled={actionBusy}
                          style={{
                            fontSize: "0.78rem",
                            padding: "7px 13px",
                            background: "#ffffff",
                            border: "1px solid #cbd5e1",
                            borderRadius: "8px",
                            fontWeight: 600,
                          }}
                        >
                          ✏️ Reschedule
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCancel(item)}
                          disabled={actionBusy}
                          style={{
                            fontSize: "0.78rem",
                            padding: "7px 13px",
                            background: "#fff1f2",
                            color: "#be123c",
                            border: "1px solid #fecdd3",
                            borderRadius: "8px",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          ✕ Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {reschedulingItem && (
        <div className="modal-backdrop">
          <div className="modal" style={{ maxWidth: "460px" }}>
            <button
              type="button"
              className="modal-close"
              onClick={() => setReschedulingItem(null)}
            >
              ×
            </button>

            <span className="eyebrow">CHANGE VISIT TIMING</span>
            <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.4rem", margin: "6px 0 12px" }}>
              Reschedule Property Visit
            </h2>
            <p style={{ fontSize: "0.84rem", color: "var(--muted)", marginBottom: "18px" }}>
              {reschedulingItem.request.property_name}
            </p>

            <form onSubmit={handleConfirmReschedule} style={{ display: "grid", gap: "14px" }}>
              <label>
                Select New Date & Time
                <input
                  type="datetime-local"
                  required
                  value={newDateTime}
                  onChange={(e) => setNewDateTime(e.target.value)}
                />
              </label>

              <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                <button
                  type="submit"
                  className="button primary"
                  disabled={actionBusy}
                  style={{ flex: 1 }}
                >
                  {actionBusy ? "Updating..." : "Confirm New Schedule"}
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => setReschedulingItem(null)}
                >
                  Close
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

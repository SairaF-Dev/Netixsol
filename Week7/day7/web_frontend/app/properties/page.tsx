"use client";

import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";
import { PropertyCard, getPropertyPhoto, formatPakistaniPrice } from "@/components/PropertyCard";
import { PropertyDetailModal } from "@/components/PropertyDetailModal";
import { Empty, ErrorNotice, Loading } from "@/components/States";
import type { Property, SearchFilters } from "@/types/api";

const VERIFIED_PROPERTY_TYPES = [
  { value: "House", label: "House" },
  { value: "Apartment", label: "Flat / Apartment" },
  { value: "Upper Portion", label: "Upper Portion" },
  { value: "Lower Portion", label: "Lower Portion" },
  { value: "Farm House", label: "Farm House" },
  { value: "Penthouse", label: "Penthouse" },
  { value: "Room", label: "Room" },
];

export default function Properties() {
  const { customer } = useSession();
  const [rows, setRows] = useState<Property[] | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Filter State
  const [city, setCity] = useState("");
  const [area, setArea] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [bedrooms, setBedrooms] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [purpose, setPurpose] = useState("");

  const search = useCallback(
    async (filters: {
      city?: string;
      area?: string;
      budgetMax?: number;
      bedrooms?: number;
      propertyType?: string;
      purpose?: string;
      offset?: number;
    }) => {
      setBusy(true);
      setError("");

      try {
        const body: SearchFilters = { customer_id: customer?.customer_id, limit: 24, offset: filters.offset ?? 0 };
        if (filters.city) body.city = filters.city;
        if (filters.area) body.area = filters.area;
        if (filters.budgetMax) body.budget_max = filters.budgetMax;
        if (filters.bedrooms) body.bedrooms = filters.bedrooms;
        if (filters.propertyType) body.property_type = filters.propertyType;
        if (filters.purpose) body.purpose = filters.purpose;

        const results = await api.searchProperties(body);
        setRows(results);
        setTotalCount(results[0]?.total_count ?? 0);
        setOffset(filters.offset ?? 0);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not search properties.");
      } finally {
        setBusy(false);
      }
    },
    [customer?.customer_id]
  );

  const [modalProperty, setModalProperty] = useState<Property | null>(null);

  useEffect(() => {
    void search({});
  }, [search]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const urlParams = new URLSearchParams(window.location.search);
    const propId = urlParams.get("id");
    if (!propId) return;

    api.getProperty(propId)
      .then((p) => {
        setModalProperty(p);
      })
      .catch((e) => {
        setError(e instanceof ApiError && e.status === 404 ? "This listing could not be found." : "Could not load this property.");
      });
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    void search({
      city: city.trim() || undefined,
      area: area.trim() || undefined,
      budgetMax: budgetMax ? Number(budgetMax) : undefined,
      bedrooms: bedrooms ? Number(bedrooms) : undefined,
      propertyType: propertyType || undefined,
      purpose: purpose || undefined,
      offset: 0,
    });
  };

  return (
    <>
      <div className="page-title">
        <span className="eyebrow">PROPERTY LISTINGS</span>
        <h1>Explore Properties</h1>
        <p>
          Explore verified listings across Pakistan and find your ideal property at the right price.
        </p>
      </div>

      <form className="search-bar" onSubmit={handleSubmit}>
        <input
          name="city"
          placeholder="City"
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
        <input
          name="area"
          placeholder="Locality"
          value={area}
          onChange={(e) => setArea(e.target.value)}
        />
        <input
          name="budget_max"
          type="number"
          min="0"
          placeholder="Maximum budget"
          value={budgetMax}
          onChange={(e) => setBudgetMax(e.target.value)}
        />
        <input
          name="bedrooms"
          type="number"
          min="0"
          placeholder="Beds"
          value={bedrooms}
          onChange={(e) => setBedrooms(e.target.value)}
        />
        <select
          name="property_type"
          value={propertyType}
          onChange={(e) => setPropertyType(e.target.value)}
        >
          <option value="">Any property type</option>
          {VERIFIED_PROPERTY_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <select
          name="purpose"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
        >
          <option value="">Any purpose</option>
          <option value="purchase">For Sale / Purchase</option>
          <option value="rental">For Rent</option>
        </select>
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Searching…" : "Search"}
        </button>
      </form>

      {rows !== null && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", color: "var(--color-muted)", fontSize: "0.875rem" }}>
          <span>
            Showing <strong>{totalCount === 0 ? 0 : offset + 1}–{Math.min(offset + rows.length, totalCount)}</strong> of {totalCount.toLocaleString()} listings
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }} />
          Property listings
          </span>
        </div>
      )}

      {busy && <Loading label="Searching property listings…" />}
      {error && <ErrorNotice message={error} />}
      {rows?.length === 0 && !busy && (
        <Empty title="No properties match your search" text="Try a broader location or different filters." />
      )}

      <div className="property-grid">
        {rows?.map((x) => (
          <PropertyCard key={x.property_id} property={x} />
        ))}
      </div>
      {totalCount > 24 && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "1rem", margin: "1.5rem 0" }}>
          <button type="button" className="primary" disabled={busy || offset === 0} onClick={() => void search({ city: city.trim() || undefined, area: area.trim() || undefined, budgetMax: budgetMax ? Number(budgetMax) : undefined, bedrooms: bedrooms ? Number(bedrooms) : undefined, propertyType: propertyType || undefined, purpose: purpose || undefined, offset: Math.max(0, offset - 24) })}>Previous</button>
          <span>Page {Math.floor(offset / 24) + 1} of {Math.ceil(totalCount / 24).toLocaleString()}</span>
          <button type="button" className="primary" disabled={busy || offset + 24 >= totalCount} onClick={() => void search({ city: city.trim() || undefined, area: area.trim() || undefined, budgetMax: budgetMax ? Number(budgetMax) : undefined, bedrooms: bedrooms ? Number(bedrooms) : undefined, propertyType: propertyType || undefined, purpose: purpose || undefined, offset: offset + 24 })}>Next</button>
        </div>
      )}

      {modalProperty && (
        <PropertyDetailModal
          property={modalProperty}
          photoUrl={getPropertyPhoto(modalProperty.property_type, modalProperty.property_id)}
          priceFormatted={formatPakistaniPrice(modalProperty.price)}
          onClose={() => setModalProperty(null)}
        />
      )}
    </>
  );
}

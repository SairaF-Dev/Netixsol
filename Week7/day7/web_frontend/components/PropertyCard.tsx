"use client";
import { useState } from "react";
import type { Property } from "@/types/api";
import { PropertyDetailModal } from "@/components/PropertyDetailModal";

const HOUSE_PHOTOS = [
  "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=600&q=80",
];

const APARTMENT_PHOTOS = [
  "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80",
];

const COMMERCIAL_PHOTOS = [
  "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=600&q=80",
];

const PLOT_PHOTOS = [
  "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1524813686514-a57563d77d61?auto=format&fit=crop&w=600&q=80",
];

export function getPropertyPhoto(type: string, id: string): string {
  const normalized = type?.toLowerCase() || "";
  let pool = HOUSE_PHOTOS;

  if (normalized.includes("flat") || normalized.includes("apartment")) {
    pool = APARTMENT_PHOTOS;
  } else if (normalized.includes("commercial")) {
    pool = COMMERCIAL_PHOTOS;
  } else if (normalized.includes("plot")) {
    pool = PLOT_PHOTOS;
  }

  const str = String(id || "0");
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % pool.length;
  return pool[index];
}

export function formatPakistaniPrice(price: number): { compact: string; exact: string } {
  const exact = `PKR ${new Intl.NumberFormat("en-PK").format(price)}`;
  if (!price || isNaN(price)) return { compact: exact, exact };

  if (price >= 10000000) {
    const val = price / 10000000;
    const str = val >= 100 ? Math.round(val).toString() : Number(val.toFixed(2)).toString();
    return { compact: `PKR ${str} Crore`, exact };
  }
  if (price >= 100000) {
    const val = price / 100000;
    const str = val >= 100 ? Math.round(val).toString() : Number(val.toFixed(2)).toString();
    return { compact: `PKR ${str} Lakh`, exact };
  }
  return { compact: exact, exact };
}

function PinIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function BedIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9" />
    </svg>
  );
}

function BathIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M9 6 6.5 3.5a1.5 1.5 0 0 0-2.12 0 1.5 1.5 0 0 0 0 2.12L6.88 8M4 11h16a1 1 0 0 1 1 1v3a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4v-3a1 1 0 0 1 1-1ZM6 19v2M18 19v2" />
    </svg>
  );
}

function TagIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" />
      <path d="M7 7h.01" />
    </svg>
  );
}

function PropertyIllustration({ type }: { type: string }) {
  const normalized = type?.toLowerCase() || "";

  if (normalized.includes("flat") || normalized.includes("apartment")) {
    return (
      <svg width="58" height="58" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Apartment illustration">
        <rect x="18" y="10" width="28" height="46" rx="2" fill="#cbe2d5" stroke="#214e43" strokeWidth="2.5" />
        <rect x="23" y="16" width="6" height="6" rx="1" fill="#ffffff" stroke="#214e43" strokeWidth="1.8" />
        <rect x="35" y="16" width="6" height="6" rx="1" fill="#ffffff" stroke="#214e43" strokeWidth="1.8" />
        <rect x="23" y="26" width="6" height="6" rx="1" fill="#ffffff" stroke="#214e43" strokeWidth="1.8" />
        <rect x="35" y="26" width="6" height="6" rx="1" fill="#ffffff" stroke="#214e43" strokeWidth="1.8" />
        <rect x="28" y="44" width="8" height="12" fill="#9dbfb1" stroke="#214e43" strokeWidth="2" />
        <path d="M8 56H56" stroke="#214e43" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    );
  }

  if (normalized.includes("commercial")) {
    return (
      <svg width="58" height="58" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Commercial illustration">
        <rect x="14" y="14" width="36" height="42" rx="2" fill="#cbe2d5" stroke="#214e43" strokeWidth="2.5" />
        <line x1="20" y1="22" x2="44" y2="22" stroke="#214e43" strokeWidth="2" />
        <line x1="20" y1="30" x2="44" y2="30" stroke="#214e43" strokeWidth="2" />
        <line x1="20" y1="38" x2="44" y2="38" stroke="#214e43" strokeWidth="2" />
        <rect x="26" y="44" width="12" height="12" fill="#9dbfb1" stroke="#214e43" strokeWidth="2" />
        <path d="M6 56H58" stroke="#214e43" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    );
  }

  if (normalized.includes("plot")) {
    return (
      <svg width="58" height="58" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Plot illustration">
        <polygon points="12,46 32,16 52,46" fill="#cbe2d5" stroke="#214e43" strokeWidth="2.5" strokeLinejoin="round" />
        <circle cx="32" cy="30" r="4" fill="#214e43" />
        <path d="M8 52H56" stroke="#214e43" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg width="62" height="62" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="House illustration">
      <path d="M32 8L7 28H15V54C15 55.1 15.9 56 17 56H47C48.1 56 49 55.1 49 54V28H57L32 8Z" fill="#cbe2d5" stroke="#214e43" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M26 56V37C26 35.9 26.9 35 28 35H36C37.1 35 38 35.9 38 37V56" fill="#9dbfb1" stroke="#214e43" strokeWidth="2.5" />
      <rect x="21" y="24" width="7" height="7" rx="1.5" fill="#ffffff" stroke="#214e43" strokeWidth="2" />
      <rect x="36" y="24" width="7" height="7" rx="1.5" fill="#ffffff" stroke="#214e43" strokeWidth="2" />
      <path d="M42 16V12H47V20" stroke="#214e43" strokeWidth="2" strokeLinecap="round" />
      <path d="M5 56H59" stroke="#214e43" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function PropertyCard({ property, actions }: { property: Property; actions?: React.ReactNode }) {
  const [hasError, setHasError] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const photoUrl = getPropertyPhoto(property.property_type, property.property_id);
  const priceFormatted = formatPakistaniPrice(property.price);

  const isRental = property.purpose?.toLowerCase() === "rental";
  const purposeLabel =
    property.purpose === "purchase"
      ? "For Sale"
      : isRental
      ? "For Rent"
      : property.purpose;

  const bedroomsDisplay =
    property.bedrooms != null && property.bedrooms > 0
      ? `${property.bedrooms} Beds`
      : property.property_type?.toLowerCase().includes("plot")
      ? "Plot"
      : property.property_type?.toLowerCase().includes("commercial")
      ? "Commercial"
      : "Studio";

  const bathroomsDisplay =
    property.bathrooms != null && property.bathrooms > 0
      ? `${property.bathrooms} Baths`
      : "—";

  return (
    <>
      <article className="property-card">
        <div
          className="property-visual"
          style={{
            position: "relative",
            overflow: "hidden",
            padding: "12px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            minHeight: "220px",
            cursor: "pointer",
          }}
          onClick={() => setShowDetails(true)}
        >
          {!hasError ? (
            <>
              <img
                src={photoUrl}
                alt={property.property_name}
                className="property-card-img"
                loading="lazy"
                onError={() => setHasError(true)}
              />
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(180deg, rgba(17,35,30,0.5) 0%, transparent 42%, rgba(17,35,30,0.6) 100%)",
                  pointerEvents: "none",
                }}
              />
            </>
          ) : (
            <div
              style={{
                margin: "auto",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "12px 0 4px",
              }}
            >
              <PropertyIllustration type={property.property_type} />
            </div>
          )}

          {/* Top-left: Verified badge */}
          <span
            style={{
              position: "relative",
              zIndex: 2,
              alignSelf: "flex-start",
              fontSize: "0.62rem",
              letterSpacing: "0.06em",
              fontWeight: 700,
              textTransform: "uppercase",
              background: "rgba(255, 255, 255, 0.94)",
              color: "#17332d",
              padding: "4px 9px",
              borderRadius: "20px",
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.18)",
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              backdropFilter: "blur(6px)",
            }}
          >
            Verified
          </span>

          {/* Bottom-left: Property Type overlay chip */}
          <span
            style={{
              position: "relative",
              zIndex: 2,
              alignSelf: "flex-start",
              fontSize: "0.68rem",
              fontWeight: 600,
              letterSpacing: "0.03em",
              background: "rgba(17, 43, 37, 0.85)",
              color: "#ffffff",
              padding: "3px 9px",
              borderRadius: "6px",
              backdropFilter: "blur(6px)",
            }}
          >
            {property.property_type}
          </span>
        </div>

        <div
          className="property-body"
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            height: "100%",
            padding: "16px 18px",
            minWidth: 0,
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          <div style={{ minWidth: 0, width: "100%" }}>
            {/* Location Pin */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                color: "var(--gold)",
                fontSize: "0.74rem",
                fontWeight: 600,
                letterSpacing: "0.02em",
                marginBottom: "3px",
                minWidth: 0,
              }}
            >
              <PinIcon />
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  minWidth: 0,
                }}
              >
                {property.area ? `${property.area}, ${property.city}` : property.city}
              </span>
            </div>

            {/* Title */}
            <h3
              style={{
                font: '600 1.15rem/1.3 "Playfair Display", serif',
                color: "var(--ink)",
                margin: "0 0 6px 0",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                textOverflow: "ellipsis",
                wordBreak: "break-word",
                minHeight: "2.55em",
                cursor: "pointer",
              }}
              title={property.property_name}
              onClick={() => setShowDetails(true)}
            >
              {property.property_name}
            </h3>

            {/* Price Row with /month indicator for rentals */}
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "8px",
                flexWrap: "wrap",
                marginBottom: "10px",
                minWidth: 0,
              }}
            >
              <span
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  color: "var(--forest)",
                  fontFamily: "'DM Sans', sans-serif",
                  letterSpacing: "-0.01em",
                  lineHeight: 1.15,
                  whiteSpace: "nowrap",
                }}
              >
                {priceFormatted.compact}
                {isRental && (
                  <span style={{ fontSize: "0.82rem", fontWeight: 500, color: "#6e827b" }}>
                    {" "}/ mo
                  </span>
                )}
              </span>
              {priceFormatted.compact !== priceFormatted.exact && (
                <span
                  style={{
                    fontSize: "0.73rem",
                    color: "var(--muted)",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                  title={priceFormatted.exact}
                >
                  ({priceFormatted.exact}{isRental ? " / mo" : ""})
                </span>
              )}
            </div>

            {/* Feature Badges */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  fontSize: "0.73rem",
                  fontWeight: 500,
                  background: "#f2f6f4",
                  color: "#254e42",
                  border: "1px solid #d9e7df",
                }}
              >
                <BedIcon />
                <span>{bedroomsDisplay}</span>
              </span>

              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  fontSize: "0.73rem",
                  fontWeight: 500,
                  background: "#f2f6f4",
                  color: "#254e42",
                  border: "1px solid #d9e7df",
                }}
              >
                <BathIcon />
                <span>{bathroomsDisplay}</span>
              </span>

              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "3px 8px",
                  borderRadius: "6px",
                  fontSize: "0.73rem",
                  fontWeight: 500,
                  background: "#faf5ee",
                  color: "#7a5a2e",
                  border: "1px solid #eedec9",
                  textTransform: "capitalize",
                }}
              >
                <TagIcon />
                <span>{purposeLabel}</span>
              </span>
            </div>

            {/* Amenities Chips */}
            {property.amenities && property.amenities.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", marginTop: "8px" }}>
                {property.amenities.slice(0, 3).map((x) => (
                  <span
                    key={x}
                    style={{
                      background: "#f8faf9",
                      border: "1px solid #e1ebe5",
                      color: "#506960",
                      fontSize: "0.68rem",
                      fontWeight: 500,
                      padding: "2px 7px",
                      borderRadius: "4px",
                    }}
                  >
                    {x}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            {/* Footer: Reference ID & View Details */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginTop: "12px",
                paddingTop: "9px",
                borderTop: "1px dashed #e4ebe6",
                minWidth: 0,
                width: "100%",
              }}
            >
              <small style={{ color: "#8c9792", fontSize: "0.72rem", fontWeight: 500 }}>
                Ref: {property.property_id}
              </small>

              <button
                type="button"
                onClick={() => setShowDetails(true)}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "var(--forest)",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                View Details <span aria-hidden="true">→</span>
              </button>
            </div>

            {actions && (
              <div
                className="card-actions"
                style={{
                  marginTop: "8px",
                  paddingTop: "8px",
                  borderTop: "1px solid #edf2ee",
                  width: "100%",
                  display: "block",
                }}
              >
                {actions}
              </div>
            )}
          </div>
        </div>
      </article>

      {showDetails && (
        <PropertyDetailModal
          property={property}
          photoUrl={photoUrl}
          priceFormatted={priceFormatted}
          onClose={() => setShowDetails(false)}
        />
      )}
    </>
  );
}

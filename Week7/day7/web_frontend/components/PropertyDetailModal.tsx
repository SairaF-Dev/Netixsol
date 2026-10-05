"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";
import type { Property } from "@/types/api";

type PropertyDetailModalProps = {
  property: Property;
  photoUrl: string;
  priceFormatted: { compact: string; exact: string };
  onClose: () => void;
};

export function PropertyDetailModal({
  property,
  photoUrl,
  priceFormatted,
  onClose,
}: PropertyDetailModalProps) {
  const router = useRouter();
  const { customer } = useSession();

  const [isBookingOpen, setIsBookingOpen] = useState(false);
  const [visitDate, setVisitDate] = useState("");
  const [meetingNotes, setMeetingNotes] = useState("");
  const [bookingBusy, setBookingBusy] = useState(false);
  const [bookingMessage, setBookingMessage] = useState("");
  const [bookingSuccess, setBookingSuccess] = useState(false);

  const purposeLabel =
    property.purpose === "purchase"
      ? "For Sale"
      : property.purpose === "rental"
      ? "For Rent"
      : property.purpose;

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customer) {
      setBookingMessage("Please log in or select a customer to book a visit.");
      return;
    }
    setBookingBusy(true);
    setBookingMessage("");
    try {
      await api.bookMyAppointment({
        property_id: property.property_id,
        starts_at: new Date(visitDate).toISOString(),
        duration_minutes: 60,
        meeting_notes: meetingNotes,
      });
      setBookingSuccess(true);
      setBookingMessage("Visit scheduled successfully! You can track it under Visits.");
    } catch (err) {
      setBookingMessage(
        err instanceof ApiError ? err.message : "Booking could not be completed."
      );
    } finally {
      setBookingBusy(false);
    }
  };

  const handleAskSara = () => {
    onClose();
    router.push("/sara");
  };

  const mapsQuery = encodeURIComponent(`${property.area} ${property.city}`);
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      style={{
        zIndex: 50,
        backgroundColor: "rgba(11, 31, 26, 0.72)",
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          position: "relative",
          width: "min(640px, 94vw)",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "#ffffff",
          borderRadius: "16px",
          boxShadow: "0 22px 50px rgba(17, 35, 30, 0.25)",
          color: "var(--ink)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero Photo Banner */}
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "230px",
            overflow: "hidden",
            backgroundColor: "#214e43",
          }}
        >
          <img
            src={photoUrl}
            alt={property.property_name}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
          {/* Gradient Overlay */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(180deg, rgba(17,35,30,0.55) 0%, transparent 45%, rgba(17,35,30,0.7) 100%)",
            }}
          />

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            style={{
              position: "absolute",
              top: "14px",
              right: "14px",
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.95)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#17332d",
              zIndex: 10,
              boxShadow: "0 2px 8px rgba(0,0,0,0.22)",
              padding: 0,
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>

          {/* Verified Pill */}
          <span
            style={{
              position: "absolute",
              top: "14px",
              left: "14px",
              fontSize: "0.65rem",
              letterSpacing: "0.06em",
              fontWeight: 700,
              textTransform: "uppercase",
              background: "rgba(255, 255, 255, 0.95)",
              color: "#17332d",
              padding: "4px 10px",
              borderRadius: "20px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.18)",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#16a34a",
                boxShadow: "0 0 6px rgba(22, 163, 74, 0.8)",
              }}
            />
            Verified Listing
          </span>

          {/* Property Type and Purpose Pills */}
          <div
            style={{
              position: "absolute",
              bottom: "12px",
              left: "14px",
              display: "flex",
              gap: "8px",
            }}
          >
            <span
              style={{
                fontSize: "0.72rem",
                fontWeight: 600,
                background: "rgba(17, 43, 37, 0.85)",
                color: "#ffffff",
                padding: "3px 10px",
                borderRadius: "6px",
                backdropFilter: "blur(4px)",
              }}
            >
              {property.property_type}
            </span>
            <span
              style={{
                fontSize: "0.72rem",
                fontWeight: 600,
                background: "rgba(194, 139, 75, 0.9)",
                color: "#ffffff",
                padding: "3px 10px",
                borderRadius: "6px",
                textTransform: "capitalize",
              }}
            >
              {purposeLabel}
            </span>
          </div>
        </div>

        {/* Modal Content */}
        <div style={{ padding: "24px" }}>
          {/* Location row with Google Maps link */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "10px",
              marginBottom: "8px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                color: "var(--gold)",
                fontSize: "0.82rem",
                fontWeight: 600,
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              <span>
                {property.area}, {property.city}
              </span>
            </div>

            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: "0.75rem",
                color: "var(--forest)",
                fontWeight: 600,
                textDecoration: "underline",
                textUnderlineOffset: "2px",
                display: "inline-flex",
                alignItems: "center",
                gap: "3px",
              }}
            >
              View on Google Maps ↗
            </a>
          </div>

          {/* Title */}
          <h2
            style={{
              font: '600 1.45rem/1.3 "Playfair Display", serif',
              color: "var(--ink)",
              margin: "0 0 12px 0",
            }}
          >
            {property.property_name}
          </h2>

          {/* Price Header */}
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "10px",
              paddingBottom: "16px",
              borderBottom: "1px solid #e5ebe7",
              marginBottom: "18px",
            }}
          >
            <span
              style={{
                fontSize: "1.6rem",
                fontWeight: 700,
                color: "var(--forest)",
                fontFamily: "'DM Sans', sans-serif",
                letterSpacing: "-0.01em",
              }}
            >
              {priceFormatted.compact}
            </span>
            {priceFormatted.compact !== priceFormatted.exact && (
              <span
                style={{
                  fontSize: "0.84rem",
                  color: "var(--muted)",
                  fontWeight: 500,
                }}
              >
                ({priceFormatted.exact})
              </span>
            )}
          </div>

          {/* Grounded Specifications Grid */}
          <div style={{ marginBottom: "22px" }}>
            <h4
              style={{
                fontSize: "0.76rem",
                letterSpacing: "0.08em",
                fontWeight: 700,
                textTransform: "uppercase",
                color: "var(--muted)",
                margin: "0 0 10px 0",
              }}
            >
              Key Specifications
            </h4>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "10px",
              }}
            >
              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Bedrooms</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)", marginTop: "2px" }}>
                  {property.bedrooms != null ? `${property.bedrooms} Beds` : "Studio / N/A"}
                </div>
              </div>

              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Bathrooms</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)", marginTop: "2px" }}>
                  {property.bathrooms != null ? `${property.bathrooms} Baths` : "—"}
                </div>
              </div>

              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Property Type</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)", marginTop: "2px" }}>
                  {property.property_type}
                </div>
              </div>

              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Purpose</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)", marginTop: "2px", textTransform: "capitalize" }}>
                  {purposeLabel}
                </div>
              </div>

              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>MLS Status</div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: property.available ? "#16a34a" : "#b91c1c", marginTop: "2px" }}>
                  {property.available ? "Active & Available" : "Under Contract"}
                </div>
              </div>

              <div
                style={{
                  background: "#f7faf8",
                  border: "1px solid #e1ebe5",
                  borderRadius: "8px",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Reference ID</div>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#546e63", marginTop: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={property.property_id}>
                  {property.property_id}
                </div>
              </div>
            </div>
          </div>

          {/* Full Verified Amenities (Every item in database) */}
          <div style={{ marginBottom: "22px" }}>
            <h4
              style={{
                fontSize: "0.76rem",
                letterSpacing: "0.08em",
                fontWeight: 700,
                textTransform: "uppercase",
                color: "var(--muted)",
                margin: "0 0 10px 0",
              }}
            >
              Verified Amenities ({property.amenities.length})
            </h4>

            {property.amenities.length > 0 ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {property.amenities.map((amenity) => (
                  <span
                    key={amenity}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "#f0f6f2",
                      color: "#1f4a3e",
                      border: "1px solid #cce2d6",
                      padding: "5px 11px",
                      borderRadius: "7px",
                      fontSize: "0.76rem",
                      fontWeight: 500,
                    }}
                  >
                    <span style={{ color: "#16a34a", fontWeight: 700 }}>✓</span>
                    {amenity}
                  </span>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: 0 }}>
                Standard residential amenities included with this property listing.
              </p>
            )}
          </div>

          {/* Inline Booking Visit Section */}
          {isBookingOpen && (
            <div
              style={{
                background: "#fdfbf7",
                border: "1px solid #eeddc8",
                borderRadius: "10px",
                padding: "16px",
                marginBottom: "20px",
              }}
            >
              <h4 style={{ fontSize: "0.92rem", fontWeight: 700, color: "#6e4b1f", margin: "0 0 12px 0" }}>
                📅 Schedule a Property Site Visit
              </h4>

              <form onSubmit={handleBookingSubmit} style={{ display: "grid", gap: "12px" }}>
                <label style={{ fontSize: "0.78rem", fontWeight: 700 }}>
                  Select Date & Time
                  <input
                    type="datetime-local"
                    required
                    value={visitDate}
                    onChange={(e) => setVisitDate(e.target.value)}
                    style={{ marginTop: "4px" }}
                  />
                </label>

                <label style={{ fontSize: "0.78rem", fontWeight: 700 }}>
                  Meeting Notes or Special Instructions
                  <textarea
                    rows={2}
                    placeholder="e.g. Interested in morning inspection, please bring floor plan."
                    value={meetingNotes}
                    maxLength={2000}
                    onChange={(e) => setMeetingNotes(e.target.value)}
                    style={{ marginTop: "4px" }}
                  />
                </label>

                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <button
                    type="submit"
                    className="primary"
                    disabled={bookingBusy || bookingSuccess}
                    style={{ fontSize: "0.85rem", padding: "8px 14px" }}
                  >
                    {bookingBusy ? "Confirming Visit…" : bookingSuccess ? "Visit Booked ✓" : "Confirm Visit"}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setIsBookingOpen(false)}
                    style={{ fontSize: "0.85rem", padding: "8px 14px" }}
                  >
                    Cancel
                  </button>
                </div>

                {bookingMessage && (
                  <div
                    className="notice"
                    style={{
                      marginTop: "6px",
                      background: bookingSuccess ? "#dfefe5" : "#f8e8e5",
                      color: bookingSuccess ? "#246148" : "var(--danger)",
                      fontSize: "0.8rem",
                      padding: "8px 12px",
                      borderRadius: "6px",
                    }}
                  >
                    {bookingMessage}
                  </div>
                )}
              </form>
            </div>
          )}

          {/* Action CTAs */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "10px",
              paddingTop: "14px",
              borderTop: "1px solid #e5ebe7",
            }}
          >
            {!isBookingOpen && !bookingSuccess && (
              <button
                type="button"
                className="primary"
                onClick={() => setIsBookingOpen(true)}
                style={{ fontSize: "0.86rem", display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <span>📅</span> Book a Site Visit
              </button>
            )}

            <button
              type="button"
              className="button"
              onClick={handleAskSara}
              style={{
                fontSize: "0.86rem",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                borderColor: "#ccd7d2",
              }}
            >
              <span>💬</span> Inquire with Sara AI
            </button>

            <button
              type="button"
              className="ghost"
              onClick={onClose}
              style={{ marginLeft: "auto", fontSize: "0.86rem" }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

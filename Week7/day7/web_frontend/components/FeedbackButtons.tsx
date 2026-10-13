"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { InteractionAction } from "@/types/api";

export function FeedbackButtons({
  customerId,
  propertyId,
  sessionId,
  onBook,
}: {
  customerId?: string;
  propertyId: string;
  sessionId: string;
  onBook: () => void;
}) {
  const [saved, setSaved] = useState<InteractionAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = async (action: InteractionAction) => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (customerId) await api.recordInteraction(customerId, propertyId, action, sessionId);
      else await api.recordMyInteraction(propertyId, action, sessionId);
      setSaved(action);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save feedback.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "5px", width: "100%" }}>
        <button
          type="button"
          disabled={busy}
          onClick={() => send("liked")}
          style={{
            padding: "6px 2px",
            fontSize: "0.72rem",
            fontWeight: 600,
            background: saved === "liked" ? "#e2f3e8" : "#ffffff",
            color: saved === "liked" ? "#195733" : "var(--ink)",
            borderColor: saved === "liked" ? "#88cfa2" : "#d8dfdb",
            borderRadius: "6px",
            textAlign: "center",
          }}
        >
          {saved === "liked" ? "Liked ✓" : "Like"}
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={() => send("rejected")}
          style={{
            padding: "6px 2px",
            fontSize: "0.72rem",
            fontWeight: 600,
            background: saved === "rejected" ? "#fae8e6" : "#ffffff",
            color: saved === "rejected" ? "var(--danger)" : "var(--ink)",
            borderColor: saved === "rejected" ? "#f1a89f" : "#d8dfdb",
            borderRadius: "6px",
            textAlign: "center",
          }}
        >
          {saved === "rejected" ? "Rejected ✓" : "Reject"}
        </button>

        <button
          type="button"
          disabled={busy}
          onClick={() => send("shortlisted")}
          style={{
            padding: "6px 2px",
            fontSize: "0.72rem",
            fontWeight: 600,
            background: saved === "shortlisted" ? "#fef5e7" : "#ffffff",
            color: saved === "shortlisted" ? "#8a5712" : "var(--ink)",
            borderColor: saved === "shortlisted" ? "#f8c77e" : "#d8dfdb",
            borderRadius: "6px",
            textAlign: "center",
          }}
        >
          {saved === "shortlisted" ? "Shortlisted ✓" : "Shortlist"}
        </button>
      </div>

      <button
        type="button"
        className="primary"
        onClick={onBook}
        style={{
          width: "100%",
          padding: "7px 10px",
          fontSize: "0.76rem",
          fontWeight: 600,
          borderRadius: "6px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "5px",
        }}
      >
        <span>📅</span> Book visit
      </button>

      {error && <small className="inline-error">{error}</small>}
    </div>
  );
}

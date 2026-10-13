"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { mlApi, MlApiError, type ChatResponse } from "@/lib/mlApi";
import { api } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";
import { BookVisit } from "@/components/BookVisit";
import type { Property } from "@/types/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
  meta?: ChatResponse;
}

const EXAMPLE_PROMPTS = [
  {
    tag: "Valuation",
    label: "🏡 DHA Lahore Price",
    query: "Lahore DHA Phase 5 mein 10 marla house ki fair price kiya hai?",
  },
  {
    tag: "Rental",
    label: "🏢 Clifton Rent",
    query: "Karachi Clifton mein 10 marla flat ka rent kitna hona chahiye?",
  },
  {
    tag: "Lead",
    label: "👥 Score Lead",
    query: "Score this lead: Facebook lead from Islamabad, budget 3 crore, 5 calls, visit booked.",
  },
  {
    tag: "Market",
    label: "📊 DHA Rates",
    query: "What is the average price per marla in DHA Lahore for sale?",
  },
  {
    tag: "Search",
    label: "🔍 Find Houses",
    query: "Show me 3 comparable houses for sale in Lahore with 5 marla area.",
  },
];

function formatToolName(raw: string): string {
  const map: Record<string, string> = {
    price_predictor_tool: "⚡ Price Valuation Engine",
    lead_scorer_tool: "👥 Deal Qualification Scorer",
    explainer_tool: "💡 Decision Attribution Driver",
    comparable_properties_tool: "🏡 Property Listings",
    market_stats_tool: "📊 Metropolitan Market Index",
  };
  return map[raw] || raw;
}

export default function AssistantPage() {
  const { customer } = useSession();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      role: "assistant",
      text: "Assalam-o-Alaikum! Main aapki AI Real Estate Copilot hoon. Aap mujh se Pakistani market mein kisi bhi property ki fair price valuation, rental estimate, lead qualification score, ya market statistics poch sakte hain (English ya UrduLish mein).",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId] = useState<string>("conv-" + Date.now());

  const [contextProperties, setContextProperties] = useState<Property[]>([]);
  const [shortlisted, setShortlisted] = useState<string[]>([]);
  const [bookingProperty, setBookingProperty] = useState<Property | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    async function loadInitialProperties() {
      try {
        const res = await api.searchProperties({ limit: 4 });
        if (res && res.length) {
          setContextProperties(res);
        }
      } catch {
        // Fallback gracefully
      }
    }
    loadInitialProperties();
  }, []);

  const handleSend = async (messageToSend?: string) => {
    const text = (messageToSend || input).trim();
    if (!text || busy) return;

    const userMsg: ChatMessage = {
      id: "usr-" + Date.now(),
      role: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setError(null);
    setBusy(true);

    try {
      const response = await mlApi.chatAssistant(text, conversationId);

      const assistantMsg: ChatMessage = {
        id: "ast-" + Date.now(),
        role: "assistant",
        text: response.response,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        meta: response,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      if (text.toLowerCase().includes("lahore") || text.toLowerCase().includes("dha")) {
        api.searchProperties({ city: "Lahore", limit: 4 }).then((res) => {
          if (res?.length) setContextProperties(res);
        }).catch(() => {});
      } else if (text.toLowerCase().includes("karachi") || text.toLowerCase().includes("clifton")) {
        api.searchProperties({ city: "Karachi", limit: 4 }).then((res) => {
          if (res?.length) setContextProperties(res);
        }).catch(() => {});
      } else if (text.toLowerCase().includes("islamabad") || text.toLowerCase().includes("f-10")) {
        api.searchProperties({ city: "Islamabad", limit: 4 }).then((res) => {
          if (res?.length) setContextProperties(res);
        }).catch(() => {});
      }
    } catch (err: any) {
      setError(
        err instanceof MlApiError
          ? err.message
          : "The assistant could not process your request. Please check your connection and try again."
      );
    } finally {
      setBusy(false);
    }
  };

  const toggleShortlist = (propertyId: string) => {
    setShortlisted((prev) =>
      prev.includes(propertyId) ? prev.filter((id) => id !== propertyId) : [...prev, propertyId]
    );
  };

  const lastAssistantMeta = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].meta) {
        return messages[i].meta;
      }
    }
    return null;
  }, [messages]);

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <span className="eyebrow">LANGGRAPH AGENT COPILOT</span>
          <h1 style={{ fontFamily: "Playfair Display, serif", fontSize: "clamp(1.8rem, 3vw, 2.3rem)", margin: "4px 0" }}>
            AI Real Estate Assistant
          </h1>
          <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.88rem" }}>
            Search property listings, explore indicative prices, and plan site visits in English or Urdu.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "0.74rem", background: "#e8f2ee", color: "#214e43", padding: "4px 10px", borderRadius: "14px", fontWeight: 700 }}>
            ● LangGraph Dual-Agent
          </span>
          {lastAssistantMeta?.guard_triggered && (
            <span style={{ fontSize: "0.74rem", background: "#fef3c7", color: "#92400e", padding: "4px 10px", borderRadius: "14px", fontWeight: 700 }}>
              🛡️ Numeric Fact Guard Active
            </span>
          )}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.35fr) minmax(340px, 0.95fr)",
          gap: "20px",
          alignItems: "start",
        }}
        className="assistant-split-layout"
      >
        <div
          className="panel"
          style={{
            padding: 0,
            display: "flex",
            flexDirection: "column",
            height: "76vh",
            minHeight: "560px",
            overflow: "hidden",
            boxShadow: "0 6px 24px rgba(23, 51, 45, 0.05)",
          }}
        >
          <div
            className="crm-scrollbar"
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "20px 22px",
              display: "grid",
              gap: "16px",
              alignContent: "start",
            }}
          >
            {messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "88%",
                      padding: "14px 16px",
                      borderRadius: isUser ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                      background: isUser ? "var(--forest)" : "#f6f8f7",
                      color: isUser ? "#ffffff" : "var(--ink)",
                      border: isUser ? "none" : "1px solid #e1e7e4",
                      fontSize: "0.92rem",
                      lineHeight: "1.6",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      boxShadow: isUser ? "0 2px 8px rgba(33, 78, 67, 0.2)" : "0 1px 4px rgba(0,0,0,0.02)",
                    }}
                  >
                    {m.text}
                  </div>

                  {m.meta?.tool_calls && m.meta.tool_calls.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                      {m.meta.tool_calls.map((tool, idx) => (
                        <span
                          key={idx}
                          style={{
                            fontSize: "0.68rem",
                            background: "#e8edea",
                            color: "var(--forest)",
                            padding: "2px 8px",
                            borderRadius: "10px",
                            fontWeight: 600,
                          }}
                        >
                          {formatToolName(tool)}
                        </span>
                      ))}
                    </div>
                  )}

                  <span style={{ fontSize: "0.65rem", color: "var(--muted)", marginTop: "4px", padding: "0 4px" }}>
                    {m.timestamp}
                  </span>
                </div>
              );
            })}

            {busy && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 4px" }}>
                <div className="spinner" style={{ width: "18px", height: "18px", borderWidth: "2px" }} />
                <span style={{ fontSize: "0.84rem", color: "var(--muted)", fontStyle: "italic" }}>
                  Sara is checking property and market information…
                </span>
              </div>
            )}

            {error && (
              <div style={{ padding: "10px 14px", background: "#fdf2f2", color: "#991b1b", borderRadius: "8px", fontSize: "0.82rem", border: "1px solid #fecaca" }}>
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div
            style={{
              padding: "8px 16px",
              background: "#fafbfb",
              borderTop: "1px solid var(--line)",
              display: "flex",
              gap: "6px",
              overflowX: "auto",
              whiteSpace: "nowrap",
            }}
          >
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p.tag}
                type="button"
                onClick={() => handleSend(p.query)}
                disabled={busy}
                style={{
                  fontSize: "0.72rem",
                  padding: "4px 10px",
                  borderRadius: "16px",
                  background: "#ffffff",
                  border: "1px solid var(--line)",
                  color: "var(--ink)",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{
              display: "flex",
              gap: "8px",
              padding: "12px 16px",
              background: "#ffffff",
              borderTop: "1px solid var(--line)",
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything in English or UrduLish (e.g. 'Lahore 10 marla house price?')"
              disabled={busy}
              style={{
                flex: 1,
                fontSize: "0.9rem",
                padding: "11px 14px",
                borderRadius: "8px",
                border: "1px solid #ccd7d2",
              }}
            />
            <button
              type="submit"
              className="button primary"
              disabled={busy || !input.trim()}
              style={{ padding: "10px 20px", display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <span>Send</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>

        <div
          className="panel"
          style={{
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            height: "76vh",
            minHeight: "560px",
            overflow: "hidden",
            boxShadow: "0 6px 24px rgba(23, 51, 45, 0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span className="eyebrow">PROPERTY SUGGESTIONS</span>
              <h2 style={{ fontFamily: "Playfair Display, serif", fontSize: "1.25rem", margin: "2px 0 0" }}>
                Matching Properties
              </h2>
            </div>
            <span style={{ fontSize: "0.72rem", color: "var(--muted)", background: "#e8edea", padding: "3px 8px", borderRadius: "10px", fontWeight: 700 }}>
              {contextProperties.length} listings
            </span>
          </div>

          <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--muted)" }}>
            Listings synchronized with your conversation topic and search parameters:
          </p>

          <div
            className="crm-scrollbar"
            style={{
              flex: 1,
              overflowY: "auto",
              display: "grid",
              gap: "14px",
              paddingRight: "4px",
            }}
          >
            {contextProperties.map((prop) => {
              const isShortlisted = shortlisted.includes(prop.property_id);
              return (
                <div
                  key={prop.property_id}
                  style={{
                    background: "#ffffff",
                    border: "1px solid var(--line)",
                    borderRadius: "10px",
                    padding: "14px",
                    display: "grid",
                    gap: "10px",
                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.02)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                    <div>
                      <span style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--gold)", fontWeight: 700 }}>
                        {prop.property_type || "House"} • {prop.city}
                      </span>
                      <h4 style={{ margin: "3px 0 2px", fontSize: "0.95rem", fontWeight: 700, color: "var(--ink)" }}>
                        {prop.area || prop.city || "Prime Location"}
                      </h4>
                      <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>
                        ID: {prop.property_id.slice(0, 8)}...
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleShortlist(prop.property_id)}
                      title={isShortlisted ? "Remove from shortlist" : "Add to shortlist"}
                      style={{
                        background: isShortlisted ? "#fef3c7" : "transparent",
                        border: "1px solid",
                        borderColor: isShortlisted ? "#f59e0b" : "var(--line)",
                        borderRadius: "50%",
                        width: "28px",
                        height: "28px",
                        display: "grid",
                        placeItems: "center",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                      }}
                    >
                      {isShortlisted ? "★" : "☆"}
                    </button>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px dashed #e8edea", paddingTop: "8px" }}>
                    <div>
                      <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>Listed price</div>
                      <div style={{ fontFamily: "Playfair Display, serif", fontWeight: 700, fontSize: "1.05rem", color: "var(--forest)" }}>
                        PKR {prop.price ? (prop.price >= 10000000 ? `${(prop.price / 10000000).toFixed(2)} Cr` : `${(prop.price / 100000).toFixed(1)} Lakh`) : "Price on Request"}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "6px", fontSize: "0.72rem", color: "var(--muted)" }}>
                      {prop.bedrooms && <span>🛏️ {prop.bedrooms} Bed</span>}
                      {prop.bathrooms && <span>🚿 {prop.bathrooms} Bath</span>}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", marginTop: "2px" }}>
                    <button
                      type="button"
                      onClick={() => setBookingProperty(prop)}
                      className="button primary"
                      style={{ flex: 1, padding: "7px 10px", fontSize: "0.75rem", textAlign: "center" }}
                    >
                      📅 Book Visit
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {bookingProperty && customer && (
            <BookVisit
              customerId={customer.customer_id}
              property={bookingProperty}
              close={() => setBookingProperty(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

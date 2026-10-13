"use client";

import { useState, useRef, useEffect } from "react";
import { mlApi, MlApiError, type ChatResponse } from "@/lib/mlApi";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  responseMeta?: ChatResponse;
}

interface ExamplePrompt {
  tag: string;
  query: string;
  icon: string;
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    tag: "Valuation",
    icon: "🏷️",
    query: "Lahore DHA Phase 5 mein 10 marla house ki fair price kiya hai?",
  },
  {
    tag: "Rental",
    icon: "🔑",
    query: "Karachi Clifton mein 10 marla flat ka rent kitna hona chahiye?",
  },
  {
    tag: "Lead CRM",
    icon: "⚡",
    query: "Score this lead: Facebook lead from Islamabad, budget 3 crore, 5 calls, visit booked.",
  },
  {
    tag: "Market Data",
    icon: "📊",
    query: "What is the average price per marla in DHA Lahore for sale?",
  },
  {
    tag: "Comparables",
    icon: "🏡",
    query: "Show me 3 comparable houses for sale in Lahore with 5 marla area.",
  },
];

function formatToolName(raw: string): string {
  const map: Record<string, string> = {
    price_predictor_tool: "⚡ Price Estimate",
    lead_scorer_tool: "👥 Lead Follow-Up",
    explainer_tool: "💡 Key Factors",
    comparable_properties_tool: "🏡 Property Listings",
    market_stats_tool: "📊 Market Overview",
  };
  return map[raw] || raw;
}

function formatIntentName(raw: string): string {
  const map: Record<string, string> = {
    valuation: "Property Valuation",
    lead_scoring: "Lead Qualification",
    market_stats: "Market Intelligence",
    property_search: "Listing Discovery",
    general_inquiry: "General Assistant",
  };
  return map[raw] || raw;
}

function getFollowUps(intent?: string, text?: string): string[] {
  const t = (text || "").toLowerCase();
  if (intent === "valuation" || t.includes("fair value") || t.includes("fair price")) {
    return [
      "What is the average price per marla in DHA Lahore for sale?",
      "Karachi Clifton mein 10 marla flat ka rent kitna hona chahiye?",
      "Show me 3 comparable houses for sale in Lahore with 5 marla area.",
    ];
  }
  if (intent === "lead_scoring" || t.includes("lead")) {
    return [
      "Lahore DHA Phase 5 mein 10 marla house ki fair price kiya hai?",
      "What is the average price per marla in DHA Lahore for sale?",
    ];
  }
  if (intent === "market_stats") {
    return [
      "Show me 3 comparable houses for sale in Lahore with 5 marla area.",
      "Score this lead: Facebook lead from Islamabad, budget 3 crore, 5 calls, visit booked.",
    ];
  }
  return [
    "Lahore DHA Phase 5 mein 10 marla house ki fair price kiya hai?",
    "Karachi Clifton mein 10 marla flat ka rent kitna hona chahiye?",
  ];
}

export default function AssistantChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string>("conv-" + Date.now());
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function handleSend(queryText?: string) {
    const textToSend = (queryText || input).trim();
    if (!textToSend || busy) return;

    setInput("");
    setError(null);
    setBusy(true);

    const userMsg: ChatMessage = { role: "user", text: textToSend };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await mlApi.chatAssistant(textToSend, conversationId);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        text: res.response,
        responseMeta: res,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(
        err instanceof MlApiError
          ? err.message
          : "Failed to communicate with AI Assistant."
      );
    } finally {
      setBusy(false);
    }
  }

  function handleCopy(text: string, idx: number) {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => {
      setCopiedIdx(null);
    }, 2200);
  }

  // Parse structured sections from assistant text
  function renderStructuredContent(rawText: string) {
    const lines = rawText.split("\n");
    const mainLines: string[] = [];
    const listingLines: string[] = [];
    const footnoteLines: string[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (trimmed.startsWith("- ID #") || trimmed.match(/^-?\s*ID\s*#\d+/i)) {
        listingLines.push(trimmed);
      } else if (
        trimmed.toLowerCase().startsWith("explanation note:") ||
        trimmed.toLowerCase().startsWith("disclaimer:")
      ) {
        footnoteLines.push(trimmed);
      } else {
        mainLines.push(trimmed);
      }
    }

    return (
      <div style={{ display: "grid", gap: "12px" }}>
        {/* Main Text / Overview */}
        <div style={{ lineHeight: 1.6, fontSize: "0.92rem", color: "var(--ink)" }}>
          {mainLines.map((ml, i) => (
            <p key={i} style={{ margin: "0 0 8px" }}>
              {ml}
            </p>
          ))}
        </div>

        {/* Comparable Listings Cards */}
        {listingLines.length > 0 && (
          <div style={{ marginTop: "4px" }}>
            <span
              style={{
                fontSize: "0.72rem",
                fontWeight: 700,
                color: "#c28b4b",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                display: "block",
                marginBottom: "8px",
              }}
            >
              Property Listings:
            </span>
            <div style={{ display: "grid", gap: "8px" }}>
              {listingLines.map((l, li) => {
                const clean = l.replace(/^-\s*/, "");
                return (
                  <div
                    key={li}
                    style={{
                      background: "#faf9f6",
                      border: "1px solid #e8e3d8",
                      borderRadius: "8px",
                      padding: "10px 14px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "6px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "1.1rem" }}>🏡</span>
                      <strong style={{ fontSize: "0.85rem", color: "var(--forest)" }}>{clean}</strong>
                    </div>
                    <span
                      style={{
                        fontSize: "0.68rem",
                        background: "#e6f4ea",
                        color: "#137333",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontWeight: 600,
                      }}
                    >
                      Listing
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Footnote / Disclaimer Box */}
        {footnoteLines.length > 0 && (
          <div
            style={{
              marginTop: "4px",
              padding: "10px 14px",
              background: "#faf9f6",
              border: "1px dashed #dce2dc",
              borderRadius: "8px",
              fontSize: "0.76rem",
              color: "var(--muted)",
              lineHeight: 1.45,
            }}
          >
            {footnoteLines.map((fl, fi) => (
              <p key={fi} style={{ margin: "2px 0" }}>
                {fl}
              </p>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <section className="ml-assistant-page">
      {/* Executive Header */}
      <div className="page-title row" style={{ marginBottom: "26px" }}>
        <div>
          <span className="eyebrow" style={{ color: "#c28b4b", fontWeight: 700, letterSpacing: "0.14em" }}>
            ENTERPRISE REAL ESTATE COPILOT
          </span>
          <h1 style={{ margin: "10px 0 12px", fontFamily: "Playfair Display" }}>
            Sara AI • Real Estate Co-Pilot
          </h1>
          <p style={{ maxWidth: "620px", color: "var(--muted)", lineHeight: 1.6, fontSize: "0.95rem" }}>
            Get property price estimates, browse listings, review lead follow-up suggestions, and explore market information in English or UrduLish.
          </p>
        </div>
        <button
          type="button"
          className="button"
          onClick={() => {
            setMessages([]);
            setConversationId("conv-" + Date.now());
            setError(null);
          }}
          disabled={busy}
          style={{
            fontSize: "0.82rem",
            padding: "8px 16px",
            borderRadius: "8px",
            fontWeight: 600,
            background: "white",
            border: "1px solid #dce2dc",
          }}
        >
          ↻ New Conversation
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.35fr 0.65fr", gap: "28px", alignItems: "start" }}>
        {/* Main Chat Flow */}
        <div className="panel" style={{ minHeight: "620px", display: "flex", flexDirection: "column", padding: "26px", borderRadius: "14px" }}>
          {/* Chat Messages Container */}
          <div style={{ flex: 1, overflowY: "auto", display: "grid", gap: "20px", marginBottom: "20px", maxHeight: "640px" }}>
            {messages.length === 0 && (
              <div style={{ textAlign: "center", padding: "50px 16px", color: "var(--muted)" }}>
                <span style={{ fontSize: "2.8rem" }}>✨</span>
                <h3 style={{ fontFamily: "Playfair Display", color: "var(--ink)", margin: "14px 0 6px", fontSize: "1.35rem" }}>
                  Enterprise Co-Pilot Ready
                </h3>
                <p style={{ maxWidth: "440px", margin: "auto", fontSize: "0.88rem", lineHeight: 1.5 }}>
                  Ask questions about property values, rental yields, buyer qualification, or metropolitan statistics in English or UrduLish.
                </p>

                {/* Quick Starter Cards */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "24px", textAlign: "left" }}>
                  {EXAMPLE_PROMPTS.slice(0, 4).map((ep, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSend(ep.query)}
                      style={{
                        padding: "12px 14px",
                        background: "#faf9f6",
                        border: "1px solid #e8e3d8",
                        borderRadius: "10px",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.72rem", fontWeight: 700, color: "#c28b4b", textTransform: "uppercase" }}>
                        <span>{ep.icon}</span>
                        <span>{ep.tag}</span>
                      </div>
                      <p style={{ margin: "6px 0 0", fontSize: "0.78rem", color: "var(--ink)", lineHeight: 1.4 }}>
                        &ldquo;{ep.query}&rdquo;
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, idx) => {
              const followUps = m.role === "assistant" ? getFollowUps(m.responseMeta?.intent, m.text) : [];

              return (
                <div key={idx} style={{ display: "grid", gap: "8px" }}>
                  <div
                    style={{
                      padding: "18px 20px",
                      borderRadius: "12px",
                      background: m.role === "user" ? "#faf9f6" : "white",
                      border: m.role === "user" ? "1px solid #ebe6dd" : "1.5px solid #dce8e3",
                      borderLeft: m.role === "assistant" ? "4px solid var(--forest)" : "1px solid #ebe6dd",
                      boxShadow: m.role === "assistant" ? "0 4px 16px rgba(23, 51, 45, 0.05)" : "none",
                    }}
                  >
                    {/* Header Row */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "1.1rem" }}>{m.role === "user" ? "👤" : "✨"}</span>
                        <strong style={{ fontSize: "0.92rem", color: "var(--ink)" }}>
                          {m.role === "user" ? "Sales Agent" : "Sara AI Co-Pilot"}
                        </strong>
                      </div>

                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        {m.responseMeta && (
                          <span
                            style={{
                              fontSize: "0.7rem",
                              fontWeight: 700,
                              padding: "3px 10px",
                              borderRadius: "12px",
                              background: "#e8f5e9",
                              color: "#2e7d32",
                            }}
                          >
                            {formatIntentName(m.responseMeta.intent)}
                          </span>
                        )}

                        {/* Copy for WhatsApp Button */}
                        {m.role === "assistant" && (
                          <button
                            type="button"
                            onClick={() => handleCopy(m.text, idx)}
                            style={{
                              fontSize: "0.72rem",
                              padding: "3px 10px",
                              borderRadius: "6px",
                              border: copiedIdx === idx ? "1px solid #2e7d32" : "1px solid #dce2dc",
                              background: copiedIdx === idx ? "#e8f5e9" : "#faf9f6",
                              color: copiedIdx === idx ? "#2e7d32" : "var(--ink)",
                              cursor: "pointer",
                              fontWeight: 600,
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              transition: "all 0.15s ease",
                            }}
                          >
                            {copiedIdx === idx ? "✓ Copied!" : "📋 Copy Quote"}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Message Body */}
                    {m.role === "user" ? (
                      <div style={{ fontSize: "0.92rem", color: "var(--ink)", lineHeight: 1.5 }}>{m.text}</div>
                    ) : (
                      renderStructuredContent(m.text)
                    )}

                    {/* Tool Invocations Badge Row */}
                    {m.responseMeta && m.responseMeta.tool_calls.length > 0 && (
                      <div style={{ marginTop: "14px", paddingTop: "10px", borderTop: "1px dashed #e2ded5", display: "flex", alignItems: "center", flexWrap: "wrap", gap: "6px" }}>
                        <small style={{ color: "var(--muted)", fontSize: "0.72rem", fontWeight: 600 }}>Tools Invoked: </small>
                        {m.responseMeta.tool_calls.map((t, ti) => (
                          <span
                            key={ti}
                            style={{
                              fontSize: "0.7rem",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: "#e8f0fe",
                              color: "#1a73e8",
                              fontWeight: 600,
                            }}
                          >
                            {formatToolName(t)}
                          </span>
                        ))}
                        <small style={{ color: "var(--muted)", fontSize: "0.72rem", marginLeft: "auto" }}>
                          ⏱️ {m.responseMeta.inference_latency_ms.toFixed(0)} ms
                        </small>
                      </div>
                    )}
                  </div>

                  {/* Contextual Smart Follow-Up Chips */}
                  {m.role === "assistant" && idx === messages.length - 1 && (
                    <div style={{ padding: "0 8px", marginTop: "2px" }}>
                      <small style={{ fontSize: "0.7rem", fontWeight: 700, color: "#c28b4b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: "6px" }}>
                        Suggested Follow-Up:
                      </small>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {followUps.map((fPrompt, fIdx) => (
                          <button
                            key={fIdx}
                            type="button"
                            onClick={() => handleSend(fPrompt)}
                            disabled={busy}
                            style={{
                              fontSize: "0.74rem",
                              padding: "4px 10px",
                              borderRadius: "14px",
                              border: "1px solid #dce2dc",
                              background: "white",
                              color: "var(--ink)",
                              cursor: "pointer",
                              fontWeight: 500,
                              boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                            }}
                          >
                            💬 {fPrompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {busy && (
              <div style={{ padding: "14px 18px", color: "var(--muted)", fontStyle: "italic", fontSize: "0.86rem", display: "flex", alignItems: "center", gap: "8px" }}>
                <div className="spinner" style={{ width: "16px", height: "16px" }}></div>
                <span>Sara is finding relevant information…</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {error && <div className="notice error" style={{ marginBottom: "12px" }}>{error}</div>}

          {/* Chat Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{ display: "flex", gap: "10px", position: "relative" }}
          >
            <input
              type="text"
              placeholder="Ask about property valuation, rent, lead scores, or market stats…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={busy}
              style={{
                flex: 1,
                padding: "13px 18px",
                borderRadius: "10px",
                border: "1px solid #ccd7d2",
                boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
                fontSize: "0.92rem",
              }}
            />
            <button
              type="submit"
              className="primary"
              disabled={busy || !input.trim()}
              style={{
                padding: "0 24px",
                borderRadius: "10px",
                fontWeight: 600,
                fontSize: "0.9rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {busy ? "Thinking…" : "Send ➤"}
            </button>
          </form>
        </div>

        {/* Sidebar with example prompts and features */}
        <div style={{ display: "grid", gap: "18px" }}>
          {/* Example Prompts Card */}
          <div className="panel" style={{ padding: "22px", borderRadius: "14px" }}>
            <h4 style={{ fontFamily: "Playfair Display", marginTop: 0, marginBottom: "12px", fontSize: "1.1rem" }}>
              Quick Action Prompts
            </h4>
            <div style={{ display: "grid", gap: "8px" }}>
              {EXAMPLE_PROMPTS.map((ep, i) => (
                <button
                  key={i}
                  type="button"
                  className="button"
                  style={{
                    textAlign: "left",
                    fontSize: "0.78rem",
                    padding: "10px 12px",
                    lineHeight: 1.4,
                    borderRadius: "8px",
                    border: "1px solid #ebe6dd",
                    background: "#faf9f6",
                    display: "grid",
                    gap: "4px",
                  }}
                  onClick={() => handleSend(ep.query)}
                  disabled={busy}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "5px", color: "#c28b4b", fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase" }}>
                    <span>{ep.icon}</span>
                    <span>{ep.tag}</span>
                  </div>
                  <span style={{ color: "var(--ink)", fontWeight: 500 }}>&ldquo;{ep.query}&rdquo;</span>
                </button>
              ))}
            </div>
          </div>

          {/* AI Engine Capabilities Card */}
          <div className="panel" style={{ padding: "22px", borderRadius: "14px", background: "white", border: "1px solid #e2ded5" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h4 style={{ fontFamily: "Playfair Display", margin: 0, fontSize: "1.05rem" }}>
                What Sara Can Help With
              </h4>
              <span style={{ fontSize: "0.68rem", background: "#e6f4ea", color: "#137333", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
                Available features
              </span>
            </div>

            <div style={{ display: "grid", gap: "10px", fontSize: "0.8rem", color: "var(--ink)" }}>
              <div style={{ display: "flex", alignItems: "start", gap: "8px" }}>
                <span style={{ color: "#2e7d32", fontSize: "0.75rem", marginTop: "2px" }}>●</span>
                <div>
                  <strong>Price Estimates:</strong> Get an indicative range for a property.
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "start", gap: "8px" }}>
                <span style={{ color: "#2e7d32", fontSize: "0.75rem", marginTop: "2px" }}>●</span>
                <div>
                  <strong>Lead Follow-Up:</strong> Review suggested priorities and helpful factors.
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "start", gap: "8px" }}>
                <span style={{ color: "#2e7d32", fontSize: "0.75rem", marginTop: "2px" }}>●</span>
                <div>
                  <strong>Property Search:</strong> Browse listings by location, price, and property features.
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "start", gap: "8px" }}>
                <span style={{ color: "#2e7d32", fontSize: "0.75rem", marginTop: "2px" }}>●</span>
                <div>
                  <strong>Key Factors:</strong> Understand what may affect a suggestion or estimate.
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "start", gap: "8px" }}>
                <span style={{ color: "#2e7d32", fontSize: "0.75rem", marginTop: "2px" }}>●</span>
                <div>
                  <strong>Market Overview:</strong> Explore average asking prices by city and area.
                </div>
              </div>
            </div>

            <div style={{ marginTop: "14px", paddingTop: "10px", borderTop: "1px dashed var(--line)", fontSize: "0.74rem", color: "var(--muted)", display: "flex", justifyContent: "space-between" }}>
              <span>Bilingual: English & UrduLish</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

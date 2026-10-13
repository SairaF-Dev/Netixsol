"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";
import { PropertyCard } from "@/components/PropertyCard";
import { FeedbackButtons } from "@/components/FeedbackButtons";
import { BookVisit } from "@/components/BookVisit";
import { SaraVoice } from "@/components/SaraVoice";
import type { ChatResponse, Property } from "@/types/api";

type Message = { role: "user" | "assistant"; text: string; response?: ChatResponse };

const SUGGESTED_PROMPTS = [
  { label: "🏠 4 Bed Houses in Faisalabad", query: "Mujhe Faisalabad mein 4 Bed houses dikhayein." },
  { label: "💰 Homes Under 1.5 Crore", query: "Under 1.5 Crore budget mein houses dikhayein." },
  { label: "📍 Samundari Road Listings", query: "Samundari Road Faisalabad par available properties dikhayein." },
  { label: "📅 Schedule a Site Visit", query: "Main aik property visit book karna chahta hoon." },
];

export default function Sara() {
  const { customer, ready } = useSession();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [booking, setBooking] = useState<Property | null>(null);
  const sending = useRef(false);
  const sessionVersion = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    sessionVersion.current += 1;
    if (ready && !customer) router.replace("/start");
    setMessages([]);
    setConversationId(undefined);
    setBooking(null);
  }, [ready, customer, router]);

  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, busy]);

  async function sendMessage(textToSend?: string) {
    const message = (textToSend ?? input).trim();
    if (!message || sending.current || !customer) return;
    sending.current = true;
    setBusy(true);
    setError("");
    const version = sessionVersion.current;
    try {
      const response = await api.chat(message, conversationId);
      if (version !== sessionVersion.current) return;
      setConversationId(response.conversation_id);
      setMessages((current) =>
        [
          ...current,
          { role: "user", text: message },
          { role: "assistant", text: response.message, response },
        ].slice(-40) as Message[]
      );
      setInput("");
    } catch (e) {
      if (version !== sessionVersion.current) return;
      setError(
        e instanceof ApiError && e.status === 410
          ? "This conversation or recommendation has expired. Start a new chat."
          : "Sara could not complete that message. Please try again."
      );
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    await sendMessage();
  }

  if (!ready) return <p role="status">Checking your session…</p>;
  if (!customer) return null;

  return (
    <section className="sara-chat" style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "20px" }}>
      {/* Page Header */}
      <div className="page-title row" style={{ marginBottom: "20px" }}>
        <div>
          <span className="eyebrow">YOUR PROPERTY ASSISTANT</span>
          <h1>Ask Sara</h1>
          <p>Chat or speak with Sara to find properties, get personalized recommendations, and manage property visits.</p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setMessages([]);
            setConversationId(undefined);
            setError("");
          }}
          style={{ fontSize: "0.82rem", padding: "8px 16px", borderRadius: "8px" }}
        >
          New chat
        </button>
      </div>

      {/* Polish Voice Mode Card */}
      <SaraVoice key={customer.customer_id} />

      {/* Main Conversation Feed */}
      <div
        role="log"
        aria-label="Conversation with Sara"
        aria-live="polite"
        style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "16px" }}
      >
        {/* Welcome Empty State with Interactive Prompts */}
        {messages.length === 0 && (
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #dce8e0",
              borderRadius: "16px",
              padding: "24px",
              boxShadow: "0 4px 18px rgba(23, 51, 45, 0.04)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
              <div
                style={{
                  width: "42px",
                  height: "42px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #17332d 0%, #246148 100%)",
                  color: "#dfc79d",
                  display: "grid",
                  placeItems: "center",
                  fontSize: "1.2rem",
                  fontWeight: 700,
                  boxShadow: "0 3px 10px rgba(23, 51, 45, 0.15)",
                }}
              >
                ✨
              </div>
              <div>
                <h2 style={{ font: '600 1.25rem "Playfair Display", serif', color: "var(--ink)", margin: 0 }}>
                  Assalam-o-Alaikum, {customer.full_name || "Valued Customer"}!
                </h2>
                <small style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
                  Sara AI — Your Personal Real Estate Advisor
                </small>
              </div>
            </div>

            <p style={{ fontSize: "0.88rem", color: "#364e46", lineHeight: 1.6, margin: "0 0 16px 0" }}>
              Main Faisalabad, Lahore, aur Pakistan ke doosray cities mein properties dhoondnay, market prices check karne, aur site visits plan karne mein aap ki madad kar sakti hoon.
            </p>

            <div>
              <small style={{ fontSize: "0.72rem", letterSpacing: "0.08em", fontWeight: 700, textTransform: "uppercase", color: "var(--gold)" }}>
                Click a prompt to get started:
              </small>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}>
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt.label}
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setInput(prompt.query);
                      void sendMessage(prompt.query);
                    }}
                    style={{
                      background: "#f4f8f5",
                      border: "1px solid #d2e4db",
                      color: "#1c4e3f",
                      padding: "7px 12px",
                      borderRadius: "20px",
                      fontSize: "0.78rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {prompt.label}
                  </button>
                ))}
              </div>
            </div>

            <p style={{ fontSize: "0.76rem", color: "#8a9691", margin: "14px 0 0 0" }}>
              Try asking: “Mujhe properties dikhayein."
            </p>
          </div>
        )}

        {/* Chat message bubbles */}
        {messages.map((message, index) => {
          const isUser = message.role === "user";
          return (
            <article
              key={index}
              className={`chat-message ${message.role}`}
              style={{
                alignSelf: isUser ? "flex-end" : "flex-start",
                maxWidth: isUser ? "min(560px, 88%)" : "100%",
                width: isUser ? "auto" : "100%",
                background: isUser ? "#17332d" : "#ffffff",
                color: isUser ? "#ffffff" : "var(--ink)",
                border: isUser ? "1px solid #17332d" : "1px solid #dfe7e2",
                borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                padding: "16px 20px",
                boxShadow: isUser ? "0 4px 14px rgba(23, 51, 45, 0.2)" : "0 4px 18px rgba(23, 51, 45, 0.05)",
                margin: 0,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: isUser ? "#dfc79d" : "#214e43",
                    color: isUser ? "#17332d" : "#ffffff",
                    fontSize: "0.68rem",
                    fontWeight: 700,
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  {isUser ? "U" : "S"}
                </span>
                <strong style={{ fontSize: "0.82rem", color: isUser ? "#dfc79d" : "var(--forest)" }}>
                  {isUser ? "You" : "Sara"}
                </strong>
              </div>

              <p style={{ whiteSpace: "pre-wrap", margin: "4px 0 0", lineHeight: 1.6, fontSize: "0.92rem" }}>
                {message.text}
              </p>

              {/* Embedded Recommended Properties Grid */}
              {message.response?.properties && message.response.properties.length > 0 && (
                <div className="property-grid" style={{ marginTop: "16px" }}>
                  {message.response.properties.map((property) => (
                    <PropertyCard
                      key={property.property_id}
                      property={property}
                      actions={
                        message.response?.recommendation_session_id && (
                          <FeedbackButtons
                            propertyId={property.property_id}
                            sessionId={message.response.recommendation_session_id}
                            onBook={() => setBooking(property)}
                          />
                        )
                      }
                    />
                  ))}
                </div>
              )}

              {/* Appointment View Link */}
              {message.response?.appointment && (
                <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px dashed #d5e6dc" }}>
                  <Link
                    href="/appointments"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "#eaf5ee",
                      color: "#1c5b3c",
                      padding: "6px 12px",
                      borderRadius: "6px",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      textDecoration: "none",
                      border: "1px solid #bde2cc",
                    }}
                  >
                    View appointment
                  </Link>
                </div>
              )}
            </article>
          );
        })}
        {/* Scroll Anchor */}
        <div ref={messagesEndRef} style={{ height: "4px" }} />
      </div>

      {busy && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", color: "var(--forest)", fontSize: "0.86rem", fontWeight: 500 }}>
          <div className="spinner" style={{ width: "18px", height: "18px" }} />
          <p role="status" style={{ margin: 0 }}>Sara is preparing a response…</p>
        </div>
      )}

      {error && (
        <p className="notice error" role="alert" style={{ marginBottom: "16px" }}>
          {error}
        </p>
      )}

      {/* Floating / Docked Chat Input Bar */}
      <form
        onSubmit={send}
        style={{
          position: "sticky",
          bottom: "16px",
          background: "rgba(255, 255, 255, 0.98)",
          backdropFilter: "blur(8px)",
          border: "1px solid #c9d8cf",
          borderRadius: "16px",
          padding: "12px 16px",
          boxShadow: "0 10px 32px rgba(17, 35, 30, 0.12)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          zIndex: 10,
          width: "100%",
          maxWidth: "100%",
          boxSizing: "border-box",
        }}
      >
        <label htmlFor="sara-message" style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--muted)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
          Message Sara
        </label>

        <div style={{ display: "flex", alignItems: "flex-end", gap: "10px", width: "100%" }}>
          <textarea
            id="sara-message"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (input.trim() && !busy) {
                  void sendMessage();
                }
              }
            }}
            placeholder="Ask Sara in English or Roman Urdu (e.g. 'Faisalabad mein houses dikhayein')…"
            maxLength={2000}
            disabled={busy}
            required
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              resize: "none",
              padding: "4px 6px",
              fontSize: "0.92rem",
              color: "var(--ink)",
              background: "transparent",
              fontFamily: "inherit",
              lineHeight: 1.45,
            }}
          />

          <button
            type="submit"
            className="primary"
            disabled={busy || !input.trim()}
            style={{
              padding: "8px 18px",
              fontSize: "0.84rem",
              fontWeight: 600,
              borderRadius: "8px",
              alignSelf: "flex-end",
              flexShrink: 0,
            }}
          >
            {busy ? "Sending…" : "Send"}
          </button>
        </div>

        <small style={{ fontSize: "0.68rem", color: "#8a9791" }}>
          Tip: Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line.
        </small>
      </form>

      {booking && (
        <BookVisit
          customerId={customer.customer_id}
          property={booking}
          close={() => setBooking(null)}
        />
      )}
    </section>
  );
}

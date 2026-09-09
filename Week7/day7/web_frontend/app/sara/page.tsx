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
  useEffect(() => {
    sessionVersion.current += 1;
    if (ready && !customer) router.replace("/start");
    setMessages([]); setConversationId(undefined); setBooking(null);
  }, [ready, customer, router]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || sending.current || !customer) return;
    sending.current = true; setBusy(true); setError("");
    const version = sessionVersion.current;
    try {
      const response = await api.chat(message, conversationId);
      if (version !== sessionVersion.current) return;
      setConversationId(response.conversation_id);
      setMessages(current => [...current, { role: "user", text: message },
        { role: "assistant", text: response.message, response }].slice(-40) as Message[]);
      setInput("");
    } catch (e) {
      if (version !== sessionVersion.current) return;
      setError(e instanceof ApiError && e.status === 410
        ? "This conversation or recommendation has expired. Start a new chat."
        : "Sara could not complete that message. Please try again.");
    } finally { sending.current = false; setBusy(false); }
  }
  if (!ready) return <p role="status">Checking your session…</p>;
  if (!customer) return null;
  return <section className="sara-chat">
    <div className="page-title row"><div><span className="eyebrow">YOUR PROPERTY ASSISTANT</span><h1>Ask Sara</h1><p>Chat or speak with Sara to find properties, get personalized recommendations, and manage property visits.</p></div>
      <button disabled={busy} onClick={() => { setMessages([]); setConversationId(undefined); setError(""); }}>New chat</button></div>
    <SaraVoice key={customer.customer_id} />
    <div role="log" aria-label="Conversation with Sara" aria-live="polite">
      {messages.length === 0 && <p>Try asking: “Mujhe properties dikhayein."</p>}
      {messages.map((message, index) => <article className={`chat-message ${message.role}`} key={index}>
        <strong>{message.role === "user" ? "You" : "Sara"}</strong><p style={{ whiteSpace: "pre-wrap" }}>{message.text}</p>
        <div className="property-grid">{message.response?.properties?.map(property => <PropertyCard key={property.property_id} property={property}
          actions={message.response?.recommendation_session_id && <FeedbackButtons propertyId={property.property_id}
            sessionId={message.response.recommendation_session_id} onBook={() => setBooking(property)} />} />)}</div>
        {message.response?.appointment && <Link href="/appointments">View appointment</Link>}
      </article>)}
    </div>
    {busy && <p role="status">Sara is preparing a response…</p>}
    {error && <p className="notice error" role="alert">{error}</p>}
    <form onSubmit={send}><label htmlFor="sara-message">Chat with Sara</label>
      <textarea id="sara-message" value={input} onChange={e => setInput(e.target.value)} maxLength={2000} disabled={busy} required />
      <button className="primary" disabled={busy || !input.trim()}>{busy ? "Sending…" : "Send"}</button>
    </form>
    {booking && <BookVisit customerId={customer.customer_id} property={booking} close={() => setBooking(null)} />}
  </section>;
}

"use client";
import { useEffect, useRef, useState } from "react";
import type Vapi from "@vapi-ai/web";
import { api } from "@/lib/api";

export function SaraVoice() {
  const [status, setStatus] = useState<"idle" | "connecting" | "active">("idle");
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState("");
  const [transcript, setTranscript] = useState<string[]>([]);
  const client = useRef<Vapi | null>(null);
  const capability = useRef<string | null>(null);
  const generation = useRef(0);
  const busy = useRef(false);
  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;

  function release() {
    const token = capability.current;
    capability.current = null;
    if (token) void api.closeVoice(token).catch(() => {});
  }
  function stop() {
    generation.current++;
    const vapi = client.current;
    client.current = null;
    vapi?.removeAllListeners();
    void vapi?.stop();
    release();
    busy.current = false;
    setStatus("idle");
    setMuted(false);
  }
  useEffect(() => () => {
    generation.current++;
    client.current?.removeAllListeners();
    void client.current?.stop();
    client.current = null;
    release();
  }, []);

  async function start() {
    if (!publicKey || busy.current) return;
    busy.current = true;
    const version = ++generation.current;
    setStatus("connecting");
    setError("");
    setTranscript([]);
    try {
      const session = await api.startVoice();
      if (version !== generation.current) {
        void api.closeVoice(session.voice_session).catch(() => {});
        return;
      }
      capability.current = session.voice_session;
      const { default: VapiClient } = await import("@vapi-ai/web");
      if (version !== generation.current) return;
      const vapi = new VapiClient(publicKey);
      client.current = vapi;
      vapi.on("call-start", () => {
        if (version !== generation.current) return;
        setStatus("active");
        if (session.preferences)
          vapi.send({
            type: "add-message",
            triggerResponseEnabled: false,
            message: {
              role: "system",
              content: `Saved property preferences: ${JSON.stringify(session.preferences)}
Summarize the saved requirement once and ask whether to continue or change it.
After the customer chooses change, stay in editing_preferences. Ask which field
only if unknown; if a field is named, ask only for its new value. If new values
are already supplied, preserve the other preferences and continue with the
updated requirement. Never repeat continue-or-change during an active edit.
Recognize UrduLish variants such as change krni hai and preference change krni hai.
Confirm persistence only after a successful tool result; check availability with the property search tools before responding.`,
            },
          });
      });
      vapi.on("call-end", () => {
        if (version === generation.current) stop();
      });
      vapi.on("error", () => {
        if (version !== generation.current) return;
        stop();
        setError("Voice could not connect. Check microphone permission and try again.");
      });
      vapi.on("message", (message: { type?: string; transcriptType?: string; role?: string; transcript?: string }) => {
        if (
          version === generation.current &&
          message.type === "transcript" &&
          message.transcriptType === "final" &&
          message.transcript
        ) {
          const text = `${message.role === "user" ? "You" : "Sara"}: ${message.transcript}`;
          setTranscript((items) => [...items, text].slice(-20));
        }
      });
      const call = await vapi.start(session.assistant_id, {
        variableValues: { sara_voice_session: session.voice_session },
        // SDK 2.7.0 declares this REST array as a scalar union in its generated types.
        // @ts-expect-error VAPI's serverMessages wire contract is an array.
        serverMessages: ["tool-calls", "transcript", "status-update", "end-of-call-report"],
        maxDurationSeconds: 1800,
      });
      if (version !== generation.current) {
        void vapi.stop();
        return;
      }
      if (!call) throw new Error("Call did not start");
    } catch {
      if (version !== generation.current) return;
      stop();
      setError("Voice could not connect. Check microphone permission and try again.");
    }
  }

  return (
    <section
      aria-label="Talk to Sara"
      className="chat-message"
      style={{
        background: "linear-gradient(135deg, #ffffff 0%, #f4f8f5 100%)",
        border: "1px solid #d4e3db",
        borderRadius: "14px",
        padding: "14px 18px",
        marginBottom: "20px",
        boxShadow: "0 4px 14px rgba(23, 51, 45, 0.03)",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              width: "26px",
              height: "26px",
              borderRadius: "50%",
              background: "#214e43",
              color: "#ffffff",
              display: "grid",
              placeItems: "center",
              fontSize: "0.8rem",
            }}
          >
            🎙️
          </span>
          <h2 style={{ font: '600 1.12rem "Playfair Display", serif', color: "var(--ink)", margin: 0 }}>
            Talk to Sara
          </h2>
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              color: "#1c5b3c",
              background: "#e4f3ea",
              padding: "2px 8px",
              borderRadius: "12px",
            }}
          >
            Urdu & English
          </span>
        </div>

        {/* Live Status Indicator */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            background: "#ffffff",
            border: "1px solid #dbe6df",
            padding: "4px 10px",
            borderRadius: "16px",
            fontSize: "0.74rem",
            fontWeight: 600,
            color: status === "active" ? "#16a34a" : status === "connecting" ? "#d97706" : "#246148",
          }}
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: status === "active" ? "#16a34a" : status === "connecting" ? "#f59e0b" : "#22c55e",
              boxShadow: status === "active" ? "0 0 8px #16a34a" : "none",
            }}
          />
          <p aria-live="polite" style={{ margin: 0 }}>
            {status === "active" ? "Call connected" : status === "connecting" ? "Connecting…" : "Ready to talk"}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--muted)", maxWidth: "520px", lineHeight: 1.4 }}>
          Speak with Sara to explore properties, discuss your preferences, or plan a property visit.
        </p>

        {/* Call Controls */}
        <div className="row" style={{ display: "flex", gap: "8px", margin: 0 }}>
          {status === "idle" ? (
            <button
              type="button"
              className="primary"
              disabled={!publicKey}
              onClick={start}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "0.78rem",
                padding: "6px 14px",
                borderRadius: "7px",
              }}
            >
              <span>📞</span> Start voice call
            </button>
          ) : (
            <button
              type="button"
              className="danger"
              onClick={stop}
              style={{
                fontSize: "0.78rem",
                padding: "6px 14px",
                borderRadius: "7px",
                borderColor: "var(--danger)",
                background: "#fae8e6",
              }}
            >
              {status === "connecting" ? "Cancel call" : "End call"}
            </button>
          )}

          {status === "active" && (
            <button
              type="button"
              aria-pressed={muted}
              onClick={() => {
                client.current?.setMuted(!muted);
                setMuted(!muted);
              }}
              style={{
                fontSize: "0.78rem",
                padding: "6px 12px",
                borderRadius: "7px",
              }}
            >
              {muted ? "Unmute microphone" : "Mute microphone"}
            </button>
          )}
        </div>
      </div>

      {!publicKey && (
        <p style={{ fontSize: "0.78rem", color: "var(--muted)", margin: 0 }}>
          Browser voice is not configured yet.
        </p>
      )}

      {error && (
        <p role="alert" className="notice error" style={{ margin: 0, fontSize: "0.8rem" }}>
          {error}
        </p>
      )}

      {/* Voice Transcript Container */}
      {transcript.length > 0 && (
        <div
          role="log"
          aria-label="Voice transcript"
          style={{
            marginTop: "8px",
            padding: "10px 12px",
            background: "#ffffff",
            border: "1px solid #dce8e0",
            borderRadius: "8px",
            maxHeight: "150px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "5px",
          }}
        >
          {transcript.map((line, i) => (
            <p key={i} style={{ margin: 0, fontSize: "0.78rem", color: "var(--ink)", lineHeight: 1.35 }}>
              {line}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}

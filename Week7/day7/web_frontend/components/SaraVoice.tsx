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
    release(); busy.current = false;
    setStatus("idle"); setMuted(false);
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
    setStatus("connecting"); setError(""); setTranscript([]);
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
        if (session.preferences) vapi.send({ type: "add-message", triggerResponseEnabled: false,
          message: { role: "system", content: `Saved property preferences: ${JSON.stringify(session.preferences)}
Summarize the saved requirement once and ask whether to continue or change it.
After the customer chooses change, stay in editing_preferences. Ask which field
only if unknown; if a field is named, ask only for its new value. If new values
are already supplied, preserve the other preferences and continue with the
updated requirement. Never repeat continue-or-change during an active edit.
Recognize UrduLish variants such as change krni hai and preference change krni hai.
Confirm persistence only after a successful tool result; use verified search tools.` } });
      });
      vapi.on("call-end", () => { if (version === generation.current) stop(); });
      vapi.on("error", () => {
        if (version !== generation.current) return;
        stop(); setError("Voice could not connect. Check microphone permission and try again.");
      });
      vapi.on("message", (message: { type?: string; transcriptType?: string; role?: string; transcript?: string }) => {
        if (version === generation.current && message.type === "transcript" && message.transcriptType === "final" && message.transcript) {
          const text = `${message.role === "user" ? "You" : "Sara"}: ${message.transcript}`;
          setTranscript(items => [...items, text].slice(-20));
        }
      });
      const call = await vapi.start(session.assistant_id, {
        variableValues: { sara_voice_session: session.voice_session },
        // SDK 2.7.0 declares this REST array as a scalar union in its generated types.
        // @ts-expect-error VAPI's serverMessages wire contract is an array.
        serverMessages: ["tool-calls", "transcript", "status-update", "end-of-call-report"],
        maxDurationSeconds: 1800,
      });
      if (version !== generation.current) { void vapi.stop(); return; }
      if (!call) throw new Error("Call did not start");
    } catch {
      if (version !== generation.current) return;
      stop(); setError("Voice could not connect. Check microphone permission and try again.");
    }
  }

  return <section aria-label="Talk to Sara" className="chat-message">
    <h2>Talk to Sara</h2>
    <p>Speak with Sara to explore properties, discuss your preferences, or plan a property visit.</p>
    {!publicKey && <p>Browser voice is not configured yet.</p>}
    <p aria-live="polite">{status === "active" ? "Call connected" : status === "connecting" ? "Connecting…" : "Ready to talk"}</p>
    <div className="row">
      {status === "idle" ? <button type="button" disabled={!publicKey} onClick={start}>Start voice call</button>
        : <button type="button" onClick={stop}>{status === "connecting" ? "Cancel call" : "End call"}</button>}
      {status === "active" && <button type="button" aria-pressed={muted} onClick={() => {
        client.current?.setMuted(!muted); setMuted(!muted);
      }}>{muted ? "Unmute microphone" : "Mute microphone"}</button>}
    </div>
    {error && <p role="alert">{error}</p>}
    <div role="log" aria-label="Voice transcript">{transcript.map((line, i) => <p key={i}>{line}</p>)}</div>
  </section>;
}

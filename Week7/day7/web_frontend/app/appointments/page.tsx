"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Empty } from "@/components/States";
import type { BackendAppointment } from "@/types/api";

export default function Appointments() {
  const [items, setItems] = useState<BackendAppointment[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    try { setItems((await api.getMyAppointments()).appointments); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Appointments could not be loaded."); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const cancel = async (item: BackendAppointment) => {
    if (!confirm("Cancel this property visit?")) return;
    try { await api.cancelAppointment(item.appointment_id); await load(); setMessage("Appointment cancelled."); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Cancellation failed."); }
  };
  const reschedule = async (item: BackendAppointment) => {
    const value = prompt("New date/time (YYYY-MM-DDTHH:mm)");
    if (!value) return;
    try { await api.rescheduleAppointment(item.appointment_id, new Date(value).toISOString()); await load(); setMessage("Appointment rescheduled."); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "Reschedule failed."); }
  };
  return <><div className="page-title"><span className="eyebrow">YOUR APPOINTMENTS</span><h1>Appointments</h1><p>Current, rescheduled, and cancelled property visits tied to your account.</p></div>{message && <div className="notice">{message}</div>}{items.length === 0 ? <Empty title="No appointments" text="Book a visit from a recommendation card." /> : <div className="appointment-list">{items.map(item => <article className="panel" key={item.appointment_id}><div><small>{item.status.toUpperCase()}</small><h3>{item.request.property_name}</h3><p>{new Date(item.request.starts_at).toLocaleString()}</p><span className="reference">{String(item.request.property_id)}</span></div>{item.status !== "cancelled" && <div className="card-actions"><button onClick={() => reschedule(item)}>Reschedule</button><button className="danger" onClick={() => cancel(item)}>Cancel</button></div>}</article>)}</div>}</>;
}

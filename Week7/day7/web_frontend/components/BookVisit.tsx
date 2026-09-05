"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Property } from "@/types/api";

export function BookVisit({ customerId, property, close }: {customerId:string;property:Property;close:()=>void}) {
  const [starts,setStarts]=useState(""); const [notes,setNotes]=useState(""); const [busy,setBusy]=useState(false); const [message,setMessage]=useState("");
  const submit=async(e:React.FormEvent)=>{e.preventDefault();setBusy(true);setMessage("");try{await api.bookMyAppointment({property_id:property.property_id,starts_at:new Date(starts).toISOString(),duration_minutes:60,meeting_notes:notes});setMessage("Visit booked successfully.");}catch(e){setMessage(e instanceof ApiError?e.message:"Booking could not be completed.");}finally{setBusy(false)}};
  return <div className="modal-backdrop"><section className="modal"><button className="modal-close" onClick={close}>×</button><small>BOOK A VERIFIED PROPERTY VISIT</small><h2>{property.property_name}</h2><form onSubmit={submit}><label>Date and time<input type="datetime-local" required value={starts} onChange={e=>setStarts(e.target.value)}/></label><label>Notes<textarea value={notes} maxLength={2000} onChange={e=>setNotes(e.target.value)} /></label><button className="primary" disabled={busy}>{busy?"Booking…":"Confirm visit"}</button>{message&&<div className="notice">{message}</div>}</form></section></div>;
}

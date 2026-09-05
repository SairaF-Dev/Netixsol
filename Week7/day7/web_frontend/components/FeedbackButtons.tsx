"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { InteractionAction } from "@/types/api";

export function FeedbackButtons({ customerId, propertyId, sessionId, onBook }: {customerId?:string;propertyId:string;sessionId:string;onBook:()=>void}) {
  const [saved,setSaved]=useState<InteractionAction|null>(null); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const send=async(action:InteractionAction)=>{if(busy)return;setBusy(true);setError("");try{if(customerId)await api.recordInteraction(customerId,propertyId,action,sessionId);else await api.recordMyInteraction(propertyId,action,sessionId);setSaved(action);}catch(e){setError(e instanceof ApiError?e.message:"Could not save feedback.");}finally{setBusy(false)}};
  return <><button disabled={busy} onClick={()=>send("liked")}>{saved==="liked"?"Liked ✓":"Like"}</button><button disabled={busy} onClick={()=>send("rejected")}>{saved==="rejected"?"Rejected ✓":"Reject"}</button><button disabled={busy} onClick={()=>send("shortlisted")}>{saved==="shortlisted"?"Shortlisted ✓":"Shortlist"}</button><button className="primary" onClick={onBook}>Book visit</button>{error&&<small className="inline-error">{error}</small>}</>;
}

"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";
import { PropertyCard } from "@/components/PropertyCard";
import { FeedbackButtons } from "@/components/FeedbackButtons";
import { BookVisit } from "@/components/BookVisit";
import { Empty, ErrorNotice, Loading } from "@/components/States";
import type { Property, RecommendationResponse } from "@/types/api";

export default function Recommendations(){const {customer,ready}=useSession();const router=useRouter();const [data,setData]=useState<RecommendationResponse|null>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [booking,setBooking]=useState<Property|null>(null);const load=useCallback(async()=>{if(!customer)return;setBusy(true);setError("");const id=crypto.randomUUID();try{setData(await api.getRecommendations(customer.customer_id,id,10))}catch(e){setError(e instanceof ApiError?e.message:"Could not load recommendations.")}finally{setBusy(false)}},[customer]);useEffect(()=>{if(ready&&!customer)router.replace("/start");else if(customer&&!data&&!busy)void load()},[ready,customer,data,busy,load,router]);return <><div className="page-title row"><div><span className="eyebrow">CURATED FOR YOUR PROFILE</span><h1>My recommendations</h1><p>Ordering is returned by Sara’s backend; no ranking happens in this browser.</p></div><button className="ghost" disabled={busy} onClick={load}>Refresh recommendations</button></div>{busy&&<Loading label="Preparing verified recommendations…"/>}{error&&<ErrorNotice message={error}/>} {data?.properties.length===0&&<Empty title="No recommendations yet" text="Save or broaden your preferences, then refresh."/>}<div className="property-grid">{data?.properties.map(x=><PropertyCard key={x.property_id} property={x} actions={<FeedbackButtons customerId={customer!.customer_id} propertyId={x.property_id} sessionId={data.recommendation_session_id} onBook={()=>setBooking(x)}/>}/>)}</div>{booking&&<BookVisit customerId={customer!.customer_id} property={booking} close={()=>setBooking(null)}/>}</>}

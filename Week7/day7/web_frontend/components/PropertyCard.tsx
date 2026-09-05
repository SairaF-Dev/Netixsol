"use client";
import Link from "next/link";
import type { Property } from "@/types/api";

export function PropertyCard({ property, actions }: { property: Property; actions?: React.ReactNode }) {
  return <article className="property-card"><div className="property-visual"><span>Verified listing</span><b>{property.property_type}</b></div><div className="property-body"><div className="property-title"><div><small>{property.area} · {property.city}</small><h3>{property.property_name}</h3></div><strong>PKR {new Intl.NumberFormat("en-PK").format(property.price)}</strong></div><div className="facts"><span>{property.bedrooms ?? "—"} beds</span><span>{property.bathrooms ?? "—"} baths</span><span>{property.purpose}</span></div>{property.amenities.length>0 && <div className="chips">{property.amenities.slice(0,5).map(x=><span key={x}>{x}</span>)}</div>}<small className="reference">Reference: {property.property_id}</small>{actions && <div className="card-actions">{actions}</div>}</div></article>;
}

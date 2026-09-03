from __future__ import annotations
from decimal import Decimal


def money(value, currency="PKR"):
    if isinstance(value,(int,float,Decimal)):
        return f"{value:,.0f} {currency}"
    return f"{value} {currency}"


def property_summary(p, index=None):
    name=p.get("property_name") or p.get("name") or "Property"
    prefix=f"{index}. " if index is not None else ""
    parts=[prefix+name]
    location=", ".join(x for x in [p.get("area"),p.get("city")] if x)
    if location: parts.append(location)
    if p.get("bedrooms") is not None: parts.append(f"{p['bedrooms']} bedrooms")
    if p.get("purpose"): parts.append(str(p["purpose"]))
    if p.get("price") is not None: parts.append(money(p["price"],p.get("currency","PKR")))
    return " — ".join(parts)


def format_results(results):
    lines=["Ji bilkul. Mujhe ye verified options mile hain:"]
    for i,p in enumerate(results[:5],1): lines.append(property_summary(p,i))
    if len(results)>5: lines.append(f"Aur {len(results)-5} verified options bhi available hain.")
    lines.append("Kis option ki details ya comparison chahiye?")
    return "\n".join(lines)


def format_details(p):
    name=p.get("property_name") or p.get("name") or "Selected Property"
    labels=[
        ("property_id","Property ID"),("area","Area"),("city","City"),
        ("property_type","Property type"),("bedrooms","Bedrooms"),("bathrooms","Bathrooms"),
        ("plot_size","Plot size"),("plot_unit","Plot unit"),("covered_area","Covered area"),
        ("covered_area_unit","Covered area unit"),("purpose","Purpose"),
        ("available","Available"),("status","Status"),("developer_name","Developer"),
        ("amenities","Amenities")
    ]
    lines=[f"Ji, {name} ki verified details:"]
    if p.get("price") is not None: lines.append(f"- Price: {money(p['price'],p.get('currency','PKR'))}")
    for field,label in labels:
        val=p.get(field)
        if val is None: continue
        if isinstance(val,list): val=", ".join(map(str,val))
        lines.append(f"- {label}: {val}")
    return "\n".join(lines)

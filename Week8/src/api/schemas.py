"""
schemas.py
----------
Pydantic v2 request and response schemas for Week 8 FastAPI Model Serving.
Enforces strict input validation, domain bounds, and clean error messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


SUPPORTED_CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]
SUPPORTED_PURPOSES_VALUATION = ["For Sale", "For Rent", "Sale", "Rent"]
SUPPORTED_PROPERTY_TYPES = [
    "House", "Flat", "Upper Portion", "Lower Portion",
    "Penthouse", "Room", "Farm House"
]
CITY_PROVINCE_MAP = {
    "Lahore": "Punjab",
    "Karachi": "Sindh",
    "Islamabad": "Islamabad Capital Territory",
    "Rawalpindi": "Punjab",
    "Faisalabad": "Punjab",
}


# ==============================================================================
# 1. Price Valuation Schemas
# ==============================================================================

class PricePredictionRequest(BaseModel):
    purpose: str = Field(..., description="Listing purpose: 'For Sale' or 'For Rent'")
    property_type: str = Field(..., description="Property category (e.g. House, Flat, Upper Portion)")
    city: str = Field(..., description="City name (Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad)")
    location: str = Field("Unknown", description="Locality or society name, e.g. DHA Defence Phase 5")
    area_marla: float = Field(..., gt=0.0, description="Plot or covered size in Marlas (must be > 0)")
    bedrooms: Optional[int] = Field(3, ge=0, le=50, description="Bedroom count")
    baths: Optional[int] = Field(3, ge=0, le=50, description="Bathroom count")
    province_name: Optional[str] = Field(None, description="Province name")
    price: Optional[float] = Field(None, gt=0.0, description="Optional listed asking price in PKR to evaluate verdict")
    property_age_years: Optional[int] = Field(5, ge=0, le=100, description="Property age in years")
    floors: Optional[int] = Field(1, ge=1, le=50, description="Storey count")
    corner: Optional[int] = Field(0, ge=0, le=1, description="1 if corner plot, 0 otherwise")
    park_facing: Optional[int] = Field(0, ge=0, le=1, description="1 if park-facing, 0 otherwise")
    parking: Optional[int] = Field(1, ge=0, le=1, description="Parking amenity")
    security: Optional[int] = Field(0, ge=0, le=1, description="Security amenity")
    electricity_backup: Optional[int] = Field(0, ge=0, le=1, description="Generator/UPS backup")
    gas: Optional[int] = Field(1, ge=0, le=1, description="Gas connection")
    water_supply: Optional[int] = Field(1, ge=0, le=1, description="Water supply")
    park_nearby: Optional[int] = Field(0, ge=0, le=1, description="Park nearby")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        v_clean = v.strip().title()
        if v_clean in ["Sale", "For Sale"]:
            return "For Sale"
        if v_clean in ["Rent", "For Rent"]:
            return "For Rent"
        raise ValueError(
            f"purpose '{v}' is invalid. Must be one of: 'For Sale', 'For Rent'"
        )

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        for c in SUPPORTED_CITIES:
            if v.strip().casefold() == c.casefold():
                return c
        supported = ", ".join(SUPPORTED_CITIES)
        raise ValueError(
            f"city '{v}' is not supported by the trained model. Supported cities: {supported}"
        )

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        for pt in SUPPORTED_PROPERTY_TYPES:
            if v.strip().casefold() == pt.casefold():
                return pt
        supported = ", ".join(SUPPORTED_PROPERTY_TYPES)
        raise ValueError(
            f"property_type '{v}' is not recognized. Supported types: {supported}"
        )

    @model_validator(mode="after")
    def infer_defaults(self) -> "PricePredictionRequest":
        if not self.province_name:
            self.province_name = CITY_PROVINCE_MAP.get(self.city, "Punjab")
        return self


class PricePredictionResponse(BaseModel):
    purpose: str
    predicted_fair_price_pkr: float
    lower_bound_pkr: float
    upper_bound_pkr: float
    confidence_band_pkr: Tuple[float, float]
    listed_price_pkr: Optional[float]
    verdict: str
    deviation_percentage: float
    human_readable_summary: str
    inference_latency_ms: float
    model_version: str
    disclaimer: str = Field(
        default="Estimated price only — not an official valuation, appraisal, or guaranteed market price.",
        description="Legal valuation disclaimer",
    )


# ==============================================================================
# 2. Lead Scoring Schemas
# ==============================================================================

class LeadScoringRequest(BaseModel):
    lead_source: str = Field(..., description="Inquiry source: Call, WhatsApp, Facebook, Website, Referral, Walk-in")
    preferred_city: str = Field(..., description="Client preferred city")
    preferred_location: str = Field("Unknown", description="Client preferred area or society")
    property_type: str = Field("House", description="House, Flat, Upper Portion, Lower Portion, Penthouse")
    purpose: str = Field("Buy", description="Client intent: Buy, Rent, or Invest")
    budget_pkr: float = Field(..., gt=0.0, description="Client budget in PKR (must be > 0)")
    number_of_calls: int = Field(1, ge=0, description="Total phone calls completed")
    total_call_duration_min: float = Field(5.0, ge=0.0, description="Total talk time in minutes")
    response_time_minutes: float = Field(30.0, ge=0.0, description="Agent response latency in minutes")
    visit_booked: int = Field(0, ge=0, le=1, description="1 if physical property visit booked, 0 otherwise")
    days_since_first_contact: int = Field(1, ge=0, description="Days elapsed since first touchpoint")
    follow_up_count: int = Field(0, ge=0, description="Agent follow-up attempts")
    budget_match_ratio: Optional[float] = Field(1.0, ge=0.0, description="Ratio of budget to area median")
    objection_raised: Optional[str] = Field("None", description="Objection tag: None, Budget, Price, Location, Timing, Financing, Trust")

    @field_validator("preferred_city")
    @classmethod
    def validate_lead_city(cls, v: str) -> str:
        for c in SUPPORTED_CITIES:
            if v.strip().casefold() == c.casefold():
                return c
        supported = ", ".join(SUPPORTED_CITIES)
        raise ValueError(
            f"preferred_city '{v}' is not supported by the trained model. Supported cities: {supported}"
        )

    @field_validator("purpose")
    @classmethod
    def validate_lead_purpose(cls, v: str) -> str:
        valid = ["Buy", "Rent", "Invest"]
        for p in valid:
            if v.strip().casefold() == p.casefold():
                return p
        return "Buy"


class LeadScoringResponse(BaseModel):
    conversion_probability: float
    lead_score_pct: float
    tier: str
    priority_rank: int
    recommended_sla_action: str
    customer_persona: str
    persona_cluster_id: int
    urdulish_explanation: str
    inference_latency_ms: float
    model_version: str


# ==============================================================================
# 3. Explainability Schemas
# ==============================================================================

class PriceExplanationResponse(BaseModel):
    status: str
    message: str
    predicted_fair_price_pkr: Optional[float]
    top_features: List[Dict[str, Any]]
    urdulish_summary: Optional[str]
    inference_latency_ms: float


class LeadExplanationResponse(BaseModel):
    conversion_probability: float
    tier: str
    top_positive_features: List[Dict[str, Any]]
    top_negative_features: List[Dict[str, Any]]
    urdulish_explanation: str
    inference_latency_ms: float


# ==============================================================================
# 4. Batch Prediction Schemas
# ==============================================================================

class BatchPredictionResponse(BaseModel):
    batch_type: str
    rows_processed: int
    successful_predictions: int
    failed_predictions: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total_latency_ms: float


# ==============================================================================
# 5. System & Health Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    models_loaded: Dict[str, bool]
    system_ready: bool


class ModelInfoResponse(BaseModel):
    service: str
    environment: str
    models: Dict[str, Any]


# ==============================================================================
# 6. LangGraph Assistant Schemas (Task 2)
# ==============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User inquiry or conversational prompt in English, Urdu, or UrduLish")
    conversation_id: Optional[str] = Field(None, description="Optional conversation tracking ID")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or pure whitespace.")
        return v.strip()


class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response text (with verified facts)")
    intent: str = Field(..., description="Detected user intent (valuation, lead_scoring, comparables, market_stats, general)")
    tool_calls: List[str] = Field(default_factory=list, description="List of tools invoked during reasoning")
    tool_results: Dict[str, Any] = Field(default_factory=dict, description="Structured factual results returned by the tools")
    missing_fields: List[str] = Field(default_factory=list, description="Missing entity slots required for precise answers")
    language: str = Field("english", description="Detected language: english, urdulish, or urdu")
    guard_triggered: bool = Field(False, description="True if numeric safety guard intervened to prevent hallucination")
    inference_latency_ms: float = Field(..., description="End-to-end processing latency in milliseconds")



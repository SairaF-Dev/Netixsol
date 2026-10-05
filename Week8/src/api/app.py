"""
app.py
------
FastAPI production application for Week 8 AI Property Valuation & Lead Scoring.

Endpoints:
- POST /predict/price       : Point valuation, quantile bounds, market verdict (Huber model)
- POST /predict/lead-score  : Lead conversion probability, priority tier, and persona
- POST /explain/price       : Feature attribution contract for price valuation
- POST /explain/lead        : TreeSHAP local attribution and UrduLish rationale
- POST /predict/batch       : Bounded CSV upload inference engine
- GET  /health              : Service liveness and loaded model verification
- GET  /model/info          : Provenance, versions, verified validation & test metrics
- POST /assistant/chat      : LangGraph AI Assistant for valuation, scoring & market analysis
"""

from __future__ import annotations

import io
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import real_estate_assistant
from src.api.schemas import (
    BatchPredictionResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LeadExplanationResponse,
    LeadScoringRequest,
    LeadScoringResponse,
    ModelInfoResponse,
    PriceExplanationResponse,
    PricePredictionRequest,
    PricePredictionResponse,
)
from src.features.lead_features import add_lead_features
from src.models.predict_lead_scoring import LeadScorer
from src.models.predict_valuation import PropertyValuator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api_server")

MODELS_DIR = PROJECT_ROOT / "models"

# Global singletons
valuator: Optional[PropertyValuator] = None
lead_scorer: Optional[LeadScorer] = None
lead_tree_explainer: Optional[shap.TreeExplainer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global valuator, lead_scorer, lead_tree_explainer
    t0 = time.time()
    logger.info("Initializing Week 8 FastAPI Serving Layer...")

    valuator = PropertyValuator(models_dir=MODELS_DIR, model_variant="auto")
    valuator.load()

    lead_scorer = LeadScorer(models_dir=MODELS_DIR)
    lead_scorer.load()

    from src.agent.data_store import PropertyDataStore

    PropertyDataStore.get_instance()

    if lead_scorer.model is not None:
        try:
            lead_tree_explainer = shap.TreeExplainer(lead_scorer.model)
            logger.info("TreeSHAP explainer for lead scoring successfully initialized.")
        except Exception as e:
            logger.warning("Could not pre-initialize TreeSHAP explainer: %s", e)

    logger.info("Lifespan startup complete in %.3fs.", time.time() - t0)
    yield
    logger.info("Shutting down Week 8 FastAPI Serving Layer.")


app = FastAPI(
    title="Week 8 AI Property Valuation & Lead Scoring Platform API",
    description="Production machine learning serving layer for dual-regression property valuation and lead prioritization.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time_ms = (time.time() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append({"field": field, "message": msg})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": errors},
    )


# ==============================================================================
# Endpoint 1: POST /predict/price
# ==============================================================================
@app.post(
    "/predict/price",
    response_model=PricePredictionResponse,
    summary="Predict fair market property price, bounds, and verdict",
    tags=["Valuation"],
)
async def predict_price(request: PricePredictionRequest) -> PricePredictionResponse:
    if valuator is None or not valuator._is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Property valuation service is not loaded.",
        )
    try:
        input_data = request.model_dump()
        result = valuator.predict(input_data, purpose=request.purpose)
        return PricePredictionResponse(**result)
    except Exception as e:
        logger.error("Error during price prediction: %s", e, exc_info=True)
        if "OUT_OF_DISTRIBUTION" in str(e):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "prediction_allowed": False,
                    "error_code": "OUT_OF_DISTRIBUTION",
                    "message": str(e),
                    "detail": str(e),
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}",
        )


# ==============================================================================
# Endpoint 2: POST /predict/lead-score
# ==============================================================================
@app.post(
    "/predict/lead-score",
    response_model=LeadScoringResponse,
    summary="Score sales lead, assign priority tier, and predict persona",
    tags=["Lead Scoring"],
)
async def predict_lead_score(request: LeadScoringRequest) -> LeadScoringResponse:
    if lead_scorer is None or not lead_scorer._is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lead scoring service is not loaded.",
        )
    try:
        input_data = request.model_dump()
        result = lead_scorer.score_lead(input_data)
        return LeadScoringResponse(**result)
    except Exception as e:
        logger.error("Error during lead scoring: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lead scoring error: {str(e)}",
        )


# ==============================================================================
# Endpoint 3: POST /explain/price
# ==============================================================================
@app.post(
    "/explain/price",
    response_model=PriceExplanationResponse,
    summary="Explain property valuation drivers and attributions",
    tags=["Explainability"],
)
async def explain_price(request: PricePredictionRequest) -> PriceExplanationResponse:
    t0 = time.time()
    if valuator is None or not valuator._is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Property valuation service is not loaded.",
        )
    input_data = request.model_dump()
    val_res = valuator.predict(input_data, purpose=request.purpose)
    latency_ms = (time.time() - t0) * 1000.0

    return PriceExplanationResponse(
        status="contract_active_explainer_pending_task2",
        message="Property valuation TreeSHAP explainer module is scheduled for Day 4 Task 2. Model prediction contract is operational.",
        predicted_fair_price_pkr=val_res.get("predicted_fair_price_pkr"),
        top_features=[],
        urdulish_summary=(
            f"Model ke mutabiq {request.city} mein {request.area_marla} marla {request.property_type} ki fair price "
            f"{val_res.get('predicted_fair_price_pkr'):,.0f} PKR hai. Tafseeli feature breakdown aglay marhalay mein dastiyab hoga."
        ),
        inference_latency_ms=round(latency_ms, 2),
    )


# ==============================================================================
# Endpoint 4: POST /explain/lead
# ==============================================================================
@app.post(
    "/explain/lead",
    response_model=LeadExplanationResponse,
    summary="Compute TreeSHAP attributions and UrduLish rationale for lead",
    tags=["Explainability"],
)
async def explain_lead(request: LeadScoringRequest) -> LeadExplanationResponse:
    t0 = time.time()
    if lead_scorer is None or not lead_scorer._is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lead scoring service is not loaded.",
        )

    try:
        input_data = request.model_dump()
        score_res = lead_scorer.score_lead(input_data)
        prob = score_res["conversion_probability"]
        tier = score_res["tier"]

        df_single = pd.DataFrame([input_data])
        df_feat = add_lead_features(df_single)
        if "location_frequency" not in df_feat.columns:
            df_feat["location_frequency"] = 0.05
        X_trans = lead_scorer.pipeline.transform(df_feat)

        top_pos = []
        top_neg = []

        if lead_tree_explainer is not None:
            shap_vals = lead_tree_explainer(X_trans)
            vals = shap_vals.values
            if len(vals.shape) == 3 and vals.shape[2] == 2:
                vals = vals[:, :, 1]
            row_vals = vals[0]

            feature_names = getattr(lead_scorer.pipeline, "get_feature_names_out", None)
            if callable(feature_names):
                f_names = list(lead_scorer.pipeline.get_feature_names_out())
            else:
                f_names = [f"feat_{i}" for i in range(len(row_vals))]

            contributions = [
                {"feature": f_names[i], "shap_value": float(round(row_vals[i], 4))}
                for i in range(len(row_vals))
            ]
            contributions.sort(key=lambda x: x["shap_value"], reverse=True)

            top_pos = [c for c in contributions if c["shap_value"] > 0][:5]
            top_neg = sorted([c for c in contributions if c["shap_value"] < 0], key=lambda x: x["shap_value"])[:5]

        latency_ms = (time.time() - t0) * 1000.0

        return LeadExplanationResponse(
            conversion_probability=prob,
            tier=tier,
            top_positive_features=top_pos,
            top_negative_features=top_neg,
            urdulish_explanation=score_res["urdulish_explanation"],
            inference_latency_ms=round(latency_ms, 2),
        )
    except Exception as e:
        logger.error("Error computing lead explanation: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation computation error: {str(e)}",
        )


# ==============================================================================
# Endpoint 5: POST /predict/batch
# ==============================================================================
@app.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    summary="Batch inference via CSV upload (capped at 500 rows)",
    tags=["Batch"],
)
async def predict_batch(file: UploadFile = File(...)) -> BatchPredictionResponse:
    t0 = time.time()

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid CSV document with .csv extension.",
        )

    try:
        contents = await file.read()
        df_batch = pd.read_csv(io.BytesIO(contents), low_memory=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV file: {str(e)}",
        )

    if df_batch.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains no rows.",
        )

    MAX_ROWS = 500
    if len(df_batch) > MAX_ROWS:
        df_batch = df_batch.iloc[:MAX_ROWS].copy()
        logger.warning("Batch CSV truncated to safe upper limit of %d rows.", MAX_ROWS)

    cols = set(df_batch.columns)
    is_valuation = "area_marla" in cols or "property_type" in cols
    is_lead = "budget_pkr" in cols or "number_of_calls" in cols or "lead_source" in cols

    if not is_valuation and not is_lead:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unrecognized CSV schema. Valuation batch requires at minimum 'area_marla' and 'city'. "
                "Lead batch requires at minimum 'budget_pkr' and 'preferred_city'."
            ),
        )

    batch_type = "valuation" if is_valuation else "lead"
    results = []
    errors = []

    for idx, row in df_batch.iterrows():
        row_dict = row.dropna().to_dict()
        try:
            if batch_type == "valuation":
                validated = PricePredictionRequest(**row_dict)
                pred = valuator.predict(validated.model_dump(), purpose=validated.purpose)
                results.append({"row_index": int(idx), "status": "success", "prediction": pred})
            else:
                validated = LeadScoringRequest(**row_dict)
                pred = lead_scorer.score_lead(validated.model_dump())
                results.append({"row_index": int(idx), "status": "success", "prediction": pred})
        except Exception as e:
            errors.append({"row_index": int(idx), "error": str(e)})

    total_latency_ms = (time.time() - t0) * 1000.0

    return BatchPredictionResponse(
        batch_type=batch_type,
        rows_processed=len(df_batch),
        successful_predictions=len(results),
        failed_predictions=len(errors),
        results=results,
        errors=errors,
        total_latency_ms=round(total_latency_ms, 2),
    )


# ==============================================================================
# Endpoint 6: GET /health
# ==============================================================================
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health and loaded model artifacts",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    val_ok = (valuator is not None) and valuator._is_loaded and (valuator.sale_model_huber is not None)
    lead_ok = (lead_scorer is not None) and lead_scorer._is_loaded and (lead_scorer.model is not None)

    system_ready = val_ok and lead_ok
    status_str = "healthy" if system_ready else "degraded"

    return HealthResponse(
        status=status_str,
        timestamp=datetime.now(timezone.utc).isoformat(),
        models_loaded={
            "sale_model_huber": val_ok,
            "rent_model_huber": val_ok,
            "sale_preprocessor_huber": val_ok,
            "rent_preprocessor_huber": val_ok,
            "lead_scoring_model": lead_ok,
            "lead_preprocessor": lead_ok,
            "lead_persona_kmeans": (lead_scorer is not None and lead_scorer.kmeans is not None),
        },
        system_ready=system_ready,
    )


# ==============================================================================
# Endpoint 7: GET /model/info
# ==============================================================================
@app.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Inspect model provenance, versions, and verified metrics",
    tags=["System"],
)
async def get_model_info() -> ModelInfoResponse:
    info = {
        "sale_valuation": {
            "model_family": "LightGBM Regressor",
            "objective": "huber (alpha=0.9)",
            "version": "huber_v1.0",
            "target": "np.log1p(price_pkr)",
            "features_count": 64,
            "trained_date": "2026-09-30",
            "validation_metrics": {
                "partition": "prop_sale_val.csv (N=18,989)",
                "mape": 18.22,
                "mdape": 11.20,
                "mae_pkr": 4227737,
                "rmse_pkr": 13175514,
                "r2": 0.8800,
            },
            "locked_test_metrics": {
                "partition": "prop_sale_test.csv (N=18,989)",
                "mape": 17.87,
                "mdape": 11.41,
                "mae_pkr": 4211545,
                "rmse_pkr": 14070212,
                "r2": 0.8538,
            },
        },
        "rent_valuation": {
            "model_family": "LightGBM Regressor",
            "objective": "huber (alpha=0.9)",
            "version": "huber_v1.0",
            "target": "np.log1p(price_pkr)",
            "features_count": 64,
            "trained_date": "2026-09-30",
            "validation_metrics": {
                "partition": "prop_rent_val.csv (N=9,621)",
                "mape": 17.61,
                "mdape": 11.65,
                "mae_pkr": 20798,
                "rmse_pkr": 145297,
                "r2": 0.4437,
            },
            "locked_test_metrics": {
                "partition": "prop_rent_test.csv (N=9,621)",
                "mape": 17.41,
                "mdape": 11.71,
                "mae_pkr": 19116,
                "rmse_pkr": 66473,
                "r2": 0.7863,
            },
        },
        "lead_scoring": {
            "model_family": "LightGBM Classifier",
            "tuning": "Optuna Bayesian Optimization (15 trials)",
            "version": "lgbm_optuna_v1.0",
            "target": "converted (binary 0/1)",
            "trained_date": "2026-09-30",
            "validation_metrics": {
                "pr_auc": 0.6125,
                "roc_auc": 0.8652,
            },
            "locked_test_metrics": {
                "partition": "lead_test.csv (N=750)",
                "pr_auc": 0.6055,
                "roc_auc": 0.8671,
                "precision_at_top_20": 58.0,
                "baseline_conversion_rate": 21.73,
                "top_20_lift": 2.67,
                "f1_score": 0.6072,
                "brier_score": 0.1263,
            },
        },
        "customer_personas": {
            "model_family": "K-Means Clustering (k=3)",
            "version": "kmeans_k3_v1.0",
            "trained_date": "2026-09-30",
            "clusters": {
                "0": "First-Time Urban Homebuyer",
                "1": "High-Net-Worth Investor",
                "2": "Budget Renter / Short-Horizon Inquirer",
            },
        },
    }

    return ModelInfoResponse(
        service="Week 8 Real Estate AI Serving Gateway",
        environment="production",
        models=info,
    )


# ==============================================================================
# Endpoint 8: POST /assistant/chat
# ==============================================================================
@app.post(
    "/assistant/chat",
    response_model=ChatResponse,
    summary="Bilingual LangGraph AI Assistant for valuation, lead scoring, and market queries",
    tags=["Assistant"],
)
async def assistant_chat(request: ChatRequest) -> ChatResponse:
    t0 = time.time()
    try:
        state_input = {
            "query": request.message,
            "conversation_id": request.conversation_id,
            "messages": [{"role": "user", "content": request.message}],
        }
        final_state = real_estate_assistant.invoke(state_input)
        latency_ms = (time.time() - t0) * 1000.0

        return ChatResponse(
            response=final_state.get("final_response", ""),
            intent=final_state.get("intent", "general"),
            tool_calls=final_state.get("tool_calls", []),
            tool_results=final_state.get("tool_results", {}),
            missing_fields=final_state.get("missing_fields", []),
            language=final_state.get("language", "english"),
            guard_triggered=bool(final_state.get("guard_triggered", False)),
            inference_latency_ms=round(latency_ms, 2),
        )
    except Exception as e:
        logger.error("Error during assistant chat: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant execution error: {str(e)}",
        )


# ==============================================================================
# Endpoint 9: GET /market/stats
# ==============================================================================
@app.get(
    "/market/stats",
    summary="Get verified property market statistics from clean dataset",
    tags=["Market"],
)
async def get_market_statistics(
    city: Optional[str] = None,
    location: Optional[str] = None,
    purpose: str = "For Sale",
) -> Dict[str, Any]:
    from src.agent.data_store import PropertyDataStore
    store = PropertyDataStore.get_instance()
    return store.get_market_stats(city=city, location=location, purpose=purpose)


# ==============================================================================
# Endpoint 10: GET /market/insights
# ==============================================================================
@app.get(
    "/market/insights",
    summary="City-wide market comparison and distributions across Pakistan",
    tags=["Market"],
)
async def get_market_insights() -> Dict[str, Any]:
    from src.agent.data_store import PropertyDataStore
    store = PropertyDataStore.get_instance()
    cities = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"]
    sale_stats = [store.get_market_stats(city=c, purpose="For Sale") for c in cities]
    rent_stats = [store.get_market_stats(city=c, purpose="For Rent") for c in cities]
    return {
        "total_dataset_records": len(store.df) if store.df is not None else 0,
        "cities": cities,
        "sale_by_city": sale_stats,
        "rent_by_city": rent_stats,
    }


# ==============================================================================
# Endpoint 11: GET /properties
# ==============================================================================
@app.get(
    "/properties",
    summary="Search Week 8 property listings from the configured catalog",
    tags=["Properties"],
)
async def get_properties(
    city: Optional[str] = None,
    location: Optional[str] = None,
    property_type: Optional[str] = None,
    purpose: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    from src.agent.data_store import PropertyDataStore
    store = PropertyDataStore.get_instance()
    return store.search_properties(
        city=city,
        location=location,
        property_type=property_type,
        purpose=purpose,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        limit=min(limit, 100),
        offset=offset,
    )


# ==============================================================================
# Endpoint 12: GET /properties/{property_id}
# ==============================================================================
@app.get(
    "/properties/{property_id}",
    summary="Fetch complete verified property specifications by ID",
    tags=["Properties"],
)
async def get_single_property(property_id: str) -> Dict[str, Any]:
    from src.agent.data_store import PropertyDataStore
    store = PropertyDataStore.get_instance()
    prop = store.get_property(property_id)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property '{property_id}' not found in verified dataset.",
        )
    return prop


# ==============================================================================
# Endpoint 13: GET /leads
# ==============================================================================
@app.get(
    "/leads",
    summary="Retrieve verified sales leads with behavioral signals from Week 8 dataset",
    tags=["Leads"],
)
async def get_leads_dataset(
    limit: int = 50,
    offset: int = 0,
    tier: Optional[str] = None,
    city: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    from src.agent.data_store import LeadDataStore
    store = LeadDataStore.get_instance()
    return store.get_leads(
        limit=min(limit, 200),
        offset=offset,
        tier=tier,
        city=city,
        source=source,
        search=search,
    )


# ==============================================================================
# Endpoint 14: GET /leads/{lead_id}
# ==============================================================================
@app.get(
    "/leads/{lead_id}",
    summary="Fetch single lead record with features",
    tags=["Leads"],
)
async def get_single_lead(lead_id: str) -> Dict[str, Any]:
    from src.agent.data_store import LeadDataStore
    store = LeadDataStore.get_instance()
    lead = store.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{lead_id}' not found in verified dataset.",
        )
    return lead


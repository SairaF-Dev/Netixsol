"""
test_day4_api.py
----------------
Automated test suite for Week 8 Day 4 Task 1: FastAPI Model Serving.
Validates all 7 endpoints, Pydantic input constraints, error responses,
model metadata, and latency SLAs (<500 ms).
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
import pytest

from src.api.app import app
from src.models.explain_valuation import generate_valuation_shap_report
from src.models.predict_valuation import PropertyValuator


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. Health & Model Info Tests
# ==============================================================================

class TestSystemEndpoints:
    def test_health_check_healthy(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["system_ready"] is True
        assert data["models_loaded"]["sale_model_huber"] is True
        assert data["models_loaded"]["rent_model_huber"] is True
        assert data["models_loaded"]["lead_scoring_model"] is True

    def test_model_info_structure_and_metrics(self, client: TestClient):
        response = client.get("/model/info")
        assert response.status_code == 200
        data = response.json()
        models = data["models"]

        # Sale valuation metadata
        assert "sale_valuation" in models
        assert models["sale_valuation"]["version"] == "huber_v1.0"
        assert models["sale_valuation"]["trained_date"] == "2026-09-30"
        assert models["sale_valuation"]["validation_metrics"]["mape"] == 18.22
        assert models["sale_valuation"]["locked_test_metrics"]["mape"] == 17.87

        # Rent valuation metadata
        assert "rent_valuation" in models
        assert models["rent_valuation"]["version"] == "huber_v1.0"
        assert models["rent_valuation"]["validation_metrics"]["mape"] == 17.61
        assert models["rent_valuation"]["locked_test_metrics"]["mape"] == 17.41

        # Lead scoring metadata
        assert "lead_scoring" in models
        assert models["lead_scoring"]["version"] == "lgbm_optuna_v1.0"
        assert models["lead_scoring"]["locked_test_metrics"]["pr_auc"] == 0.6055
        assert models["lead_scoring"]["locked_test_metrics"]["precision_at_top_20"] == 58.0

        # Customer personas metadata
        assert "customer_personas" in models
        assert "0" in models["customer_personas"]["clusters"]


# ==============================================================================
# 2. Property Valuation Tests
# ==============================================================================

class TestPropertyValuationEndpoints:
    def test_predict_price_valid_sale(self, client: TestClient):
        payload = {
            "purpose": "For Sale",
            "property_type": "House",
            "city": "Lahore",
            "location": "DHA Defence Phase 5",
            "area_marla": 20.0,
            "bedrooms": 5,
            "baths": 6,
            "price": 85_000_000.0,
        }
        t0 = time.time()
        response = client.post("/predict/price", json=payload)
        latency_ms = (time.time() - t0) * 1000.0

        assert response.status_code == 200
        assert latency_ms < 500.0, f"SLA violated: {latency_ms:.2f}ms >= 500ms"

        data = response.json()
        assert data["purpose"] == "For Sale"
        assert data["predicted_fair_price_pkr"] > 0
        assert data["lower_bound_pkr"] <= data["predicted_fair_price_pkr"] <= data["upper_bound_pkr"]
        assert data["verdict"] in ["Overpriced", "Fair", "Underpriced"]
        assert data["model_version"] == "huber_v1.0"
        assert "PKR" in data["human_readable_summary"]

    def test_predict_price_valid_rent(self, client: TestClient):
        payload = {
            "purpose": "For Rent",
            "property_type": "Flat",
            "city": "Islamabad",
            "location": "F-11",
            "area_marla": 6.0,
            "bedrooms": 2,
            "baths": 2,
            "price": 60_000.0,
        }
        response = client.post("/predict/price", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["purpose"] == "For Rent"
        assert data["predicted_fair_price_pkr"] > 0
        assert data["lower_bound_pkr"] <= data["predicted_fair_price_pkr"] <= data["upper_bound_pkr"]

    def test_predict_price_rejects_negative_area(self, client: TestClient):
        payload = {
            "purpose": "For Sale",
            "property_type": "House",
            "city": "Lahore",
            "area_marla": -5.0,
        }
        response = client.post("/predict/price", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "greater than 0" in str(data)

    def test_predict_price_rejects_unsupported_city(self, client: TestClient):
        payload = {
            "purpose": "For Sale",
            "property_type": "House",
            "city": "Peshawar",
            "area_marla": 10.0,
        }
        response = client.post("/predict/price", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "not supported by the trained model" in str(data)

    def test_predict_price_rejects_invalid_purpose(self, client: TestClient):
        payload = {
            "purpose": "Mortgage",
            "property_type": "House",
            "city": "Lahore",
            "area_marla": 10.0,
        }
        response = client.post("/predict/price", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "Must be one of: 'For Sale', 'For Rent'" in str(data)

    def test_valuation_global_and_local_shap_reports(self, tmp_path: Path):
        project_root = Path(__file__).resolve().parents[1]
        validation = pd.read_csv(
            project_root / "data" / "processed" / "prop_sale_val.csv",
            low_memory=False,
        ).head(8)
        valuator = PropertyValuator(models_dir=project_root / "models", model_variant="auto")
        report = generate_valuation_shap_report(
            valuator,
            validation,
            purpose="sale",
            output_dir=tmp_path,
            max_rows=8,
        )

        assert report["target_scale"] == "log_price"
        assert report["rows_explained"] == 8
        assert report["top_features"]
        assert Path(report["global_plot"]).is_file()
        assert Path(report["local_plot"]).is_file()
        assert Path(report["report_path"]).is_file()


# ==============================================================================
# 3. Lead Scoring Tests
# ==============================================================================

class TestLeadScoringEndpoints:
    def test_predict_lead_score_valid(self, client: TestClient):
        payload = {
            "lead_source": "Call",
            "preferred_city": "Islamabad",
            "preferred_location": "DHA Phase 2",
            "property_type": "House",
            "purpose": "Buy",
            "budget_pkr": 45_000_000.0,
            "number_of_calls": 3,
            "total_call_duration_min": 15.0,
            "response_time_minutes": 20.0,
            "visit_booked": 1,
            "days_since_first_contact": 3,
            "follow_up_count": 2,
            "budget_match_ratio": 0.95,
        }
        t0 = time.time()
        response = client.post("/predict/lead-score", json=payload)
        latency_ms = (time.time() - t0) * 1000.0

        assert response.status_code == 200
        assert latency_ms < 500.0, f"SLA violated: {latency_ms:.2f}ms >= 500ms"

        data = response.json()
        assert 0.0 <= data["conversion_probability"] <= 1.0
        assert data["tier"] in ["Hot", "Warm", "Cold"]
        assert data["priority_rank"] in [1, 2, 3]
        assert len(data["recommended_sla_action"]) > 0
        assert len(data["customer_persona"]) > 0
        assert len(data["urdulish_explanation"]) > 0
        assert data["model_version"] == "lgbm_optuna_v1.0"
        assert data["training_label_provenance"] == "synthetic"
        assert data["crm_validated"] is False

    def test_predict_lead_score_rejects_negative_budget(self, client: TestClient):
        payload = {
            "lead_source": "WhatsApp",
            "preferred_city": "Lahore",
            "budget_pkr": -100_000.0,
        }
        response = client.post("/predict/lead-score", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "greater than 0" in str(data)

    def test_predict_lead_score_rejects_unsupported_city(self, client: TestClient):
        payload = {
            "lead_source": "WhatsApp",
            "preferred_city": "Multan",
            "budget_pkr": 10_000_000.0,
        }
        response = client.post("/predict/lead-score", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "not supported by the trained model" in str(data)


# ==============================================================================
# 4. Explainability Tests
# ==============================================================================

class TestExplainabilityEndpoints:
    def test_explain_price_contract_active(self, client: TestClient):
        payload = {
            "purpose": "For Sale",
            "property_type": "House",
            "city": "Karachi",
            "location": "Clifton",
            "area_marla": 10.0,
        }
        response = client.post("/explain/price", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shap_available"
        assert data["explanation_available"] is True
        assert data["predicted_fair_price_pkr"] > 0
        assert data["lower_bound_pkr"] <= data["predicted_fair_price_pkr"] <= data["upper_bound_pkr"]
        assert data["top_features"]
        assert data["target_scale"] == "log_price"
        assert "Model ke mutabiq" in data["urdulish_summary"]
        assert "PKR mein alag-alag price changes nahi" in data["urdulish_summary"]

    def test_explain_lead_returns_shap_and_urdulish(self, client: TestClient):
        payload = {
            "lead_source": "Call",
            "preferred_city": "Lahore",
            "budget_pkr": 25_000_000.0,
            "number_of_calls": 4,
            "total_call_duration_min": 18.0,
            "visit_booked": 1,
            "days_since_first_contact": 2,
        }
        response = client.post("/explain/lead", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["conversion_probability"] <= 1.0
        assert data["tier"] in ["Hot", "Warm", "Cold"]
        assert len(data["urdulish_explanation"]) > 0
        assert isinstance(data["top_positive_features"], list)
        assert isinstance(data["top_negative_features"], list)


# ==============================================================================
# 5. Batch Prediction Tests
# ==============================================================================

class TestBatchEndpoints:
    def test_predict_batch_valuation_csv(self, client: TestClient):
        csv_content = (
            "purpose,property_type,city,location,area_marla,bedrooms,baths\n"
            "For Sale,House,Lahore,DHA Defence,20.0,5,6\n"
            "For Rent,Flat,Karachi,Clifton,6.0,2,2\n"
            "For Sale,House,Islamabad,F-7,10.0,4,4\n"
        )
        files = {"file": ("test_properties.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = client.post("/predict/batch", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["batch_type"] == "valuation"
        assert data["rows_processed"] == 3
        assert data["successful_predictions"] == 3
        assert data["failed_predictions"] == 0
        assert len(data["results"]) == 3

    def test_predict_batch_lead_csv(self, client: TestClient):
        csv_content = (
            "lead_source,preferred_city,budget_pkr,number_of_calls,visit_booked\n"
            "Call,Lahore,25000000.0,3,1\n"
            "WhatsApp,Islamabad,45000000.0,1,0\n"
        )
        files = {"file": ("test_leads.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = client.post("/predict/batch", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["batch_type"] == "lead"
        assert data["rows_processed"] == 2
        assert data["successful_predictions"] == 2
        assert data["failed_predictions"] == 0

    def test_predict_batch_rejects_non_csv(self, client: TestClient):
        files = {"file": ("test.txt", io.BytesIO(b"Hello World"), "text/plain")}
        response = client.post("/predict/batch", files=files)
        assert response.status_code == 400
        assert "valid CSV" in response.json()["detail"]

    def test_predict_batch_rejects_unrecognized_columns(self, client: TestClient):
        csv_content = "col_x,col_y\n1,2\n3,4\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        response = client.post("/predict/batch", files=files)
        assert response.status_code == 422
        assert "Unrecognized CSV schema" in response.json()["detail"]

"""Read-only smoke check against configured PostgreSQL; prints inventory only."""
from pathlib import Path
import sys

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "day2" / "03_structured_retrieval"))
for path in (root / ".env", root / "day2" / ".env", root / "day7" / "vapi_integration" / ".env"):
    load_dotenv(path)

from postgres_repository import PostgresPropertyRepository

repo = PostgresPropertyRepository()
for purpose, budget in (("Purchase", 40000000), ("Purchase", 1), ("Rental", 100000), ("Purchase", None)):
    result = repo.budget_area_options(city="Lahore", purpose=purpose, budget=budget)
    assert all(budget is None or row["match_price"] <= budget for row in result["areas"])
    print(purpose, budget, result)

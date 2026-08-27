import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "01_knowledge_base"


def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return pd.read_csv(path)


def check_unique_ids(df, column, dataset_name):
    duplicates = df[df[column].duplicated(keep=False)]

    if duplicates.empty:
        print(f"✅ {dataset_name}: {column} values are unique")
    else:
        print(f"❌ {dataset_name}: duplicate {column} values found:")
        print(duplicates[[column]].drop_duplicates())


def check_foreign_keys(child_df, child_column, parent_df, parent_column,
                       child_name, parent_name):

    child_values = set(child_df[child_column].dropna().astype(str))
    parent_values = set(parent_df[parent_column].dropna().astype(str))

    missing = child_values - parent_values

    if not missing:
        print(
            f"✅ {child_name} → {parent_name}: "
            f"all {child_column} references are valid"
        )
    else:
        print(
            f"❌ {child_name} → {parent_name}: "
            f"missing references found:"
        )
        for value in sorted(missing):
            print(f"   - {value}")


def main():

    print("\n" + "=" * 60)
    print("DAY 2 — KNOWLEDGE BASE VALIDATION")
    print("=" * 60)

    # Load datasets
    properties = load_csv("properties.csv")
    prices = load_csv("prices.csv")
    locations = load_csv("locations.csv")
    amenities = load_csv("amenities.csv")
    schools = load_csv("schools.csv")
    hospitals = load_csv("hospitals.csv")
    payment_plans = load_csv("payment_plans.csv")
    developers = load_csv("developers.csv")
    faqs = load_csv("faqs.csv")

    print("\n📊 RECORD COUNTS")
    print("-" * 40)

    datasets = {
        "Properties": properties,
        "Prices": prices,
        "Locations": locations,
        "Amenities": amenities,
        "Schools": schools,
        "Hospitals": hospitals,
        "Payment Plans": payment_plans,
        "Developers": developers,
        "FAQs": faqs,
    }

    for name, df in datasets.items():
        print(f"{name:<20} {len(df):>4} rows")

    # --------------------------------------------------
    # Primary key checks
    # --------------------------------------------------

    print("\n🔑 PRIMARY KEY VALIDATION")
    print("-" * 40)

    check_unique_ids(
        properties,
        "property_id",
        "properties.csv"
    )

    check_unique_ids(
        prices,
        "property_id",
        "prices.csv"
    )

    check_unique_ids(
        locations,
        "location_id",
        "locations.csv"
    )

    check_unique_ids(
        developers,
        "developer_id",
        "developers.csv"
    )

    check_unique_ids(
        schools,
        "school_id",
        "schools.csv"
    )

    check_unique_ids(
        hospitals,
        "hospital_id",
        "hospitals.csv"
    )

    check_unique_ids(
        faqs,
        "faq_id",
        "faqs.csv"
    )

    # --------------------------------------------------
    # Foreign key checks
    # --------------------------------------------------

    print("\n🔗 FOREIGN KEY VALIDATION")
    print("-" * 40)

    # Properties → Locations
    check_foreign_keys(
        properties,
        "location_id",
        locations,
        "location_id",
        "properties.csv",
        "locations.csv"
    )

    # Properties → Developers
    check_foreign_keys(
        properties,
        "developer_id",
        developers,
        "developer_id",
        "properties.csv",
        "developers.csv"
    )

    # Prices → Properties
    check_foreign_keys(
        prices,
        "property_id",
        properties,
        "property_id",
        "prices.csv",
        "properties.csv"
    )

    # Amenities → Properties
    check_foreign_keys(
        amenities,
        "property_id",
        properties,
        "property_id",
        "amenities.csv",
        "properties.csv"
    )

    # Schools → Properties
    check_foreign_keys(
        schools,
        "reference_property",
        properties,
        "property_id",
        "schools.csv",
        "properties.csv"
    )

    # Hospitals → Properties
    check_foreign_keys(
        hospitals,
        "reference_property",
        properties,
        "property_id",
        "hospitals.csv",
        "properties.csv"
    )

    # Payment Plans → Properties
    check_foreign_keys(
        payment_plans,
        "property_id",
        properties,
        "property_id",
        "payment_plans.csv",
        "properties.csv"
    )

    # --------------------------------------------------
    # Property-specific checks
    # --------------------------------------------------

    print("\n🏠 PROPERTY DATA VALIDATION")
    print("-" * 40)

    if len(properties) >= 40:
        print(f"✅ Property dataset contains {len(properties)} valid properties")
    else:
        print(
            f"❌ Expected at least 40 properties, "
            f"found {len(properties)}"
        )
    valid_purposes = {"Purchase", "Rental"}

    invalid_purposes = set(properties["purpose"]) - valid_purposes

    if not invalid_purposes:
        print("✅ Property purposes are valid")
    else:
        print(f"❌ Invalid purposes: {invalid_purposes}")

    valid_availability = {"Yes", "No"}

    invalid_availability = (
        set(properties["available"]) - valid_availability
    )

    if not invalid_availability:
        print("✅ Availability values are valid")
    else:
        print(f"❌ Invalid availability values: {invalid_availability}")

    # --------------------------------------------------
    # Price checks
    # --------------------------------------------------

    print("\n💰 PRICE VALIDATION")
    print("-" * 40)

    duplicate_prices = prices[
        prices.duplicated(
            subset=["property_id"],
            keep=False
        )
    ]

    if duplicate_prices.empty:
        print("✅ No duplicate price records")
    else:
        print("❌ Duplicate price records found:")
        print(duplicate_prices["property_id"].tolist())

    if (prices["price"] > 0).all():
        print("✅ All prices are greater than zero")
    else:
        print("❌ Invalid price values found")

    # --------------------------------------------------
    # FAQ checks
    # --------------------------------------------------

    print("\n📚 FAQ VALIDATION")
    print("-" * 40)

    required_faq_columns = {
        "faq_id",
        "question",
        "answer",
        "category"
    }

    missing_faq_columns = (
        required_faq_columns - set(faqs.columns)
    )

    if not missing_faq_columns:
        print("✅ FAQ required fields are present")
    else:
        print(
            f"❌ Missing FAQ columns: "
            f"{missing_faq_columns}"
        )

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
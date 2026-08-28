from pathlib import Path


PROPERTY_METADATA = {
    "skyline_residences.md": {
        "property_name": "Skyline Residences",
        "property_id": "DHA-APT-001",
        "document_type": "property",
    },
    "dha_pearl_apartments.md": {
        "property_name": "DHA Pearl Apartments",
        "property_id": "DHA-APT-002",
        "document_type": "property",
    },
    "bahria_grand_apartments.md": {
        "property_name": "Bahria Grand Apartments",
        "property_id": "BT-APT-001",
        "document_type": "property",
    },
    "real_estate_faq.md": {
        "property_name": "",
        "property_id": "",
        "document_type": "faq",
    },
}


def get_metadata(source: str) -> dict:
    """Return metadata for a document source."""

    filename = Path(source).name

    metadata = PROPERTY_METADATA.get(
        filename
    )

    if metadata is None:
        return {
            "property_name": "",
            "property_id": "",
            "document_type": "unknown",
        }

    return metadata.copy()
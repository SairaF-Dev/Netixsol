"""
Neo4j connection from .env (NEO4J_URI, NEO4J_USERNAME / NEO4J_USER, NEO4J_PASSWORD).

AuraDB serves a certificate from SSL.com whose root may be missing from the Windows
certificate store that Python uses, which fails with "self-signed certificate in
certificate chain". The connection is therefore made with the `certifi` CA bundle:
still encrypted and verified, just against Mozilla's root list.
"""

import os
from pathlib import Path

import certifi
from dotenv import load_dotenv
from neo4j import GraphDatabase, TrustCustomCAs


def get_driver():
    load_dotenv(Path(".env"))
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER") or "neo4j"
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not password:
        raise RuntimeError("Set NEO4J_URI and NEO4J_PASSWORD in .env")
    if uri.startswith(("neo4j+s://", "bolt+s://")):
        scheme = uri.split("+s://", 1)[0]
        return GraphDatabase.driver(uri.replace(f"{scheme}+s://", f"{scheme}://"), auth=(user, password),
                                    encrypted=True, trusted_certificates=TrustCustomCAs(certifi.where()))
    return GraphDatabase.driver(uri, auth=(user, password))


def database() -> str | None:
    return os.getenv("NEO4J_DATABASE") or None
